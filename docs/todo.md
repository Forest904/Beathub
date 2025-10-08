# TODO

# TODO IN THE FAR FUTURE

## Steps for Online Publication (No Burning Feature)

### Plan
- Publish a "cloud mode" build where CD burning and local file serving is disabled, while discovery and downloads remain available.
- Deliver via container image and simple reverse proxy; secure keys via environment variables.

### Batches

Batch 1 — Feature flags and hardening
- [ ] Config: Add `PUBLIC_MODE=1` and `ENABLE_CD_BURNER=0` flags. In `app.create_app()`, conditionally skip `CDBurningService` and the CD routes.
- [ ] Backend: Gate `/api/items/*` streaming endpoints behind `PUBLIC_MODE=0` (return 403 in public mode) to avoid serving local files remotely.
- [ ] Frontend: Hide the "CD Burner" nav/page behind a feature flag fetched from `/api/config` (new tiny endpoint exposing public caps).
- [ ] CORS: Restrict origins via environment variables when in public mode.
- [ ] Acceptance: App runs with burning hidden/disabled; local streaming APIs blocked in public mode.

Batch 2 — Build and deploy
- [ ] Dockerfile: Multi-stage build to compile React (`frontend/build`) and package Flask app; serve static via Flask or (optionally) Nginx.
- [ ] Compose: `docker-compose.yml` with one service, volume-mounted `downloads/`, environment for Spotify/Genius keys.
- [ ] Reverse proxy: Example Nginx config with HTTPS, gzip, and caching headers for static assets.
- [ ] Acceptance: One-command run serves the app on HTTPS with all non-burning features.

Batch 3 — Observability and quotas
- [ ] Logging: Route app logs to stdout and file; redact secrets.
- [ ] Metrics (optional): Add `/healthz` and `/readyz`; capture basic request timing logs.
- [ ] Rate limits: Apply simple IP-based limits on preview and download start endpoints.
- [ ] Acceptance: Health endpoints green, logs useful for ops, rate limits in place.

Batch 4 — Documentation
- [ ] README: Public-mode instructions, required environment variables, how to rotate keys, and how to disable public mode locally.
- [ ] Security notes: Keys, allowed origins, and common pitfalls.

## Steps for Executable Packaging

### Plan
- Ship a desktop-friendly package (Windows first) bundling the Flask backend and built React assets, launching the app and opening the default browser.

### Batches

Batch 1 — PyInstaller proof of concept
- [ ] Create `entrypoint.py` that calls `create_app()` and `app.run()` with `DEBUG=False` and `threaded=True`.
- [ ] PyInstaller spec: include `frontend/build` as data, and mark hidden imports used by SpotDL/Spotipy.
- [ ] Ensure `.env` is optional; document environment fallbacks.
- [ ] Acceptance: Single-folder distribution runs on a clean Windows VM.

Batch 2 — Assets and config
- [ ] Verify static routing (`static_folder='frontend/build'`) resolves in the frozen app; adjust relative paths if needed.
- [ ] Bundle default `ffmpeg` discovery notes; prefer system `ffmpeg` with clear error message if missing.
- [ ] Add version resource info (Windows icon, product name) to the executable.
- [ ] Acceptance: Frontend loads, downloads work, logs write to `%LOCALAPPDATA%/CD-Collector/log`.

Batch 3 — One-file and installer (optional)
- [ ] Test one-file mode; if startup time is acceptable, ship as alternative.
- [ ] Build an NSIS/Inno Setup installer with Start Menu shortcut and file associations (optional).
- [ ] Acceptance: Install/uninstall lifecycle verified; app auto-opens browser on first run.

Batch 4 — Cross-platform notes
- [ ] macOS: Test code-signing requirements; provide `venv + pyinstaller` recipe.
- [ ] Linux: Provide `.deb`/AppImage instructions or fallback to Docker.

## Steps for Telegram Bot

### Plan
- A minimal Telegram bot to trigger downloads, track progress, and return results (links to files or status). Restrict access to allowed user IDs.

### Batches

Batch 1 — Bootstrap
- [ ] Add `src/bots/telegram_bot.py` using `python-telegram-bot` (v20+). Read `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USER_IDS` from the environment.
- [ ] Commands: `/start`, `/help`, `/download <spotify_link>`, `/status <job_id>`.
- [ ] Wire `/download` to submit a job via existing `JobQueue` (async) and return the job ID.
- [ ] Acceptance: Local bot responds; submits jobs; `/status` reflects queue state.

Batch 2 — Progress and results
- [ ] Subscribe the bot to `ProgressBroker` updates (in-process) to push progress messages back to the chat.
- [ ] On completion, reply with a summary (item type, title, tracks). If running locally, offer a path; if public, offer a signed, time-limited download link (future).
- [ ] Errors: Send a friendly failure message and include the logged error code.
- [ ] Acceptance: End-to-end flow works for album/playlist/track links.

Batch 3 — Deployment and safety
- [ ] Add a small runner `python -m src.bots.telegram_bot` with graceful shutdown.
- [ ] Containerize the bot (optional) or run alongside the app; document systemd service.
- [ ] Rate limit per user (simple token bucket) and validate links to be Spotify only.
- [ ] Acceptance: Bot remains responsive under load and rejects unknown users.
