# TODO

## Make Your Compilation Feature
- [ ] Add a "Make Your Own Compilation" button on the DiscoverArtists page.
- [ ] Make the button change appearance while in compilation mode so the user knows the compilation has items in it.
- [ ] Create a `Compilation` sidebar component that opens from the left when the button is clicked.
- [ ] Allow users to add/remove songs while browsing artists (cart-like experience).
- [ ] Prompt for a compilation name on first click and allow editing later.
- [ ] At the bottom of the Compilation component have a direct download button working same as the others.

### Plan
- Scope: Let users collect tracks from album/artist views into a temporary "Compilation" cart, name it, re-order it, and kick off a download exactly like other items.
- State: A `CompilationContext` in the frontend stores `{ name, items[], totalMs }`, persisted to `localStorage` (with versioning).
- UX: Toggle button enters/leaves Compilation Mode. While active, track rows expose an "Add"/"Remove" control. A left drawer shows current selection, total duration, and the download CTA.
- Backend: New endpoint to accept a list of Spotify track URLs/IDs and orchestrate spotDL downloads into a compilation folder named after the cart.

### Batches

Batch 1 — Foundation and UI scaffold
- [ ] Frontend: Create `frontend/src/compilation/CompilationContext.jsx` with API: `add(track)`, `remove(spotify_id)`, `clear()`, `rename(name)`, `reorder(from,to)`, and `isInCompilation(id)`; persist to `localStorage` (key `compilation:v1`).
- [ ] Frontend: Add a `CompilationToggle` button to `ArtistBrowserPage` header area; store `compilationMode` in a top-level state (or context) so all pages can check it.
- [ ] Frontend: Style the toggle with an item-count badge (`0` hidden; >0 shows count) and active state.
- [ ] Frontend: Scaffold `CompilationSidebar.jsx` as a left drawer (fixed, portal to `body`) with: name input, list of items, total duration, Clear, and Close.
- [ ] Acceptance: Toggling works, sidebar opens/closes, name persists, and items state is visible (stubbed items ok).

Batch 2 — Add/remove from track sources
- [ ] Frontend: In `AlbumDetailsPage`, switch track rendering to use `TrackListRich` with an extra column when `compilationMode` is on: an Add/Remove button reflecting membership.
- [ ] Frontend: Ensure track objects passed to `TrackListRich` include `spotify_id`, `title`, `artists[]`, `duration_ms`, and `albumId` (for context).
- [ ] Frontend: Add lightweight hover Add/Remove affordance in `ArtistDetailsPage` Best-Of pseudo-album (if applicable) and any other track lists.
- [ ] Frontend: In `CompilationSidebar`, implement Remove and drag-and-drop reorder (e.g., `react-beautiful-dnd` or simple up/down controls first; DnD later).
- [ ] Acceptance: Can add/remove tracks while browsing; sidebar reflects changes immediately; reordering updates order index and total minutes.

Batch 3 — Backend orchestration and download
- [ ] Backend: Add `src/routes/compilation_routes.py` with `POST /api/compilations/download` accepting `{ name: str, tracks: [{spotify_id|string|url, title, artists[], duration_ms}] }`.
- [ ] Backend: In `SpotifyContentDownloader`, add method `download_compilation(tracks, name)` that: resolves each track (URL/ID), downloads via spotDL into `BASE_OUTPUT_DIR/Compilations/<name-YYYYMMDD-HHMM>`; writes a manifest.json; returns a synthetic item record.
- [ ] Backend: Integrate with `JobQueue` for async; publish progress via existing `ProgressBroker` (use `compilation:<name>` job id/topic).
- [ ] Frontend: Hook sidebar "Direct Download" CTA to call the new endpoint (async), open/attach to progress panel (same component as downloads), and on completion, route user to history with the new compilation selected.
- [ ] Acceptance: Kicks off a compilation download that appears in history; progress panel shows aggregated progress.

