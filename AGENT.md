# Repository Guidelines for Codex Agents

This repository already embeds many conventions. Follow the playbook below whenever you touch the codebase.

## Test & Build Commands
- Install dependencies inside the virtualenv:
  `ash
  pip install -r requirements.txt
  pip install -r requirements-dev.txt
  `
- Run the backend suite (stubs isolate external deps):
  `ash
  python -m pytest -q
  `
  Tests automatically configure a temporary SQLite database and stub SpotDL/Spotify access, so no network or audio downloads are required.
- CI mirrors the same python -m pytest -q command; keep the suite green locally before pushing.

## Coding Standards
- Python code sticks to standard PEP8/black-style formatting; keep lines sensible (< 100 chars) and prefer explicit names.
- Favor pure functions and testable units. Inject dependencies via parameters where possible; avoid hidden globals.
- Use descriptive docstrings/comments sparingly—only when logic is non-obvious.
- Tests should be deterministic and isolated (tmp paths, stubbed network). Shared fixtures live in 	ests/support/ and 	ests/conftest.py—reuse them instead of re-rolling stubs.

## Project Structure Overview
`
app.py                  # Flask app factory and wiring
config.py               # Configuration defaults/env loading
src/
  routes/               # Flask blueprints
  database/             # SQLAlchemy models & init helpers
  downloads/, lyrics/, jobs/, progress/, etc.
frontend/               # React UI (CRA)
downloads/              # Default output dir (ignored)
tests/
  unit/                 # Feature-focused test modules
  support/              # Shared factories and SpotDL/Spotify stubs
  conftest.py           # Common fixtures (DB isolation, stubs)
`
- Keep feature code alongside its domain (e.g., downloader helpers under src/download_service.py and matching tests under 	ests/unit/downloads/).
- When adding new tests, mirror this layout and use existing fixtures/stubs for cohesion and low coupling.

Stick to these guidelines and Codex will behave predictably in this repo.
