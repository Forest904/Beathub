# Repository Guidelines for Codex Agents

This repository already embeds many conventions. Follow the playbook below whenever you touch the codebase.

## Environment Setup
- Install dependencies inside the virtualenv:
  ```
  pip install -r requirements.txt
  ```

## Coding Standards
- Python code sticks to standard PEP8/black-style formatting; keep lines sensible (< 100 chars) and prefer explicit names.
- Favor pure functions and testable units. Inject dependencies via parameters where possible; avoid hidden globals.
- Use descriptive docstrings/comments sparingly—only when logic is non-obvious.

## Project Structure Overview
```
app.py                  # Flask app factory and wiring
config.py               # Configuration defaults/env loading
src/
  routes/               # Flask blueprints
  database/             # SQLAlchemy models & init helpers
  downloads/, lyrics/, jobs/, progress/, etc.
frontend/               # React UI (CRA)
downloads/              # Default output dir (ignored)
```
- Keep feature code alongside its domain (e.g., downloader helpers under src/download_service.py).

Stick to these guidelines and Codex will behave predictably in this repo.
