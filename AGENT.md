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
src/                    # Python application modules & blueprints
web/                    # React web client (CRA) within the pnpm workspace
apps/mobile/            # Expo Android client scaffold
packages/shared/        # Shared API clients, storage, React Query hooks
downloads/              # Default output dir (ignored)
```
- Keep feature code alongside its domain (e.g., downloader helpers under src/download_service.py).
- Avoid deep nesting of directories—keep related files close together.
- Separate web/mobile clients and backend code clearly.
- Do not make unit tests it would be lost tokens. 
