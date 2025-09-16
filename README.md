# CD-Collector

[![Tests](https://github.com/LucaForesti/CD-Collector/actions/workflows/tests.yml/badge.svg)](https://github.com/LucaForesti/CD-Collector/actions/workflows/tests.yml)

CD-Collector is a full-stack app to search artists and albums on Spotify, download Spotify content (albums, tracks, playlists) via spotDL, extract lyrics embedded by spotDL (optionally leveraging a Genius token), organize files locally, and optionally burn them to an audio CD. The backend is a Flask API with SQLite via SQLAlchemy; the frontend is a React app served by Flask in production.

## Features

- Search Spotify artists and view album details
- Download albums/tracks/playlists using `spotdl` (default format `mp3`)
- Extract and save embedded lyrics via SpotDL (Genius token optional)
- Store downloaded items in SQLite with metadata and paths
- Burn audio CDs from downloaded content via `cdrecord`/`wodim` + `ffmpeg`
- React UI (Create React App) with API proxy to the Flask server

## Tech Stack

- Backend: `Python 3.11+`, `Flask`, `Flask-SQLAlchemy`, `flask-cors`
- Integrations: `spotipy` (Spotify Web API), `spotdl`, `pydub`/`ffmpeg`
- DB: SQLite (file at `database/instance/cd_collector.db`)
- Frontend: React (CRA), `axios`, Tailwind (optional)

## Prerequisites

- Python `3.11+`
- Node.js `18+` and npm (for the frontend)
- `ffmpeg` available on `PATH` (required by `pydub`)
- `cdrecord`/`wodim` available on `PATH` for CD burning (Linux/macOS). On Windows, you may need compatible cdrtools or adapt the burning command.
- Spotify API credentials (optional: Genius token for SpotDL lyrics)

## Quick Start

1) Clone and set up Python environment

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: . .venv/Scripts/Activate.ps1
pip install -r requirements.txt
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


## Troubleshooting

- Missing Spotify credentials: Set `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET` in `.env`
- Missing lyrics: Not all sources embed lyrics. Setting `GENIUS_ACCESS_TOKEN` may help SpotDL fetch and embed lyrics.
- `ffmpeg` not found: Install and ensure it’s on `PATH`
- `spotdl` not found: Installed via `requirements.txt`. Ensure the app runs with the same Python where dependencies were installed
- No burner detected: Verify `cdrecord`/`wodim` is installed and accessible; try running with admin/root if required
- Rate limits or spotDL failures: Try lowering `SPOTDL_THREADS` (e.g., `1`), ensure your own Spotify credentials are set (used by both the app and spotDL), and consider switching audio source (`SPOTDL_AUDIO_SOURCE`) if throttling persists.


## Development

- Lint/format: not configured; follow existing style
- Do not commit the SQLite DB or `downloads/` directory
- Environment variables are loaded via `python-dotenv` from `.env`

## License

No license specified. Add one if you plan to distribute.


## Tests

Run the backend test suite from the repository root:

```bash
python -m pytest -q
```

Install dev dependencies first if you have not already:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Tests automatically isolate their database storage and stub external SpotDL/Spotify calls, so the suite runs quickly without network access.