Batch 4 — Polish and guardrails
- [ ] Frontend: Show CD time budget (e.g., 80 min via `Config.CD_CAPACITY_MINUTES`) and warn when exceeding; badge turns warning when >80min.
- [ ] Frontend: Add "Save as .m3u" button in sidebar (client-side) to export current queue (nice-to-have).
- [ ] Backend: Reject over-large requests (e.g., >200 tracks) and sanitize compilation name for filesystem.
- [ ] Frontend: Persistent restore of cart across reloads; confirm Clear action; disable download when cart empty.
- [ ] Acceptance: Smooth UX, clear warnings, sensible limits, and basic input sanitization.

## Song Previews
- [ ] Retrieve 10-second song previews during artist discovery (e.g., via Spotipy if available).
- [ ] Add a quick-play button to preview tracks inline.

### Plan
- Goal: Enable inline, short previews for tracks on album/artist views without requiring a prior download.
- Source: Prefer Spotify `preview_url` (often 30s MP3). If missing, skip or future-fallback to another provider.
- Delivery: Backend proxy endpoint streams preview bytes to avoid CORS and to allow truncation to ~10s if needed.
- UI: Play button in track rows wires into the existing `PlayerContext` with a "preview" queue.

### Batches

Batch 1 — Backend preview proxy
- [ ] Add `GET /api/preview/<track_id>`: uses Spotipy `sp.track(track_id)` to fetch `preview_url` and caches mapping in LRU (TTL from `Config.METADATA_CACHE_TTL_SECONDS`).
- [ ] If `preview_url` exists, proxy-stream it to the client (requests `stream=True`); optionally apply `Range` passthrough. If enforcing ~10s, stop after N bytes or return `206` with `Content-Range` approximating 10s for MP3.
- [ ] Add `HEAD /api/preview/<track_id>` to quickly test availability and type.
- [ ] Errors: 404 when no preview_url, 502 on remote stream error, 429 with basic rate-limiter if needed.

Batch 2 — Frontend integration
- [ ] Album details: Render `TrackListRich` with `enablePlay` and provide `onPlayTrack` that builds preview URLs: `/api/preview/${track.spotify_id}`.
- [ ] Artist details: Add a "Top Tracks" section above discography using Spotipy `artist_top_tracks` (new endpoint) and the same preview handling.
- [ ] Player: No code changes expected; it plays any `audioUrl`. Ensure player state distinguishes preview vs local by title suffix or metadata flag (optional).
- [ ] Visuals: Show a small "Preview" badge when the audio source is a preview.

Batch 3 — UX polish and fallback
- [ ] Gracefully hide play buttons when `HEAD /api/preview/:id` responds 404 for many tracks.
- [ ] Preload small batches of availability (HEAD) to avoid click-time delays; cache on client.
- [ ] Optional future: add YT Music short-clip fallback for tracks without Spotify previews.


## Steps for online publication (no burning feature)

### Plan
- Publish a "cloud mode" build where CD-burning and local-file serving is disabled, while discovery and downloads remain available.
- Deliver via container image and simple reverse proxy; secure keys via env vars.

### Batches

Batch 1 — Feature flags and hardening
- [ ] Config: Add `PUBLIC_MODE=1` and `ENABLE_CD_BURNER=0` flags. In `app.create_app()`, conditionally skip `CDBurningService` and the CD routes.
- [ ] Backend: Gate `/api/items/*` streaming endpoints behind `PUBLIC_MODE=0` (return 403 in public mode) to avoid serving local files remotely.
- [ ] Frontend: Hide the "CD Burner" nav/page behind a feature flag fetched from `/api/config` (new tiny endpoint exposing public caps).
- [ ] CORS: Restrict origins via env when in public mode.
- [ ] Acceptance: App runs with burning hidden/disabled; local streaming APIs blocked in public mode.

