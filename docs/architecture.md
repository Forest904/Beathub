# CD-Collector Architecture

The application is organised as a layered system that separates domain behaviour, cross-cutting primitives, infrastructure adapters, and delivery mechanisms. This document describes those layers, the boundaries between them, and the contracts that hold them together.

## Layered View

```
┌──────────────────────────────────────────┐
│                Interfaces                │
│  (Flask blueprints in src/interfaces/)   │
├──────────────────────────────────────────┤
│                 Domain                   │
│  downloads/ catalog/ burning/ modules    │
├──────────────────────────────────────────┤
│        Cross-cutting & Support           │
│  core/ (progress), support/ (identity)   │
├──────────────────────────────────────────┤
│             Infrastructure               │
│  spotdl adapter, external services       │
├──────────────────────────────────────────┤
│      Application Composition (app.py)    │
├──────────────────────────────────────────┤
│        Database & persistence layer      │
│  (SQLAlchemy models in src/database/)    │
└──────────────────────────────────────────┘
```

### Composition Root (`app.py`)

`app.create_app()` wires all dependencies:

- initialises configuration (`config.Config`) and Flask extensions (SQLAlchemy, CORS, login manager).
- constructs cross-cutting primitives (`ProgressBroker`, `BrokerPublisher`), infrastructure adapters (`SpotdlClient`), and domain services.
- registers routes from `src/interfaces/http/routes`.
- stores shared services in `app.extensions`:
  - `download_orchestrator`: orchestrates Spotify downloads.
  - `download_jobs`: in-process job queue for asynchronous downloads.
  - `progress_broker`: server-sent event broker.
  - `cd_burning_service`: coordinates local CD burning.
  - `burn_sessions`: tracks per-session burner state.

## Domain Layer

The `src/domain` package contains pure domain logic with explicit dependencies.

### `domain/catalog`
| Module | Responsibilities | Key Interfaces |
| --- | --- | --- |
| `metadata_service.py` | Interacts with the Spotify Web API to fetch artists, albums, and track metadata. Handles caching of responses. | Constructor accepts Spotify credentials and optional client instance. Exposes `get_album_by_id`, `get_tracks_details`, and search helpers. |
| `lyrics_service.py` | Extracts embedded lyrics from audio files and provides fallbacks for remote providers. | Methods operate on audio file paths and return extracted text; no Flask or database dependencies. |

### `domain/downloads`
| Module | Responsibilities | Key Interfaces |
| --- | --- | --- |
| `orchestrator.py` (`DownloadOrchestrator`) | Coordinates metadata lookup, SpotDL downloads, file management, repository persistence, and progress publication. All dependencies are injected (metadata service, audio helpers, lyrics service, file manager, SpotDL client, progress publisher, repository). | Public surface includes `download_spotify_content`, compilation helpers, job-oriented operations. |
| `download_service.py` | Handles cover art downloads, file sanitisation, and storage within the output directory. | Methods return file paths and raise exceptions for callers to handle. |
| `file_manager.py` | Creates item-specific directories, writes metadata JSON, and cleans up partial downloads. | Stateless helper using base output path injected by orchestrator. |
| `repository.py` | Defines `DownloadRepository` interface and SQLAlchemy-backed `DefaultDownloadRepository`. Resolves acting user through `support.identity.resolve_user_id`. | `save_tracks(tracks, user_id=None)` persists or updates rows in `DownloadedTrack`. |
| `history_service.py` | Persists high-level download history (`DownloadedItem`) after successful downloads. | Called from routes and job queue. |
| `jobs.py` (`JobQueue`) | Manages the asynchronous download queue. Depends on orchestrator, SQLAlchemy session, and `support.identity`. | Exposes `submit`, `get`, `wait`, `request_cancel`. Publishes progress through the common broker. |

### `domain/burning`
| Module | Responsibilities | Key Interfaces |
| --- | --- | --- |
| `service.py` (`CDBurningService`) | Provides high-level burning workflow: device enumeration, track matching, WAV conversion, IMAPI interaction, and progress reporting. Injected with base output directory, `LyricsService`, `ProgressPublisher`. | Methods `burn_cd`, `generate_burn_plan`, `list_devices_with_status`, `request_cancel`. |
| `sessions.py` (`BurnSession`, `BurnSessionManager`) | Thread-safe state holders for per-session burner status. | Used by routes to check/track progress without global mutability. |

