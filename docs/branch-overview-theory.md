# Branch Knowledge Base — Theory

This document explains the full BeatHub branch (repository `CD-Collector`) from a conceptual perspective. It covers why each subsystem exists, how components interact, and the technologies that enable the product experience.

## 1. Product and Branch Goals

BeatHub lets users discover Spotify artists/albums, download Spotify content using [spotDL](https://github.com/spotDL/spotify-downloader), extract lyrics, organise the assets locally, and optionally burn audio CDs (Windows only).【F:README.md†L1-L75】 The branch introduces a production-ready “public mode” for hosted deployments, feature gating via configuration, and observability hooks so that the same codebase can run both locally and as a managed SaaS.【F:README.md†L77-L173】【F:README.md†L175-L233】

Key goals addressed by this branch:

- **End-to-end Spotify workflow** – metadata search, download orchestration, and catalogue persistence, all bound together inside a Flask application.【F:src/domain/downloads/orchestrator.py†L1-L116】【F:src/domain/downloads/repository.py†L1-L153】
- **User-facing React experience** – a SPA built with React Query, React Router, and shared feature-flag context to surface backend capabilities in real time.【F:frontend/src/App.js†L1-L56】【F:frontend/src/shared/context/FeatureFlagsContext.js†L1-L55】
- **Operational controls** – configuration flags, rate limiting, logging, metrics, tracing, and Docker packaging aimed at public SaaS deployments.【F:config.py†L1-L126】【F:config.py†L128-L209】【F:src/observability/logging.py†L1-L88】【F:src/observability/metrics.py†L1-L66】【F:docker-compose.public.yml†L1-L33】

## 2. Architectural Overview

The backend is organised along layered, dependency-injected boundaries described in `docs/architecture.md`. Delivery (Flask blueprints) sits on top of domain services, which in turn depend on infrastructure adapters and persistence.【F:docs/architecture.md†L1-L121】 The composition root (`app.create_app`) wires these layers at runtime.【F:app.py†L1-L121】

### 2.1 Application Composition

`app.py` loads `.env`, instantiates Flask, applies configuration, and registers extensions such as SQLAlchemy, CORS, authentication, progress streaming, download orchestration, CD burning, and observability hooks.【F:app.py†L1-L131】【F:app.py†L133-L223】 Shared services are stored under `app.extensions` for blueprint access.【F:app.py†L134-L195】

### 2.2 Domain Services

- **Catalog domain** – `MetadataService` (Spotify metadata via Spotipy) and `LyricsService` (embedded lyrics extraction) live under `src/domain/catalog`. They provide pure Python interfaces for other services.【F:src/domain/downloads/orchestrator.py†L10-L89】
- **Downloads domain** – `DownloadOrchestrator` coordinates metadata, spotDL downloads, file management, lyrics, and repository persistence while emitting progress events.【F:src/domain/downloads/orchestrator.py†L1-L242】 `AudioCoverDownloadService` handles artwork, `FileManager` prepares directories, and `DefaultDownloadRepository` persists tracks and items via SQLAlchemy.【F:src/domain/downloads/download_service.py†L1-L188】【F:src/domain/downloads/file_manager.py†L1-L140】【F:src/domain/downloads/repository.py†L1-L153】
- **Background jobs** – `JobQueue` runs downloads asynchronously using worker threads, persists job metadata, cooperatively handles cancellation, and publishes Prometheus metrics.【F:src/domain/downloads/jobs.py†L1-L190】【F:src/domain/downloads/jobs.py†L192-L316】
- **History & favourites** – `history_service` and `repository` modules persist download history, playlists, and favourites, exposing repositories consumed by API routes.【F:src/domain/downloads/history_service.py†L1-L165】【F:src/domain/downloads/repository.py†L1-L153】
- **CD burning domain** – `CDBurningService` (Windows-only) wraps IMAPI v2 via `src/burners/imapi2_audio`, converts MP3 → WAV with `pydub`, correlates metadata, and pushes progress to the broker. `BurnSessionManager` keeps per-session state in memory for polling endpoints.【F:src/domain/burning/service.py†L1-L187】【F:src/domain/burning/sessions.py†L1-L179】

### 2.3 Cross-cutting Utilities

`src/core/progress.py` provides an in-memory Server-Sent Events (SSE) broker; `BrokerPublisher` exposes a narrow interface consumed by downloads and burner services.【F:src/core/progress.py†L1-L69】 `src/support/identity.py` resolves the acting user (explicit id → Flask-Login user → system account) for consistent persistence.【F:src/support/identity.py†L1-L33】

### 2.4 Infrastructure Adapters

`src/infrastructure/spotdl` wraps the SpotDL library with a thread-safe client, handles templating, and surfaces progress callbacks to the orchestrator.【F:src/infrastructure/spotdl/client.py†L1-L247】 This keeps third-party APIs out of domain logic and makes instrumentation easier.

### 2.5 Persistence Layer

`src/database/db_manager.py` initialises SQLAlchemy, defines `User`, `DownloadedItem`, `DownloadedTrack`, `Playlist`, `Favorite`, and `DownloadJob` models, and wires helper utilities such as `get_system_user_id` for background ownership.【F:src/database/db_manager.py†L1-L192】【F:src/database/db_manager.py†L194-L372】 Table schemas encode relationships between catalogue items and tracks, track metadata (ISRC, popularity, genres), and job bookkeeping.

### 2.6 Interface Layer

Flask blueprints under `src/interfaces/http/routes` expose REST endpoints for catalog browsing, download submission, job polling, progress streaming, playlists/favourites, configuration, and CD burning.【F:docs/architecture.md†L82-L121】 For example, `/api/progress/stream` streams SSE chunks from the broker, while `/api/config/public-config` returns deployment feature flags consumed by the frontend.【F:src/interfaces/http/routes/progress.py†L1-L43】【F:src/interfaces/http/routes/config.py†L1-L43】

### 2.7 Observability

`src/observability/logging.py` installs structured JSON logging, attaches request metadata, and optionally exports to OpenTelemetry OTLP if configured.【F:src/observability/logging.py†L1-L88】 `src/observability/metrics.py` exposes Prometheus counters, gauges, and histograms for download throughput, queue depth, and latencies via `/metrics`. Tracing bootstrap logic is housed in `src/observability/tracing.py` (OTel SDK setup).【F:src/observability/metrics.py†L1-L66】

## 3. Frontend Architecture

The React SPA lives in `frontend/` (Create React App). Key architectural elements include:

- **State & networking** – React Query (`@tanstack/react-query`) fetches API resources; `frontend/src/api` centralises endpoint definitions and HTTP helpers.【F:frontend/src/App.js†L1-L56】【F:frontend/package.json†L1-L34】
- **Routing & layout** – `App.js` wraps the app in providers (Auth, FeatureFlags, Theme, Player), defines routes for browsing, downloads, playlists, favourites, burner, and auth flows.【F:frontend/src/App.js†L1-L56】
- **Feature gating** – `FeatureFlagsContext` fetches `/api/config/public-config` and controls UI exposure for streaming and CD burning.【F:frontend/src/shared/context/FeatureFlagsContext.js†L1-L55】
- **Theming & media** – `ThemeProvider` and `PlayerProvider` coordinate Tailwind-based styling and optional in-browser playback when streaming export is allowed.【F:frontend/src/App.js†L21-L49】

## 4. External Dependencies & Tooling

- **Spotify Web API** – via Spotipy (`MetadataService`) for artist/album lookup. Requires `SPOTIPY_CLIENT_ID/SECRET` environment variables.【F:config.py†L36-L47】
- **spotDL** – CLI/library for downloading tracks from YouTube Music (default) with metadata/lyrics extraction.【F:README.md†L9-L45】【F:config.py†L55-L72】
- **SQLite & SQLAlchemy** – persistence layer stored under `src/database/instance/beathub.db` by default.【F:config.py†L28-L35】
- **pydub + ffmpeg** – audio conversion prior to CD burning.【F:src/domain/burning/service.py†L1-L43】
- **IMAPI v2 (Windows)** – built-in COM API for disc burning.【F:README.md†L105-L173】【F:src/domain/burning/service.py†L1-L85】
- **OpenTelemetry & Prometheus client** – optional telemetry exporters for logs, metrics, and traces.【F:src/observability/logging.py†L1-L88】【F:src/observability/metrics.py†L1-L66】
- **Docker/Docker Compose** – containerised public deployment with persistent download volume and optional Redis stub for future queue offloading.【F:docker-compose.public.yml†L1-L33】

## 5. Configuration & Feature Flags

All runtime behaviour is driven by `config.py`, which reads environment variables for feature toggles, queue sizing, rate limiting, CORS policies, and OpenTelemetry endpoints.【F:config.py†L1-L209】 Notable flags:

- `PUBLIC_MODE`, `ALLOW_STREAMING_EXPORT`, `ENABLE_CD_BURNER` – gate functionality for hosted vs. local deployments.【F:config.py†L73-L98】【F:README.md†L175-L210】
- `DOWNLOAD_QUEUE_WORKERS`, `DOWNLOAD_MAX_RETRIES` – control job queue concurrency.【F:config.py†L65-L72】
- `CORS_ALLOWED_ORIGINS`, `OAUTH_REDIRECT_ALLOWLIST`, `CONTENT_SECURITY_POLICY` – tighten frontend/backoffice integrations.【F:config.py†L179-L209】
- `OTEL_*` variables – enable OTLP logging/tracing exporters.【F:config.py†L107-L126】

Feature flag values are surfaced to the UI via `/api/config/public-config`, enabling runtime gating without rebuilds.【F:src/interfaces/http/routes/config.py†L1-L43】【F:frontend/src/shared/context/FeatureFlagsContext.js†L1-L55】

## 6. Data & State Flow

1. **User submits Spotify link** → `download` blueprint validates request, enqueues job in `JobQueue`, and returns job id.
2. **Job worker executes** → `DownloadOrchestrator` fetches metadata, invokes SpotDL, persists tracks/items, stores job result, and publishes progress through `ProgressBroker`.
3. **Frontend polls/SSE** → UI consumes `/api/downloads/jobs/:id` and `/api/progress/stream` for real-time updates.【F:src/interfaces/http/routes/progress.py†L1-L43】【F:src/domain/downloads/jobs.py†L1-L190】
4. **History surfaces** – persisted items and tracks power artist/album views and allow favourites/playlists via dedicated endpoints.【F:src/domain/downloads/repository.py†L1-L153】【F:docs/architecture.md†L82-L121】
5. **CD burning** – when enabled, user selects a download item, backend builds a burn plan, converts assets, and streams progress via same broker.【F:src/domain/burning/service.py†L1-L187】

## 7. Deployment Modes

- **Local development** – run Flask (`python app.py`) with React dev server for hot reloading. Default `.env` values allow streaming export and CD burning when supported.【F:README.md†L41-L74】【F:README.md†L90-L134】
- **Production / Public mode** – set `PUBLIC_MODE=1`, disable streaming/burning, and optionally run via Docker Compose (`docker-compose.public.yml`) which mounts downloads volume and exposes `/metrics`. Health is checked via `scripts/healthcheck.py`.【F:README.md†L175-L233】【F:docker-compose.public.yml†L1-L33】

## 8. Repository Topology

Supporting documentation maps the folder structure (`docs/structure.md`) and architecture layers (`docs/architecture.md`). Frontend, backend, infrastructure, and support directories align with those diagrams to keep responsibilities isolated.【F:docs/structure.md†L1-L34】【F:docs/architecture.md†L1-L155】

Together, these concepts describe how the branch delivers a full-stack Spotify download and CD-burning platform that can operate locally or as a controlled public SaaS offering.
