# Branch Knowledge Base — Practical Guide

This runbook lists every practical task required to operate or publish the BeatHub branch. Follow these steps sequentially when preparing local development, internal demos, or public SaaS deployments.

## 1. Prerequisites

- **Operating system** – Backend runs anywhere Python 3.11+ is available. CD burning workflows require Windows 10/11 because they depend on IMAPI v2 COM interfaces.【F:README.md†L13-L19】【F:README.md†L105-L173】
- **Python toolchain** – Install Python 3.11+ plus `pip` and `venv` support.【F:README.md†L19-L45】
- **Node.js** – Version 18+ for the React frontend (Create React App).【F:README.md†L31-L56】
- **Audio tooling** – Install `ffmpeg` on your PATH; `pydub` shells out to it during downloads and CD preparation.【F:README.md†L21-L45】【F:src/domain/burning/service.py†L1-L43】
- **API credentials** – Spotify client id/secret (required for browsing and higher success with spotDL). Genius token optional for richer lyric extraction.【F:README.md†L23-L45】【F:config.py†L36-L63】

## 2. Repository Checkout & Python Environment

```bash
# Clone and enter the repository
git clone <repo-url>
cd CD-Collector

# Create & activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1

# Install backend dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```
The requirements file contains Flask, SQLAlchemy, Spotipy, spotDL, pydub, Flask-CORS, and observability extras needed by the app.【F:README.md†L41-L74】【F:requirements.txt†L1-L120】

## 3. Frontend Tooling

```bash
cd frontend
npm install
cd ..
```
This installs React, React Router, React Query, Tailwind (optional styling utilities), and build tooling defined in `package.json`.【F:frontend/package.json†L1-L34】

## 4. Environment Configuration

Create `.env` in the repository root with the sample below, adjusting values as needed:

```env
SECRET_KEY=change_me
BASE_OUTPUT_DIR=downloads
SPOTIPY_CLIENT_ID=<spotify_client_id>
SPOTIPY_CLIENT_SECRET=<spotify_client_secret>
GENIUS_ACCESS_TOKEN=<optional_genius_token>
SPOTDL_AUDIO_SOURCE=youtube-music
SPOTDL_FORMAT=mp3
SPOTDL_THREADS=1
DOWNLOAD_QUEUE_WORKERS=2
DOWNLOAD_MAX_RETRIES=2
PUBLIC_MODE=0
ALLOW_STREAMING_EXPORT=1
ENABLE_CD_BURNER=1
ENABLE_CONSOLE_LOGS=0
```
The configuration loader in `config.py` automatically picks up these values (with sensible defaults) when Flask starts.【F:config.py†L1-L209】 Adjust `PUBLIC_MODE`, `ALLOW_STREAMING_EXPORT`, and `ENABLE_CD_BURNER` based on whether you intend to expose CD burning or audio streaming in production.【F:README.md†L175-L210】

## 5. Database Initialization

On first boot the app creates an SQLite database at `src/database/instance/beathub.db` and seeds a system user. No manual migrations are required. Remove that file to reset the environment; the schema recreates on the next run.【F:config.py†L28-L35】【F:src/database/db_manager.py†L1-L44】

## 6. Running the Backend (Development)

```bash
# From repository root with virtualenv active
python app.py
```
`app.py` loads `.env`, configures logging, sets up SQLAlchemy, the download orchestrator, job queue, progress broker, CD burning service, and registers all Flask blueprints (including `/api` routes and `/metrics`).【F:app.py†L1-L223】 The server listens on `http://localhost:5000` by default.【F:README.md†L90-L134】

Watch the terminal for the startup log file path (`log-YYYY-MM-DD-HH-MM-SS`) created in the configured log directory. Request IDs are injected into responses (`X-Request-ID`) for traceability.【F:app.py†L89-L157】【F:src/observability/logging.py†L1-L88】

## 7. Running the Frontend (Development)

```bash
cd frontend
npm start
```
The dev server runs on `http://localhost:3000`, proxying API calls to the Flask backend. Hot module replacement accelerates UI iteration.【F:README.md†L56-L88】 Ensure the backend is already running so the proxy finds `/api` endpoints.

## 8. Production Build (Single Machine)

1. Build frontend assets: `cd frontend && npm run build && cd ..`. Flask serves `frontend/build` statically when present.【F:README.md†L56-L114】【F:app.py†L1-L45】
2. Run the backend with production settings (`PUBLIC_MODE=0/1` as desired). Use a process manager (systemd, supervisor) for longevity.
3. Configure reverse proxies (NGINX/Caddy) if exposing publicly; ensure CORS origins match your domain via `CORS_ALLOWED_ORIGINS` env var.【F:config.py†L179-L209】

## 9. Docker-Based Public Deployment

