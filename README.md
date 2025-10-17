# BeatHub

BeatHub is a full-stack app to search artists and albums on Spotify, download Spotify content (albums, tracks, playlists) via spotDL, extract lyrics embedded by spotDL (optionally leveraging a Genius token), organize files locally, and optionally burn them to an audio CD. The backend is a Flask API with SQLite via SQLAlchemy; the web client lives in a pnpm workspace (`web/`) and a companion Expo Android client ships from `apps/mobile`.

## Features

- Search Spotify artists and view album details
- Download albums/tracks/playlists using `spotdl` (default format `mp3`)
- Extract and save embedded lyrics via SpotDL (Genius token optional)
- Store downloaded items in SQLite with metadata and paths
- Burn Audio CDs on Windows via IMAPI v2 (COM) with `pydub`/`ffmpeg` for audio prep
- React web client (Create React App) and Android Expo scaffold sharing the same data layer via `@cd-collector/shared`

## Tech Stack

- Backend: `Python 3.11+`, `Flask`, `Flask-SQLAlchemy`, `flask-cors`
- Integrations: `spotipy` (Spotify Web API), `spotdl`, `pydub`/`ffmpeg`
- DB: SQLite (file at `src/database/instance/beathub.db`)
- Web: React (CRA), `@tanstack/react-query`, Tailwind, shared monorepo packages
- Mobile: Expo (Android), NativeWind, React Query, shared monorepo packages

## Prerequisites

