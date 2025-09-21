# TODO

### Completed (Covers and Selection)
- [x] Frontend: Album cards render covers in a fixed 1:1 square (object-cover) with 640×640 hints.
- [x] Frontend: Download page toggles selection off when clicking the already-selected album card.
- [x] Frontend: Compilation sidebar posts cover_data_url with the name and tracks (custom image upload flows through).
- [x] Backend: /api/compilations/download accepts cover_data_url; saves custom cover to cover.jpg/png or creates default 640×640 title SVG.
- [x] Backend: New /api/items/by-spotify/<id>/cover serves local cover (jpg/png) or default SVG fallback.
- [x] Backend: DB image_url points to local cover endpoint when local cover exists (history uses it).
- [x] Rasterizing the default SVG to a 640×640 JPG/PNG (Pillow).
- [x] Client-side downscaling of uploaded covers to 640×640.

## Song Previews
- [ ] Retrieve 10-second song previews during artist discovery (e.g., via Spotipy if available).
- [ ] Add a quick-play button to preview tracks inline.

### Plan
- Goal: Enable inline, short previews for tracks on album/artist views without requiring a prior download.
- Source: Prefer Spotify `preview_url` (often 30s MP3). If missing, skip or future-fallback to another provider.
- Delivery: Backend proxy endpoint streams preview bytes to avoid CORS and to allow truncation to ~10s if needed.
- UI: Play button in track rows wires into the existing `PlayerContext` with a "preview" queue.

### Batches

Batch 1 â€” Backend preview proxy
- [ ] Add `GET /api/preview/<track_id>`: uses Spotipy `sp.track(track_id)` to fetch `preview_url` and caches mapping in LRU (TTL from `Config.METADATA_CACHE_TTL_SECONDS`).
- [ ] If `preview_url` exists, proxy-stream it to the client (requests `stream=True`); optionally apply `Range` passthrough. If enforcing ~10s, stop after N bytes or return `206` with `Content-Range` approximating 10s for MP3.
- [ ] Add `HEAD /api/preview/<track_id>` to quickly test availability and type.
- [ ] Errors: 404 when no preview_url, 502 on remote stream error, 429 with basic rate-limiter if needed.

Batch 2 â€” Frontend integration
- [ ] Album details: Render `TrackListDiscovery` with `enablePlay` and provide `onPlayTrack` that builds preview URLs: `/api/preview/${track.spotify_id}`.
- [ ] Artist details: Add a "Top Tracks" section above discography using Spotipy `artist_top_tracks` (new endpoint) and the same preview handling.
- [ ] Player: No code changes expected; it plays any `audioUrl`. Ensure player state distinguishes preview vs local by title suffix or metadata flag (optional).
- [ ] Visuals: Show a small "Preview" badge when the audio source is a preview.

Batch 3 â€” UX polish and fallback
- [ ] Preload small batches of availability (HEAD) to avoid click-time delays; cache on client.

# TODO IN THE FUTURE


## Steps for online publication (no burning feature)

### Plan
- Publish a "cloud mode" build where CD-burning and local-file serving is disabled, while discovery and downloads remain available.
- Deliver via container image and simple reverse proxy; secure keys via env vars.

### Batches

Batch 1 â€” Feature flags and hardening
- [ ] Config: Add `PUBLIC_MODE=1` and `ENABLE_CD_BURNER=0` flags. In `app.create_app()`, conditionally skip `CDBurningService` and the CD routes.
- [ ] Backend: Gate `/api/items/*` streaming endpoints behind `PUBLIC_MODE=0` (return 403 in public mode) to avoid serving local files remotely.
- [ ] Frontend: Hide the "CD Burner" nav/page behind a feature flag fetched from `/api/config` (new tiny endpoint exposing public caps).
- [ ] CORS: Restrict origins via env when in public mode.
- [ ] Acceptance: App runs with burning hidden/disabled; local streaming APIs blocked in public mode.

