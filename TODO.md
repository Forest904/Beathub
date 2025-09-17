# TODO

## Legacy CLI Cleanup — Completed
- Inventory: No standalone CLI modules, scripts, or packaging entry points found (search for `argparse`, `click`, `typer`, `__main__` blocks returned none beyond `app.py`).
- Removals: No CLI entry points to remove.
- Dependencies: Removed `rich` from `requirements.txt` as it was CLI-only and unused; retained `click` as it is required by Flask (transitively).
- Documentation: Added a "CLI Status" section to `README.md` clarifying there is no standalone CLI and that legacy helpers were retired.

## Architecture Review — Completed
- Package map:
  - `src/spotify_content_downloader.py`: Orchestrator composing metadata, file, lyrics, SpotDL client, and DB writes.
  - `src/spotdl_client.py`: SpotDL wrapper with dedicated engine thread and progress callback bridging.
  - `src/metadata_service.py`: Spotipy-based lookups for album/track/playlist metadata.
  - `src/file_manager.py`: Output directory creation and metadata JSON persistence.
  - `src/lyrics_service.py`: Embedded lyrics extraction/export via mutagen.
  - `src/jobs.py`: In-memory job queue for download requests (uses Flask app context for DB).
  - `src/progress.py`: SSE-friendly in-memory publish/subscribe broker.
  - `src/cd_burning_service.py`: CD burning logic (IMAPI2/ffmpeg on Windows) + per-session status manager.
  - `src/database/db_manager.py`: SQLAlchemy setup, models (`DownloadedItem`, `DownloadedTrack`), and initializer.
  - `src/routes/*`: Flask blueprints for artists, album details, downloads, progress SSE, CD burning.

- Data flow (happy path):
  1) HTTP → `src/routes/download_routes.py` → optional `JobQueue` → `SpotifyContentDownloader.download_spotify_content()`
  2) Orchestrator resolves `SpotdlClient` → `search` → `download_songs` → progress via `ProgressBroker` (SSE)
  3) Writes files under `BASE_OUTPUT_DIR` (`FileManager`), saves `spotify_metadata.json`, exports lyrics (`LyricsService`)
  4) Persists tracks (`DownloadedTrack`) and container (`DownloadedItem`) in DB → response dict to route
  5) Frontend listens on `/api/progress/stream` for progress.

- Coupling/cycles:
  - No circular imports detected via inspection.
  - Notable tight couplings:
    - Orchestrator accesses Flask `current_app.extensions` for broker/client.
    - Global `CD_BURN_STATUS_MANAGER` shared across routes/services.
    - Orchestrator performs DB writes directly.

- Mixed concerns found and proposed separations:
  - `src/spotify_content_downloader.py`: mixes business logic, persistence, and transport (SSE progress). Suggest:
    - Extract a `DownloadRepository` (for `DownloadedItem`/`DownloadedTrack` CRUD) and inject it.
    - Accept a `ProgressPublisher` interface instead of importing Flask `current_app`.
    - Keep orchestration focused on coordination; push IO (DB/FS) behind injected services.
  - `src/cd_burning_service.py`: mixes status management (global singleton), process execution, and policy. Suggest:
    - Move status manager to an app-scoped instance in `app.extensions` and key by burn-session ID.
    - Abstract burner/ffmpeg calls behind `BurnerAdapter` for testability.
  - `src/database/db_manager.py`: mixes model declarations with init. Suggest separating models into `src/database/models.py` and keeping init in `src/database/__init__.py`.

- Top risks and actionable refactors:
  1) Global state for burning (`CD_BURN_STATUS_MANAGER`) and direct thread access can leak state across users and invites race conditions.
     - Action: Replace singleton with per-session status objects managed by a `BurnSessionManager` in `app.extensions`; expose progress via the existing `ProgressBroker`.
  2) Orchestrator tightly coupled to Flask/runtime (`current_app`), DB, and filesystem, reducing testability and maintainability.
     - Action: Introduce interfaces (`ProgressPublisher`, `DownloadRepository`, `Storage`), inject implementations in `create_app()`, and remove `current_app` references from the orchestrator.
  3) SpotDL engine/thread and global stdout/stderr redirection (`dup2`) in `spotdl_client.py` can impact the whole process under concurrency.
     - Action: Encapsulate output suppression per subprocess where possible; gate redirection with a context flag; consider per-job clients or a semaphore to avoid cross-thread fd changes.