Batch 2 — Build and deploy
- [ ] Dockerfile: Multi-stage build to compile React (`frontend/build`) and package Flask app; serve static via Flask or (optionally) Nginx.
- [ ] Compose: `docker-compose.yml` with one service, volume-mounted `downloads/`, env for Spotify/Genius keys.
- [ ] Reverse proxy: Example Nginx config with HTTPS, gzip, and caching headers for static.
- [ ] Acceptance: One-command run serves the app on HTTPS with all non-burning features.

Batch 3 — Observability and quotas
- [ ] Logging: Route app logs to stdout and file; redact secrets.
- [ ] Metrics (optional): Add `/healthz` and `/readyz`; basic request timing logs.
- [ ] Rate limits: Apply simple IP-based limits on preview and download start endpoints.
- [ ] Acceptance: Health endpoints green, logs useful for ops, rate-limits in place.

Batch 4 — Docs
- [ ] README: Public-mode instructions, required env vars, how to rotate keys, and how to disable public mode locally.
- [ ] Security notes: Keys, allowed origins, and common pitfalls.

## Steps for executable packaging 

### Plan
- Ship a desktop-friendly package (Windows first) bundling Flask backend and built React assets, launching the app and opening the default browser.

### Batches

Batch 1 — PyInstaller POC
- [ ] Create `entrypoint.py` that calls `create_app()` and `app.run()` with `DEBUG=False` and `threaded=True`.
- [ ] PyInstaller spec: include `frontend/build` as data, and mark hidden imports used by SpotDL/Spotipy.
- [ ] Ensure `.env` is optional; document env fallbacks.
- [ ] Acceptance: Single-folder dist runs on a clean Windows VM.

Batch 2 — Assets and config
- [ ] Verify static routing (`static_folder='frontend/build'`) resolves in frozen app; adjust relative paths if needed.
- [ ] Bundle default `ffmpeg` discovery notes; prefer system `ffmpeg` with clear error message if missing.
- [ ] Add version resource info (Windows icon, product name) to the executable.
- [ ] Acceptance: Frontend loads, downloads work, logs write to `%LOCALAPPDATA%/CD-Collector/log`.

Batch 3 — One-file and installer (optional)
- [ ] Test one-file mode; if startup time is acceptable, ship as alternative.
- [ ] Build an NSIS/Inno Setup installer with Start Menu shortcut and file associations (optional).
- [ ] Acceptance: Install/uninstall lifecycle verified; app auto-opens browser on first run.

Batch 4 — Cross-platform notes
- [ ] macOS: Test codesigning requirements; provide `venv + pyinstaller` recipe.
- [ ] Linux: Provide `.deb`/AppImage instructions or fallback to Docker.

## Steps for telegram bot

### Plan
- A minimal Telegram bot to trigger downloads, track progress, and return results (links to files or status). Restrict access to allowed user IDs.

### Batches

Batch 1 — Bootstrap
- [ ] Add `src/bots/telegram_bot.py` using `python-telegram-bot` (v20+). Read `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USER_IDS` from env.
- [ ] Commands: `/start`, `/help`, `/download <spotify_link>`, `/status <job_id>`.
- [ ] Wire `/download` to submit a job via existing `JobQueue` (async) and return the job id.
- [ ] Acceptance: Local bot responds; submits jobs; `/status` reflects queue state.

Batch 2 — Progress and results
- [ ] Subscribe the bot to `ProgressBroker` updates (in-process) to push progress messages back to the chat.
- [ ] On completion, reply with a summary (item type, title, tracks). If running locally, offer a path; if public, offer a signed, time-limited download link (future).
- [ ] Errors: Send a friendly failure message and include the logged error code.
- [ ] Acceptance: End-to-end flow works for album/playlist/track links.

Batch 3 — Deployment and safety
- [ ] Add a small runner `python -m src.bots.telegram_bot` with graceful shutdown.
- [ ] Containerize the bot (optional) or run alongside the app; document systemd service.
- [ ] Rate-limit per user (simple token bucket) and validate links to be Spotify only.
- [ ] Acceptance: Bot remains responsive under load and rejects unknown users.
