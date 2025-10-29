# Project Structure

Use this map when navigating the repository or wiring new modules.

## Top Level

- `app.py` - Flask application factory, wiring, and production static serving.
- `config.py` - Central configuration helpers and environment parsing.
- `requirements.txt` - Backend dependencies.
- `frontend/` - React application (development server + build artefacts).
- `docs/` - Architecture, contracts, structure, and roadmap notes.
- `downloads/` - Default output directory for downloaded media (gitignored).
- `instance/` - Holds the SQLite database and runtime settings file (`app-settings.json`).
- `src/` - Backend source code (detailed below).
- `src/log/` - Rolling log files generated at runtime.

## Backend Layout (`src/`)

- `auth/` - Flask-Login setup (`init_auth`), session handling.
- `core/` - Cross-cutting primitives such as the `ProgressBroker` and publisher interfaces.
- `domain/`
  - `catalog/` - Spotify metadata and lyrics services.
  - `downloads/` - Download orchestrator, job queue, file/metadata helpers, repositories.
  - `burning/` - CD burning workflow, IMAPI session management.
- `infrastructure/`
  - `spotdl/` - spotDL client wrapper and factory.
- `burners/` - Windows IMAPI v2 adapter (`imapi2_audio.py`).
- `interfaces/`
  - `http/routes/` - Flask blueprints segmented by responsibility (download, playlists, favorites, settings, cd_burner, auth, etc.).
- `database/` - SQLAlchemy models, database initialisation, and shared `db` handle.
- `support/` - Runtime settings helpers, user preference utilities, identity resolution.
- `models/` - DTOs and mapping helpers bridging spotDL outputs with domain objects.
- `utils/` - Shared utilities (TTL cache, cancellation primitives).

## Runtime Assets

- `downloads*/` directories - Scratch output locations used during development and tests (ignored).
- `src/database/instance/` - Default location of the SQLite file (`beathub.db`).
- `instance/app-settings.json` - Persisted runtime download settings and API keys.

## Documentation

- `docs/architecture.md` - Layered backend description.
- `docs/contracts.md` - Shared API payload contracts.
- `docs/structure.md` - This document.
- `docs/todo.md` - Roadmap/backlog checklist.
