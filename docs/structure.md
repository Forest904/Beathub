# Project Structure

## Backend

- `app.py` - Flask app factory, blueprint registration, SPA static serving.
- `config.py` - central configuration: database URL, client credentials, output directories.
- `src/` - backend modules grouped by responsibility:
  - `database/` - SQLAlchemy setup (`db_manager.py`), models, init helpers.
  - `downloads/` - utilities for file management, cover/metadata handling.
  - `jobs/`, `progress/` - background queue & event broker.
  - `lyrics_service.py`, `metadata_service.py`, `spotify_content_downloader.py`, etc.
  - `routes/` - Flask blueprints (`download`, `artist`, `album_details`, `cd_burning`, `progress`).

## Web Client

- `web/` - Create React App hosted inside the pnpm workspace. Production assets are emitted to `web/build/` and served by Flask when present. Shares logic via `@cd-collector/shared`.

## Mobile Client

- `apps/mobile/` - Expo-managed Android application scaffolded with NativeWind and shared data layer bindings. See `apps/mobile/app.config.ts` & `apps/mobile/eas.json` for build configuration.

## Shared Packages

- `packages/shared/` - TypeScript package consumed by both clients. Provides API endpoints, HTTP client, React Query hooks, storage abstractions, and eventing helpers.

## Data & Runtime Assets

- `downloads/`, `downloads-test/`, `test_downloads/`, `t_out/` - local artifact directories (ignored from VCS).
- `instance/` - Flask instance folder; holds SQLite database files by default.

## Tooling & Configuration

- `requirements.txt` - Python runtime dependencies.
- `package.json` / `pnpm-workspace.yaml` - pnpm workspace definition and shared scripts.
- `.gitignore` - ignores virtualenvs, caches, coverage, and download artifacts.
- `AGENT.md` - quick-start guidelines for Codex agents working in this repository.

## Documentation

- `README.md` - project overview and setup instructions.
- `docs/structure.md` (this file) - high-level directory map.
