# BeatHub

BeatHub is a full-stack app to search artists and albums on Spotify, download Spotify content (albums, tracks, playlists) via spotDL, extract lyrics embedded by spotDL (optionally leveraging a Genius token), organize files locally, and optionally burn them to an audio CD. The backend is a Flask API with SQLite via SQLAlchemy; the frontend is a React app served by Flask in production.

## Features

- Search Spotify artists and view album details
- Download albums/tracks/playlists using `spotdl` (default format `mp3`)
- Extract and save embedded lyrics via SpotDL (Genius token optional)
- Store downloaded items in SQLite with metadata and paths
- Burn Audio CDs on Windows via IMAPI v2 (COM) with `pydub`/`ffmpeg` for audio prep
- React UI (Create React App) with API proxy to the Flask server

## Tech Stack

- Backend: `Python 3.11+`, `Flask`, `Flask-SQLAlchemy`, `flask-cors`
- Integrations: `spotipy` (Spotify Web API), `spotdl`, `pydub`/`ffmpeg`
- DB: SQLite (file at `src/database/instance/beathub.db`)
- Frontend: React (CRA), `axios`, Tailwind (optional)

## Prerequisites

- Python `3.11+`
- Node.js `18+` and npm (for the frontend)
- `ffmpeg` available on `PATH` (required by `pydub`)
- Windows: Uses built-in IMAPI v2 via COM (`comtypes`). No external burner CLI required.
- Non-Windows: CD burning is currently supported only on Windows; Linux/macOS are not supported in this build.
- Spotify API credentials (optional: Genius token for SpotDL lyrics)

## Quick Start

1) Clone and set up Python environment

```bash
python -m venv .venv
# PowerShell
. .venv/Scripts/Activate.ps1
python -m pip install -r requirements.txt
```

2) Create a `.env` at the repo root

```env
# Flask
SECRET_KEY=change_me

# Storage
BASE_OUTPUT_DIR=downloads

# Spotify (https://developer.spotify.com/)
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret

# Optional: Genius token (used by SpotDL for lyrics)
GENIUS_ACCESS_TOKEN=your_genius_token

# spotDL (optional)
SPOTDL_AUDIO_SOURCE=youtube-music
SPOTDL_FORMAT=mp3
# Limit spotDL concurrency (helps avoid provider rate limits)
SPOTDL_THREADS=1
```

3) Frontend (development or production)

- Dev mode (recommended while iterating UI):
  ```bash
  cd frontend
  npm install
  npm start
  # Opens http://localhost:3000, proxies API to http://localhost:5000
  ```
- Production build served by Flask:
  ```bash
  cd frontend
  npm install
  npm run build  # creates frontend/build used by Flask static serving
  ```

4) Run the backend

```bash
python app.py  # Starts Flask on http://localhost:5000
```

On first run, the SQLite DB and tables are created automatically.

## CLI Status

- No standalone CLI commands or entry points are shipped.
- Legacy CLI helpers have been retired; interact via the Flask HTTP API and the React UI.
- No external consumers depend on a CLI interface at this time.

## Troubleshooting

- Missing Spotify credentials: Set `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET` in `.env`
- Missing lyrics: Not all sources embed lyrics. Setting `GENIUS_ACCESS_TOKEN` may help SpotDL fetch and embed lyrics.
- `ffmpeg` not found: Install and ensure it's on `PATH`.
- `spotdl` not found: Installed via `requirements.txt`. Ensure the app runs with the same Python where dependencies were installed.
- No burner detected (Windows): Ensure you have an optical recorder and run the app with sufficient privileges. IMAPI v2 is built into modern Windows.
- Rate limits or spotDL failures: Try lowering `SPOTDL_THREADS` (e.g., `1`), ensure your own Spotify credentials are set (used by both the app and spotDL), and consider switching audio source (`SPOTDL_AUDIO_SOURCE`) if throttling persists.

## Development

- Lint/format: not configured; follow existing style
- Do not commit the SQLite DB or `downloads/` directory
- Environment variables are loaded via `python-dotenv` from `.env`

## Documentation

- [Architecture](docs/architecture.md)
- [Structure](docs/structure.md)
- [TODO / Roadmap](docs/todo.md)

## License

No license specified. Add one if you plan to distribute.

## Tests

Run the backend test suite from the repository root:

```bash
python -m pytest -q
```

Install dev dependencies first if you have not already:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

Tests automatically isolate their database storage and stub external SpotDL/Spotify calls, so the suite runs quickly without network access.

## CD Burning API

- Start burn: `POST /api/cd-burner/burn` with JSON `{ "download_item_id": <id> }` — returns `202 Accepted` with `{ "session_id": "..." }`.
- Poll status: `GET /api/cd-burner/status?session_id=<id>` — returns per-session state (`is_burning`, `progress_percentage`, etc.). If `session_id` omitted, returns the most recent session.

## CD Burning (Windows)

CD burning is implemented on Windows using the built-in IMAPI v2 COM interfaces. Audio preparation (MP3 → WAV) uses `pydub`, which requires `ffmpeg` on your system `PATH`.

Platform & Dependencies
- Windows 10/11 only (IMAPI v2)
- Python packages: `comtypes`, `pydub` (installed via `requirements.txt`)
- `ffmpeg` on `PATH`

Workflow
1. Insert a blank CD-R/RW into your burner.
2. List devices: `GET /api/cd-burner/devices` — shows device `id`, `present`, `writable`.
3. Select device (optional, defaults to first): `POST /api/cd-burner/select-device` with `{ "device_id": "<id>" }`.
4. Start burn: `POST /api/cd-burner/burn` with `{ "download_item_id": <id> }` for a previously downloaded item.
5. View progress: UI CDBurner page or connect to `/api/progress/stream` (SSE).
6. Cancel (optional): `POST /api/cd-burner/cancel` with `{ "session_id": "..." }`.

Progress Phases
- Preparing: 0–5% (validation, device/disc checks)
- Converting: 5–50% (MP3 to WAV, per-track updates)
- Staging: 50–60% (IMAPI staging, per-track updates)
- Burning: 60–100% (disc write progress via IMAPI)

CD-TEXT
- The service sets album title/artist and per-track titles/artists when supported by the OS/device. Display varies by player.

Notes
- The service expects a `spotify_metadata.json` file in the content directory to determine track order and titles.
- Non-Windows platforms are not supported in this build.

