#TODO
## Prompt for Comprehensive Scalability & Cohesion Audit

You are tasked with auditing the entire CD-Collector codebase (backend, frontend, build tooling, and docs) to design a refactor plan that maximizes scalability, high cohesion, and low coupling. Perform the following steps and record concrete action items for each subsystem you review:

- [ ] Map domain boundaries and ownership: catalogue every module/package, identify their responsibilities, dependencies, and shared primitives, then propose domain-aligned boundaries that reduce cross-cutting concerns.
- [ ] Evaluate data flow contracts: trace API schemas, database models, and React props/state to ensure each boundary exchanges well-typed, versioned contracts; note where adapters or DTOs are required.
- [ ] Analyze service lifecycle and configuration: document initialization sequences, background jobs, and configuration inputs (env vars, feature flags) to surface areas requiring dependency injection or factories for testability.
- [ ] Inspect shared utilities and duplicate logic: locate repeated helpers across backend jobs, routes, and frontend hooks; schedule extractions into cohesive libraries with clear owners.
- [ ] Review asynchronous workflows: examine job queues, download progress brokers, and React async hooks for scalability risks (blocking I/O, unbounded concurrency) and outline mitigation tactics.
- [ ] Assess state management cohesion: audit Redux/React Query/local state usage to enforce a consistent pattern per feature and limit coupling between discovery, playlists, and downloads.
- [ ] Verify build and deployment pipelines: ensure Flask app factory, CLI runners, and frontend builds share composable configuration; note refactors to simplify local vs. production parity.
- [ ] Prioritize incremental refactor roadmap: rank findings by impact and effort, defining milestones and acceptance criteria for each planned refactor to update this TODO accordingly.
## NEW FEATURE FOR LOGGED IN USERS "My Playlists" 
- [ ] Action: Implement playlist CRUD endpoints with authorization checks ensuring only the owner can mutate or delete; reuse SQLAlchemy relationships for tracks.
- [ ] Action: Introduce optimistic updates in the playlist UI backed by paginated fetch hooks that cache results using React Query/SWR patterns.
- [ ] Action: Reuse the discovery track tile components inside the playlist view, extracting shared presentation utilities to avoid duplication.

## NEW FEATURE "User Favourites" as in liked items Artists/Albums/Songs
- [ ] Action: Model favorites via a polymorphic association table keyed by user and item type; expose aggregate queries for quick lookups.
- [ ] Action: Synchronize favorites with discovery/download contexts by emitting events/hooks whenever a favorite toggles, so buttons update instantly across the app.
- [ ] Action: Standardize favorite icons/badges in a shared design token file and apply them across cards, lists, and detail headers.
# TODO IN THE FAR FUTURE

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

