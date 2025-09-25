# Project Structure

## Backend
- `app.py` - Flask app factory, blueprint registration, SPA static serving.
- `config.py` - central configuration: database URL, client credentials, output directories.
- `src/` - backend modules grouped by responsibility:
  - `database/` - SQLAlchemy setup (`db_manager.py`), models, init helpers.
  - `downloads/` - utilities for file management, cover/metadata handling.
  - `jobs/`, `progress/` - background queue & server-sent events broker.
  - `lyrics_service.py`, `metadata_service.py`, `spotify_content_downloader.py`, etc.
  - `routes/` - Flask blueprints (`download`, `artist`, `album_details`, `cd_burning`, `progress`).

## Frontend
- `frontend/` - React application (Create React App). Production build output lives in `frontend/build/`, served by Flask when present.

## Data & Runtime Assets
- `downloads/`, `downloads-test/`, `test_downloads/`, `t_out/` - local artifact directories (ignored from VCS).
- `instance/` - Flask instance folder; holds SQLite database files by default.

## Tooling & Configuration
- `requirements.txt` - runtime dependencies.
- `.gitignore` - ignores virtualenvs, caches, coverage, and download artifacts.
- `AGENT.md` - quick-start guidelines for Codex agents working in this repository.

## Documentation
  - `README.md` - project overview and setup instructions.
- `docs/structure.md` (this file) - high-level directory map.