- Python `3.11+`
- Node.js `18+` and [pnpm](https://pnpm.io/) `9+`
- `ffmpeg` available on `PATH` (required by `pydub`)
- Windows: Uses built-in IMAPI v2 via COM (`comtypes`). No external burner CLI required.
- Non-Windows: CD burning is currently supported only on Windows; Linux/macOS are not supported in this build.
- Spotify API credentials (optional: Genius token for SpotDL lyrics)
- Expo CLI (optional) if you prefer globally installed tooling (`npm i -g expo-cli`)

## Quick Start

1. **Backend** – create a virtual environment and install dependencies:

```bash
python -m venv .venv
# PowerShell
. .venv/Scripts/Activate.ps1
python -m pip install -r requirements.txt
```

2. **Environment** – create a `.env` at the repo root:

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

3. **Install workspace dependencies** – from the repo root (Corepack keeps `pnpm@9.12.3` in sync):

```bash
corepack enable
corepack prepare pnpm@9.12.3 --activate
pnpm install
```

4. **Run the web client** – launches CRA dev server proxied to Flask (set the ESLint toggle in the shell before starting):

```bash
# PowerShell (per session)
$env:DISABLE_ESLINT_PLUGIN = "true"
pnpm dev:web
# -> http://localhost:3000 (or the next free port if prompted)
```

5. **Build the production web bundle** – generated output is served by Flask from `web/build`:

```bash
pnpm build:web
```

6. **Run the mobile (Expo) workspace** – Android only scaffold:

```bash
pnpm mobile:start    # Expo dev server with Android target
pnpm mobile:android  # Build & install native Android binary via Gradle
```

Android networking uses Expo public env vars (see `.env`):

- `EXPO_PUBLIC_EMULATOR_API_BASE_URL` (default `http://10.0.2.2:5000`)
- `EXPO_PUBLIC_DEVICE_API_BASE_URL` (set to your workstation LAN IP, e.g. `http://192.168.1.36:5000`)
- Optional `EXPO_PUBLIC_API_BASE_URL` to force both targets to the same host.

Restart Metro after changing these values.

7. **Run the backend**:

```bash
python app.py  # Starts Flask on http://localhost:5000
```

On first run, the SQLite DB and tables are created automatically.

## Developer Tooling

- `pnpm lint` � ESLint (flat config) across `web/`, `apps/mobile/`, and shared packages
- `pnpm format` / `pnpm format:write` � Prettier check/apply
- VS Code tasks (`.vscode/tasks.json`)
  - `pnpm dev:web`
  - `pnpm mobile:start`
  - `pnpm mobile:android`
- Dev server ESLint toggle: before `pnpm dev:web`, set `DISABLE_ESLINT_PLUGIN=true` in that shell (PowerShell: `$env:DISABLE_ESLINT_PLUGIN = "true"`).
- Shared package build helpers: `pnpm shared:build`, `pnpm shared:watch`
- Shared TypeScript configuration (`tsconfig.base.json`) powers both web and mobile packages
- Shared business logic lives in `packages/shared` (`@cd-collector/shared`)

## Mobile Builds (APK)

Local EAS profiles are configured in `apps/mobile/eas.json`:

```bash
pnpm mobile:apk:dev     # eas build --platform android --local --profile dev-apk
pnpm mobile:apk:release # eas build --platform android --local --profile release-apk
```

Install the resulting APK with `adb install <path-to-apk>`.

## Troubleshooting

- Missing Spotify credentials: Set `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET` in `.env`
- Missing lyrics: Not all sources embed lyrics. Setting `GENIUS_ACCESS_TOKEN` may help SpotDL fetch and embed lyrics.
- `ffmpeg` not found: Install and ensure it's on `PATH`.
- `spotdl` not found: Installed via `requirements.txt`. Ensure the app runs with the same Python where dependencies were installed.
- No burner detected (Windows): Ensure you have an optical recorder and run the app with sufficient privileges. IMAPI v2 is built into modern Windows.
- Rate limits or spotDL failures: Try lowering `SPOTDL_THREADS` (e.g., `1`), ensure your own Spotify credentials are set (used by both the app and spotDL), and consider switching audio source (`SPOTDL_AUDIO_SOURCE`) if throttling persists.
- Expo unable to reach the API: confirm Flask is running on port 5000; for remote targets export `EXPO_PUBLIC_API_BASE_URL=http://<server-ip>:5000` before launching `pnpm mobile:start`.

## Documentation

- [Architecture](docs/architecture.md)
- [Structure](docs/structure.md)
- [TODO / Roadmap](docs/todo.md)

## License

No license specified. Add one if you plan to distribute.

## CD Burning API

- Start burn: `POST /api/cd-burner/burn` with JSON `{ "download_item_id": <id> }` � returns `202 Accepted` with `{ "session_id": "..." }`.
- Poll status: `GET /api/cd-burner/status?session_id=<id>` � returns per-session state (`is_burning`, `progress_percentage`, etc.). If `session_id` is omitted, returns the most recent session.
- Progress polling: `GET /api/progress/snapshot` returns the latest event (used by mobile polling); SSE remains available at `/api/progress/stream`.

## CD Burning (Windows)

CD burning is implemented on Windows using the built-in IMAPI v2 COM interfaces. Audio preparation (MP3 + WAV) uses `pydub`, which requires `ffmpeg` on your system `PATH`.

Platform & Dependencies
- Windows 10/11 only (IMAPI v2)
- Python packages: `comtypes`, `pydub` (installed via `requirements.txt`)
- `ffmpeg` on `PATH`

Workflow
1. Insert a blank CD-R/RW into your burner.
2. List devices: `GET /api/cd-burner/devices` � shows device `id`, `present`, `writable`.
3. Select device (optional, defaults to first): `POST /api/cd-burner/select-device` with `{ "device_id": "<id>" }`.
4. Start burn: `POST /api/cd-burner/burn` with `{ "download_item_id": <id> }` for a previously downloaded item.
5. View progress: UI CD Burner page, `/api/progress/snapshot`, or `/api/progress/stream` (SSE).
6. Cancel (optional): `POST /api/cd-burner/cancel` with `{ "session_id": "..." }`.

Progress Phases
- Preparing: 0�5% (validation, device/disc checks)
- Converting: 5�50% (MP3 to WAV, per-track updates)
- Staging: 50�60% (IMAPI staging, per-track updates)
- Burning: 60�100% (disc write progress via IMAPI)

CD-TEXT
- The service sets album title/artist and per-track titles/artists when supported by the OS/device. Display varies by player.

Notes
- The service expects a `spotify_metadata.json` file in the content directory to determine track order and titles.
- Non-Windows platforms are not supported in this build.