- Implemented:
  - Per-session burn state: `src/burn_sessions.py`; routes return `session_id` and `/status?session_id=...` reports per-session status. Wired in `app.py` and `src/routes/cd_burning_routes.py`. `src/cd_burning_service.py` now accepts a session + optional publisher.
  - Orchestrator DI: `src/spotify_content_downloader.py` now accepts `progress_publisher`, `spotdl_client`, and `download_repository` (default `DefaultDownloadRepository`). Removed hard dependency on `current_app` (kept a backward-compatible fallback for publisher only).
  - SpotDL output suppression: Added `SPOTDL_SUPPRESS_OUTPUT` env flag (default on) in `src/settings.py`; gated fd redirection + added semaphore in `src/spotdl_client.py` to avoid cross-thread interference.

Follow-ups (non-blocking):
- Consider removing unused web stack deps (`fastapi`, `uvicorn`, `starlette`) from `requirements.txt` if not needed.
- Consolidate `Config` and `AppSettings` sources; document runtime configuration in a dedicated `ARCHITECTURE.md`.

## CD Burning Feature Audit
1. Perform a code review of `src/cd_burning_service.py` and related modules, capturing bugs, unclear logic, and missing error handling.
2. Reproduce current CD burning flows end-to-end, logging failures and performance bottlenecks.
3. Draft a refactor plan covering data validation, dependency boundaries, and improved status reporting.

Immediate Fixes
Fix check_disc_status: Move the IMAPI check block into the method and return a boolean in src/cd_burning_service.py.
Protect success state: Ensure BurnSession.complete() clears is_burning; guard the finally block from overwriting success with error in burn_cd.
Validate inputs: In burn_cd, verify content_dir exists/readable and spotify_metadata.json present; fail fast with clear errors.

Device Handling
Add select_device(id): Public method to choose a recorder and set _imapi_recorder[_id]; update route usage.
Improve non‑Windows path: Early, user‑friendly error from routes when not on Windows.

Progress & Observability
Standardize phases: preparing (0–5), converting (5–50), staging (50–60), burning (60–100) with consistent ProgressPublisher payloads.
Add timing logs: Time per‑track conversion and staging totals; log at INFO for audits.

Testing
Unit tests: Cover metadata parsing, conversion filename matching (mock AudioSegment), device listing/status (mock IMAPI), and check_disc_status.
Run suite: Execute pytest -q and address regressions.

End‑to‑End Repro
Dependency check: Ensure ffmpeg on PATH, pydub and comtypes installed.
Manual burn on Windows: Blank disc inserted, list/select device, burn flow, confirm progress phases and CD‑TEXT; test cancel path.

Cleanup & Docs
Trim dead code.
Document usage: Update README with platform limits, dependencies, and burn workflow.

## Frontend Cleanup
1. Identify unused components, styles, and assets; remove them while keeping a changelog for QA.
2. Standardize component structure (naming, props, hooks) and align with the design system guidelines.
3. Resolve lint warnings and type-checking errors to enforce a stable baseline.

## Spotify Metadata Performance - Completed
- Dynamic playlist-driven popular artist sourcing with Spotipy batching and popularity sorting now lives in src/spotify_content_downloader.py.
- Metadata TTL caches in MetadataService and SpotifyContentDownloader keep repeat lookups within the SLA.

Yet TODO:

## Lyrics Component Delivery
1. Design a frontend component that displays lyrics when the user clicks the green "lyrics acquired" icon, with loading and error states defined.
2. Wire the component to existing lyrics retrieval APIs, including fallback messaging when lyrics are unavailable.
3. Add UI tests (or storybook stories) confirming the component renders, toggles visibility, and handles long lyrics gracefully.

## High-Level Follow-Ups
1. Schedule a cross-team review to align backend, frontend, and devops priorities for the next milestone.
2. Document the refactor and testing roadmap in the project wiki so stakeholders can track progress.
3. Re-evaluate resource allocation once the above tasks start, ensuring owners and timelines are confirmed.
