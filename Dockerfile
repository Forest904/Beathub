###############################################
# Frontend build stage
###############################################
FROM node:20-bullseye-slim AS frontend-builder

WORKDIR /frontend

# Install dependencies first to leverage layer caching
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

###############################################
# Python dependency build stage
###############################################
FROM python:3.11-slim AS python-deps

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

###############################################
# Final runtime image
###############################################
FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app \
    BASE_OUTPUT_DIR=/app/downloads \
    PUBLIC_MODE=1 \
    ALLOW_STREAMING_EXPORT=0

WORKDIR ${APP_HOME}

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --system cdcollector && useradd --system --gid cdcollector --create-home --home-dir /home/cdcollector cdcollector

# Install Python dependencies from wheel cache
COPY --from=python-deps /wheels /wheels
COPY --from=python-deps /app/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir /wheels/*

# Copy application code
COPY . ${APP_HOME}
COPY --from=frontend-builder /frontend/build ${APP_HOME}/frontend/build

# Ensure healthcheck script is executable
RUN chmod +x ${APP_HOME}/scripts/healthcheck.py

# Set ownership of application files and downloads directory
RUN mkdir -p ${BASE_OUTPUT_DIR} \
    && chown -R cdcollector:cdcollector ${APP_HOME}

USER cdcollector

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python /app/scripts/healthcheck.py

CMD ["python", "app.py"]