1. Build and run: `docker compose -f docker-compose.public.yml up --build`. This sets `PUBLIC_MODE=1`, disables streaming/burning, attaches a persistent volume at `/app/downloads`, and exposes port `5000`.【F:docker-compose.public.yml†L1-L33】
2. Populate Spotify/Genius credentials via environment or `.env` file exported before running Compose.【F:docker-compose.public.yml†L11-L20】
3. Optional: enable the bundled Redis service if you later replace the in-process queue.
4. Health checks run `python /app/scripts/healthcheck.py`; monitor container status via `docker compose ps`.【F:docker-compose.public.yml†L21-L28】

## 10. User Onboarding & Authentication

- Visit `http://localhost:3000/register` to create an account; credentials persist in the `users` table (`src/database/db_manager.py`).【F:frontend/src/App.js†L27-L43】【F:src/database/db_manager.py†L17-L63】
- Login at `/login`; session cookies are stored client-side and honoured by Flask via Flask-Login integration wired in `app.py` (see `src/auth`).【F:app.py†L1-L223】【F:src/auth/__init__.py†L1-L120】

## 11. Download Workflow

1. Navigate to **Browse** to search artists/albums (Spotipy-backed endpoints).【F:frontend/src/App.js†L27-L43】【F:src/domain/downloads/orchestrator.py†L1-L242】
2. On the **Download** page, paste a Spotify album/track/playlist link and submit. The API enqueues a job via `JobQueue.submit`, returning a job id.【F:src/domain/downloads/jobs.py†L33-L118】
3. Monitor progress using the UI’s SSE stream (`/api/progress/stream`) or poll `/api/downloads/jobs/<id>`. Workers publish queue depth and job timings to Prometheus metrics.【F:src/interfaces/http/routes/progress.py†L1-L43】【F:src/domain/downloads/jobs.py†L118-L190】【F:src/observability/metrics.py†L1-L66】
4. Completed downloads appear under history/favourites; assets are saved under `BASE_OUTPUT_DIR` (default `downloads/`). Metadata JSON in each folder includes track ordering for CD burning.【F:config.py†L55-L98】【F:src/domain/downloads/file_manager.py†L1-L140】

## 12. CD Burning (Windows Only)

1. Ensure `ENABLE_CD_BURNER=1` and run backend on Windows with IMAPI v2 available.【F:config.py†L73-L98】【F:src/domain/burning/service.py†L1-L85】
2. Insert a blank CD-R/RW and open the **Burn CD** page. The backend enumerates devices via `CDBurningService.scan_for_burner` and caches the chosen recorder.【F:src/domain/burning/service.py†L43-L108】
3. Select a previously downloaded item; the service converts MP3 → WAV with `pydub`, stages files via IMAPI, and emits progress events through the shared broker.【F:src/domain/burning/service.py†L109-L187】【F:src/core/progress.py†L1-L69】
4. Monitor burn status via the UI or `/api/cd-burner/status`. Cancelling calls `CDBurningService.request_cancel` to stop staging/burning gracefully.【F:src/domain/burning/service.py†L187-L275】

## 13. Observability & Operations

- **Structured logs** – JSON logs include request metadata and optional OTLP export when `OTEL_EXPORTER_OTLP_ENDPOINT` is configured.【F:src/observability/logging.py†L1-L88】【F:config.py†L107-L126】
- **Metrics** – Scrape `http://<host>:5000/metrics` (Prometheus format) for download counts, failures, queue depth, and job durations.【F:src/observability/metrics.py†L1-L66】
- **Tracing** – Configure `OTEL_EXPORTER_OTLP_ENDPOINT/HEADERS` to emit spans (init logic in `src/observability/tracing.py`).【F:config.py†L107-L126】
- **Rate limiting** – Enable by setting `ENABLE_RATE_LIMITING=1` with thresholds via `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS`; frontend surfaces the policy via feature flags.【F:config.py†L73-L126】【F:src/interfaces/http/routes/config.py†L15-L43】
- **Health/readiness** – Compose deployments use `scripts/healthcheck.py`; for bare-metal setups, consider curling `/metrics` or building an HTTP readiness endpoint around queue depth (`READINESS_QUEUE_THRESHOLD`).【F:docker-compose.public.yml†L21-L28】【F:config.py†L99-L126】

## 14. Maintenance Tasks

- **Resetting downloads** – Clear the `downloads/` directory and associated DB rows if you need a clean slate (delete `beathub.db`).【F:config.py†L28-L63】【F:src/domain/downloads/repository.py†L1-L153】
- **Backing up data** – Snapshot `downloads/` and `src/database/instance/beathub.db` regularly in production deployments.
- **Upgrading dependencies** – Re-run `pip install -r requirements.txt` after editing the file; rebuild the frontend (`npm install`, `npm run build`) when `package.json` changes.【F:requirements.txt†L1-L120】【F:frontend/package.json†L1-L34】
- **Monitoring queue pressure** – Track `cdcollector_job_queue_depth` gauge; raise `DOWNLOAD_QUEUE_WORKERS` or scale out workers if backlog persists.【F:src/observability/metrics.py†L15-L33】【F:config.py†L65-L72】

Following this checklist covers the full lifecycle: from local setup and testing through public publication, observability, and day-two operations.
