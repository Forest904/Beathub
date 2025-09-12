# CD-Collector

CD-Collector is a full‑stack app to search artists and albums on Spotify, download Spotify content (albums, tracks, playlists) via spotDL, fetch lyrics from Genius, organize files locally, and optionally burn them to an audio CD. The backend is a Flask API with SQLite via SQLAlchemy; the frontend is a React app served by Flask in production.

## Features

- Search Spotify artists and view album details
- Download albums/tracks/playlists using `spotdl` (default format `mp3`)
- Fetch and save lyrics via Genius API
- Store downloaded items in SQLite with metadata and paths
- Burn audio CDs from downloaded content via `cdrecord`/`wodim` + `ffmpeg`
- React UI (Create React App) with API proxy to the Flask server

## Tech Stack

- Backend: `Python 3.11+`, `Flask`, `Flask-SQLAlchemy`, `flask-cors`
- Integrations: `spotipy` (Spotify Web API), `spotdl`, `lyricsgenius`, `pydub`/`ffmpeg`
- DB: SQLite (file at `database/instance/cd_collector.db`)
- Frontend: React (CRA), `axios`, Tailwind (optional)

## Prerequisites

- Python `3.11+`
- Node.js `18+` and npm (for the frontend)
- `ffmpeg` available on `PATH` (required by `pydub`)
- `cdrecord`/`wodim` available on `PATH` for CD burning (Linux/macOS). On Windows, you may need compatible cdrtools or adapt the burning command.
- Spotify and Genius API credentials

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

# Genius (https://genius.com/api-clients)
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

## Project Structure

- `app.py`: Flask app factory, blueprint registration, static serving
- `config.py`: Configuration (DB URI, API keys, base output dir)
- `database/db_manager.py`: SQLAlchemy setup and `DownloadedItem` model
- `src/spotify_content_downloader.py`: Orchestrates metadata, audio, cover, lyrics, files
- `src/download_service.py`: spotDL invocation and cover download
- `src/metadata_service.py`: Spotify metadata via `spotipy`
- `src/lyrics_service.py`: Lyrics via `lyricsgenius`
- `src/file_manager.py`: File/dir creation and JSON metadata saving
- `src/routes/*.py`: API routes (downloads, artists, album details, CD burner)
- `frontend/`: React app (CRA). Built assets at `frontend/build`
- `downloads/`: Default output root for downloaded content

## API Overview

- `POST /api/download`: Download a Spotify item
  - Body: `{ "spotify_link": "https://open.spotify.com/..." }`
  - Success: metadata, output paths, tracks, cover path

- `GET /api/albums`: List downloaded items from DB
- `DELETE /api/albums/:id`: Remove DB row and local files

- `GET /api/search_artists?q=term`: Search Spotify artists
- `GET /api/famous_artists`: Curated famous artists list
- `GET /api/artist_details/:artist_id`: Artist profile
- `GET /api/artist_discography/:artist_id`: Albums and singles

- `GET /api/album_details/:album_id`: Album with tracks

- CD Burning
  - `GET /api/cd-burner/status`: Poll burn state/progress
  - `POST /api/cd-burner/burn`: Start burn for a downloaded item
    - Body: `{ "download_item_id": 123 }`

## How Downloads Are Organized

- Root folder: `downloads/` (configurable via `BASE_OUTPUT_DIR`)
- Per item: `downloads/<Artist> - <Title>/`
  - Audio: `<Title>.<ext>` (`mp3` by default)
  - Cover: `cover.jpg` (if available)
  - Metadata: `spotify_metadata.json`
  - Lyrics: `"<Track Title> - <Artist>.txt"` (when found)

## CD Burning Notes

- Converts MP3 to WAV via `pydub`/`ffmpeg` before burning
- Uses `cdrecord -scanbus` to detect burner and `cdrecord` to burn
- Requires a blank/erasable disc; progress is exposed via `/api/cd-burner/status`
- Linux/macOS recommended. Windows may require installing cdrtools and adjusting paths.

## Configuration Tips

- spotDL format/source/threads: Defaults are `mp3`, `youtube-music`, and `1` thread. Configure via env vars `SPOTDL_FORMAT`, `SPOTDL_AUDIO_SOURCE`, and `SPOTDL_THREADS`, or change defaults in `src/download_service.py`.
- DB file: Default is `database/instance/cd_collector.db` (configured in `config.py`). Created on startup.
- Static build: Flask serves `frontend/build` when present. During dev, use CRA dev server with the proxy.

## Troubleshooting

- Missing Spotify credentials: Set `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET` in `.env`
- Lyrics not downloading: Ensure `GENIUS_ACCESS_TOKEN` is set
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