## Cross-cutting Utilities

| Module | Purpose |
| --- | --- |
| `src/core/progress.py` | Defines `ProgressBroker` (in-memory SSE pub/sub) and `ProgressPublisher` abstraction. |
| `src/support/identity.py` | Resolves acting user based on explicit value, Flask-Login context, or system user fallback. |

These modules are dependency-free and can be reused across domain services.

## Infrastructure Layer

| Module | Responsibilities |
| --- | --- |
| `src/infrastructure/spotdl/client.py` | Thread-safe wrapper around the SpotDL library. Manages engine thread, output template, progress callbacks, and cancellation. |
| `src/infrastructure/spotdl/__init__.py` | Exposes `SpotdlClient` factory `build_default_client`. |

Additional adapters can be added here (e.g., storage providers, external APIs) without leaking into domain logic.

## Interface Layer (Delivery)

`src/interfaces/http/routes` contains Flask blueprints that:

- resolve services from `current_app.extensions`.
- validate/serialise HTTP payloads.
- invoke domain services and manage HTTP semantics (status codes, errors).

Blueprints include:

- `download.py`: handles download requests, job queue interactions, history listing, metadata streaming.
- `artist.py`, `album_details.py`: expose catalog endpoints.
- `compilation.py`: handles user-defined compilations.
- `cd_burning.py`: exposes burning workflows (status, devices, preview, burn, cancel).
- `progress.py`: serves SSE stream for progress updates.
- `auth.py`, `config.py`: authentication and configuration endpoints.

## Database Layer

`src/database/db_manager.py` provides SQLAlchemy models:

- `User`, `DownloadedItem`, `DownloadedTrack`, `DownloadJob`.
- `initialize_database(app)` ensures tables exist and system user is created.

Domain repositories interact with these models through SQLAlchemy sessions.

## Interface Contracts Summary

| Contract | Provider | Consumer |
| --- | --- | --- |
| `ProgressPublisher.publish(event: dict)` | `core.progress.BrokerPublisher` | `DownloadOrchestrator`, `CDBurningService`, job queue |
| `DownloadRepository.save_tracks(tracks, user_id=None)` | `domain.downloads.repository.DefaultDownloadRepository` | `DownloadOrchestrator` |
| `resolve_user_id(explicit=None)` | `support.identity` | repositories, job queue, compilation history |
| `SpotdlClient` methods (`set_output_template`, `set_progress_callback`, `download`) | `infrastructure.spotdl.client` | `DownloadOrchestrator`, job queue |
| `BurnSessionManager` API (`create`, `get`, `last`, `is_any_burning`, `cleanup_finished`) | `domain.burning.sessions` | burning routes, `CDBurningService` |

All contracts are Python classes or functions that can be mocked or replaced for testing and future extensions.

## Responsibility Matrix

| Subsystem | Primary Responsibilities | Key Files |
| --- | --- | --- |
| Composition & Routing | Application bootstrap, HTTP delivery, auth, config | `app.py`, `src/interfaces/http/routes/*`, `src/auth/__init__.py` |
| Catalog Domain | Metadata enrichment, lyrics extraction | `src/domain/catalog/*` |
| Downloads Domain | Spotify downloads, job orchestration, history persistence | `src/domain/downloads/*` |
| Burning Domain | CD burning workflows, session management | `src/domain/burning/*` |
| Cross-cutting | Progress streaming, identity resolution | `src/core/*`, `src/support/*` |
| Infrastructure | SpotDL integration and external adapters | `src/infrastructure/*` |
| Persistence | SQLAlchemy models and DB initialisation | `src/database/db_manager.py` |

## Future Considerations

- **Storage abstraction**: introduce interfaces for filesystem operations to enable remote storage providers.
- **Durable queue**: replace in-process job queue with a persistent task runner if long-running downloads need resiliency.
- **Observability**: layer structured logging and metrics around orchestrator and burning service calls.
- **Public mode**: leverage feature flags (e.g., `PUBLIC_MODE`) to disable burning/navigation features in cloud deployments.

By keeping the layers explicit and the contracts narrow, new delivery mechanisms (CLI, REST v2) or infrastructure adapters (cloud storage, worker processes) can be added without touching core domain logic.