Batch 2 â€” Build and deploy
- [ ] Dockerfile: Multi-stage build to compile React (`frontend/build`) and package Flask app; serve static via Flask or (optionally) Nginx.
- [ ] Compose: `docker-compose.yml` with one service, volume-mounted `downloads/`, env for Spotify/Genius keys.
- [ ] Reverse proxy: Example Nginx config with HTTPS, gzip, and caching headers for static.
- [ ] Acceptance: One-command run serves the app on HTTPS with all non-burning features.

Batch 3 â€” Observability and quotas
- [ ] Logging: Route app logs to stdout and file; redact secrets.
- [ ] Metrics (optional): Add `/healthz` and `/readyz`; basic request timing logs.
- [ ] Rate limits: Apply simple IP-based limits on preview and download start endpoints.
- [ ] Acceptance: Health endpoints green, logs useful for ops, rate-limits in place.

Batch 4 â€” Docs
- [ ] README: Public-mode instructions, required env vars, how to rotate keys, and how to disable public mode locally.
- [ ] Security notes: Keys, allowed origins, and common pitfalls.

## Steps for executable packaging 

### Plan
- Ship a desktop-friendly package (Windows first) bundling Flask backend and built React assets, launching the app and opening the default browser.

### Batches

Batch 1 â€” PyInstaller POC
- [ ] Create `entrypoint.py` that calls `create_app()` and `app.run()` with `DEBUG=False` and `threaded=True`.
- [ ] PyInstaller spec: include `frontend/build` as data, and mark hidden imports used by SpotDL/Spotipy.
- [ ] Ensure `.env` is optional; document env fallbacks.
- [ ] Acceptance: Single-folder dist runs on a clean Windows VM.

Batch 2 â€” Assets and config
- [ ] Verify static routing (`static_folder='frontend/build'`) resolves in frozen app; adjust relative paths if needed.
- [ ] Bundle default `ffmpeg` discovery notes; prefer system `ffmpeg` with clear error message if missing.
- [ ] Add version resource info (Windows icon, product name) to the executable.
- [ ] Acceptance: Frontend loads, downloads work, logs write to `%LOCALAPPDATA%/CD-Collector/log`.

Batch 3 â€” One-file and installer (optional)
- [ ] Test one-file mode; if startup time is acceptable, ship as alternative.
- [ ] Build an NSIS/Inno Setup installer with Start Menu shortcut and file associations (optional).
- [ ] Acceptance: Install/uninstall lifecycle verified; app auto-opens browser on first run.

Batch 4 â€” Cross-platform notes
- [ ] macOS: Test codesigning requirements; provide `venv + pyinstaller` recipe.
- [ ] Linux: Provide `.deb`/AppImage instructions or fallback to Docker.

## Steps for telegram bot

### Plan
- A minimal Telegram bot to trigger downloads, track progress, and return results (links to files or status). Restrict access to allowed user IDs.

### Batches

Batch 1 â€” Bootstrap
- [ ] Add `src/bots/telegram_bot.py` using `python-telegram-bot` (v20+). Read `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USER_IDS` from env.
- [ ] Commands: `/start`, `/help`, `/download <spotify_link>`, `/status <job_id>`.
- [ ] Wire `/download` to submit a job via existing `JobQueue` (async) and return the job id.
- [ ] Acceptance: Local bot responds; submits jobs; `/status` reflects queue state.

Batch 2 â€” Progress and results
- [ ] Subscribe the bot to `ProgressBroker` updates (in-process) to push progress messages back to the chat.
- [ ] On completion, reply with a summary (item type, title, tracks). If running locally, offer a path; if public, offer a signed, time-limited download link (future).
- [ ] Errors: Send a friendly failure message and include the logged error code.
- [ ] Acceptance: End-to-end flow works for album/playlist/track links.

Batch 3 â€” Deployment and safety
- [ ] Add a small runner `python -m src.bots.telegram_bot` with graceful shutdown.
- [ ] Containerize the bot (optional) or run alongside the app; document systemd service.
- [ ] Rate-limit per user (simple token bucket) and validate links to be Spotify only.
- [ ] Acceptance: Bot remains responsive under load and rejects unknown users.

