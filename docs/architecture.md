# BeatHub Architecture

BeatHub follows a layered backend architecture that keeps HTTP delivery, domain services, infrastructure adapters, and cross-cutting helpers separate. This document summarises the responsibilities of each layer and the contracts between them.

## Layer Overview

```
Interfaces (Flask blueprints)
    |
Domain services (catalog, downloads, burning)
    |
Core & support (progress, identity, runtime settings)
    |
Infrastructure adapters + persistence (spotDL, IMAPI, SQLAlchemy)
    |
Application composition (`app.py`)
```

## Composition Root (`app.py`)

- Loads configuration and environment defaults via `Config`.
- Configures logging (`configure_logging`), CORS, Flask extensions, and SQLAlchemy.
- Applies persisted runtime settings (`app_settings.apply_*`) and exposes readiness flags (`spotify_credentials_ready`, `spotdl_ready`).
- Builds singletons: `ProgressBroker`, `DownloadOrchestrator`, `JobQueue`, `CDBurningService`, `BurnSessionManager`.
- Registers HTTP blueprints from `src/interfaces/http/routes`.
- Serves the built React app from `frontend/build/`.

## Delivery Layer (`src/interfaces/http/routes`)

Blueprints provide HTTP adapters and stay thin:

- `auth.py` – registration, login, session, and profile management via Flask-Login.
- `download.py` – download requests, job queue control, metadata/lyrics/audio streaming.
- `artist.py` / `album_details.py` – Spotify catalog search, popular artists, discography.
- `compilation.py` – user curated compilation downloads.
- `playlist.py` – CRUD and track management for user playlists.
- `favorites.py` – mark/list favourite artists, albums, tracks.
- `settings.py` / `settings_status.py` – runtime download settings and credential storage.
- `cd_burning.py` – device discovery, burn sessions, cancellation, planning.
- `config.py` and `progress.py` – misc configuration endpoint and SSE progress stream.

Blueprints resolve services from `current_app.extensions`, validate payloads (Pydantic where needed), and translate domain exceptions to HTTP responses.

## Domain Layer (`src/domain`)

### Catalog (`src/domain/catalog`)
| Module | Responsibilities |
| --- | --- |
| `metadata_service.py` | Wraps Spotipy to fetch artists, albums, tracks, and curated popular playlists with caching. |
| `lyrics_service.py` | Extracts embedded lyrics from local audio and can supplement with Genius when tokens are present. |

### Downloads (`src/domain/downloads`)
| Module | Responsibilities |
| --- | --- |
| `orchestrator.py` | End-to-end download workflow: credential enforcement, metadata enrichment, spotDL orchestration, progress publication, metadata persistence. |
| `download_service.py` | Cover art and audio helpers that prepare outputs for persistence. |
| `file_manager.py` | Directory and metadata JSON management per download item. |
| `history_service.py` | Persists `DownloadedItem` records and audit history. |
| `repository.py` | `DownloadRepository` abstraction and SQLAlchemy implementation for downloaded tracks. |
| `jobs.py` | In-process job queue managing asynchronous downloads, cancellation, and retries. |

### Burning (`src/domain/burning`)
| Module | Responsibilities |
| --- | --- |
| `service.py` (`CDBurningService`) | Manages IMAPI burners, WAV conversion, burn plans, progress updates, and cancellation. |
| `sessions.py` | Thread-safe session tracking (`BurnSession`, `BurnSessionManager`) used by HTTP endpoints. |

Domain modules depend only on abstractions from `src/core`, `src/support`, and injected infrastructure adapters.

## Core & Support

| Module | Purpose |
| --- | --- |
| `src/core/progress.py` | In-memory SSE broker (`ProgressBroker`) and publisher interfaces used by downloads and burning. |
| `src/support/identity.py` | Resolves the acting user (explicit id, logged-in user, or system fallback). |
| `src/support/app_settings.py` | Persists runtime download settings and API keys in `instance/app-settings.json`, applies them to the process, and rebuilds the spotDL client. |
| `src/support/user_settings.py` | Stores per-user API keys in `User.preferences` and coordinates with runtime settings to refresh clients. |
| `src/utils/cache.py`, `src/utils/cancellation.py` | Shared utilities for TTL caches and cancellable workflows. |

These modules avoid Flask globals, making them easy to unit test.

## Infrastructure & Integrations

- `src/infrastructure/spotdl`: wraps the spotDL library (`SpotdlClient`) and exposes a factory to build configured instances with callbacks and cancellation support.
- `src/burners/imapi2_audio.py`: Windows-only COM wrapper around IMAPI v2 used by `CDBurningService`.
- Future external adapters should live alongside these modules to keep domain code insulated from third-party libraries.

## Persistence (`src/database/db_manager.py`)

SQLAlchemy models capture the persistent state:

- `User` (with Flask-Login integration and preference JSON blob).
- `DownloadedItem`, `DownloadedTrack`, `DownloadJob` (download history and queue state).
- `Playlist` / `PlaylistTrack` (user playlists with track snapshots).
- `Favorite` (user favourites with summary helpers).

`initialize_database` ensures instance folders exist, creates tables, seeds a system user, and exposes the global `db` session.

## Runtime Settings & Credential Flow

1. On startup `create_app` loads persisted settings via `app_settings.apply_api_keys` and `apply_download_settings`.
2. When a user saves credentials or download settings, `settings.py` persists them (per-user and global) and optionally rebuilds the shared spotDL client.
3. API routes that require Spotify call `ensure_user_api_keys_applied` to guarantee the active user's credentials are in effect before delegating to domain services.

## Progress & Observability

- Download and burn processes publish structured events through `ProgressBroker`. The `/api/progress/stream` endpoint emits SSE frames with heartbeats for the UI.
- `src/log/log-*.log` captures application-level logs; console output is opt-in via `ENABLE_CONSOLE_LOGS`.

## Frontend Delivery

Flask serves the compiled React bundle from `frontend/build`. During development the React dev server proxies API calls to Flask (`http://localhost:5000`), mirroring the production route structure documented above.
