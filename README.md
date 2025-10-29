# BeatHub

BeatHub is a full-stack music collector that pairs a Flask backend with a React frontend to search Spotify, download content via spotDL, keep lyrics and metadata in sync, manage a local library, and burn audio CDs on Windows. The app leans on a layered architecture so the download pipeline, user experience, and external integrations stay decoupled.

## Features

- Spotify artist discovery, album lookups, curated popular artist feeds, and detailed discography retrieval.
- Download Spotify albums, tracks, playlists, or custom compilations through spotDL, backed by an in-process job queue and real-time Server-Sent Events (SSE) progress updates.
- Automatically extract embedded lyrics (with optional Genius support), persist metadata/cover art, and expose audio/lyric previews over HTTP.
- Build personal playlists from the local library with track snapshots, fast reorder support, and duplicate detection.
- Mark artists, albums, or tracks as favourites and surface summary counts for UI dashboards.
- Burn audio CDs on Windows through the IMAPI v2 stack with granular progress reporting and device management.
- Manage per-user Spotify/Genius credentials and download settings at runtime (values persist into `instance/app-settings.json` and user preference columns and override `.env` defaults without restarting the server).
- React single-page application served by Flask in production with a tailored REST API surface area.

## Architecture Highlights

The backend follows a layered layout:

- `app.py` wires configuration, logging, runtime settings, the download orchestration stack, and Flask blueprints.
- Domain packages (`src/domain`) encapsulate catalog queries, download orchestration, and CD burning workflows.
- Cross-cutting helpers live in `src/core` (progress broker), `src/support` (identity, runtime settings), and `src/utils`.
- Infrastructure adapters (`src/infrastructure`) wrap spotDL and OS-specific burners.
- Delivery logic resides in `src/interfaces/http/routes`, each blueprint fronting a cohesive slice of the API.

A deeper walkthrough lives in `docs/architecture.md`.

## Tech Stack

- Backend: Python 3.11+, Flask, Flask-SQLAlchemy, Flask-Login, flask-cors, Pydantic, Spotipy, spotDL, pydub/ffmpeg, comtypes (Windows burners).
- Database: SQLite (default file `src/database/instance/beathub.db`), SQLAlchemy models created automatically.
- Frontend: React (Create React App), axios, Tailwind (optional utilities).
- Messaging: In-memory SSE broker for download/burn progress.

## Prerequisites

- Python 3.11+
- Node.js 18+ with npm (frontend dev/build pipeline)
- ffmpeg available on your `PATH`
- Spotify API credentials (client id/secret)
- Optional: Genius API token for richer lyrics
- Windows 10/11 is required for CD burning (IMAPI v2 COM). The rest of the app runs cross-platform.

## Quick Start

1. **Create & activate a virtual environment**

   ```bash
   python -m venv .venv
   # PowerShell
   . .venv/Scripts/Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

2. **Bootstrap environment variables**

   Create `.env` in the repository root:

   ```env
   SECRET_KEY=change_me

   # Storage
   BASE_OUTPUT_DIR=downloads

   # Spotify (https://developer.spotify.com/)
   SPOTIPY_CLIENT_ID=your_spotify_client_id
   SPOTIPY_CLIENT_SECRET=your_spotify_client_secret

   # Optional: Genius token (used by spotDL for lyrics)
   GENIUS_ACCESS_TOKEN=your_genius_token

   # spotDL defaults
   SPOTDL_AUDIO_SOURCE=youtube-music
   SPOTDL_FORMAT=mp3
   SPOTDL_THREADS=2

   # Optional logging/CORS tweaks
   ENABLE_CONSOLE_LOGS=0
   CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
   ```

   Environment variables act as boot defaults. The runtime Settings API can override download configuration and API keys per user without restarting the server.

3. **Frontend**

   ```bash
   cd frontend
   npm install
   npm start        # Dev mode (http://localhost:3000)
   # or build for production:
   npm run build    # Outputs to frontend/build served by Flask
   ```

4. **Run the backend**

   ```bash
   python app.py  # Serves API on http://localhost:5000
   ```

   - On first launch the SQLite database, tables, and a system user record are created automatically.
   - Authentication is email/password based; register the first account via `/api/auth/register` or the UI.

## Runtime Settings & Credentials

- `GET /api/settings/download` surfaces the active download settings, defaults, and redacted credential status.
- `PUT /api/settings/download` stores per-user Spotify/Genius keys and download options (output directory, spotDL concurrency flags). Values are persisted under `instance/app-settings.json` and the authenticated user's `preferences` column.
- When credentials change the backend refreshes the shared spotDL client, so downloads remain available without a restart.

Settings are cached in `app.extensions` and also inform CD burning (`BASE_OUTPUT_DIR`).

## Library & Playback

- The download pipeline persists metadata to SQLite (`DownloadedItem`, `DownloadedTrack`, `DownloadJob`) and writes a comprehensive `spotify_metadata.json` alongside the audio.
- `/api/download/items/...` endpoints expose metadata, lyrics, and cover art; `/api/download/items/<id>/audio` streams local tracks for previews.
- Personal playlists and favourites are stored under `Playlist`, `PlaylistTrack`, and `Favorite` tables, available via `/api/playlists/*` and `/api/favorites/*`.

## CD Burning (Windows)

- `CDBurningService` wraps IMAPI v2 to convert audio to WAV, stage projects, and burn discs.
- `/api/cd-burner` endpoints manage device selection, burn plans, cancellations, and status checks.
- Progress updates are delivered through the shared SSE stream (`/api/progress/stream`).

## Logging & Data Folders

- Rotating log files are written to `src/log/log-YYYY-MM-DD-HH-MM-SS`.
- Downloads land under `BASE_OUTPUT_DIR` (default `downloads/`).
- Runtime settings live at `instance/app-settings.json`; the SQLite database file resides in `src/database/instance/beathub.db`.

## Documentation

- `docs/architecture.md` - Layered architecture details.
- `docs/contracts.md` - API payload contracts shared with the frontend.
- `docs/structure.md` - Project layout reference.

## License

No license is currently specified. Add one before distributing the project.
