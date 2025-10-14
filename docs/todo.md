# TODO

# TODO IN THE FAR FUTURE

## Online Web Deployment (Public SaaS Mode)

### Plan
- Deliver a hosted version of CD-Collector that exposes discovery and download flows while
  suppressing local-only tooling (e.g., CD burning). Harden security boundaries and provide a
  reproducible deployment pipeline.

### Batches

Batch 0 — Discovery and requirements
- [X] Audit every route and background job for assumptions about local storage or LAN access.
- [X] Document required third-party services (Spotify, Genius, YouTube) and credential scopes.
- [X] Capture compliance requirements (GDPR/DMCA takedown workflow, logging retention policy).
- [X] Acceptance: Confluence-style page summarises constraints, data flows, and ownership.

Batch 1 — Feature flags and surface hardening
- [X] Config: Introduce `PUBLIC_MODE`, `ENABLE_CD_BURNER`, and `ALLOW_STREAMING_EXPORT` flags; wire
      them through `create_app()` and CLI entrypoints.
- [X] Backend: Guard `/api/items/*` streaming and any filesystem-returning endpoints when
      `PUBLIC_MODE=1`; emit structured 403 errors.
- [X] Frontend: Add `/api/public-config` endpoint and hydrate a React context to hide gated
      navigation, buttons, and tooltips.
- [X] Security: Enforce OAuth redirect allowlist, strict CORS, rate-limiting middleware, and
      Content Security Policy headers in Flask.
- [X] Acceptance: Public build shows no burning/streaming options; blocked routes log policy
      violations.

Batch 2 — Build system and artifacts
- [X] Dockerfile: Multi-stage with `node:XX` for React build, `python:XX-slim` runtime, non-root
      user, and healthcheck script.
- [X] Docker Compose: Author `docker-compose.public.yml` with Postgres/Redis stubs (if needed),
      environment variables, and persistent `downloads/` volume.
- [X] CI: GitHub Actions (or alternative) workflow to lint, test, build image, and push to a
      registry with semantic tags.
- [X] Acceptance: `docker compose -f docker-compose.public.yml up` serves prod build locally. (Build image with `docker compose build` and then run `docker compose -f docker-compose.public.yml up` to serve the app on http://localhost:5000.)

Batch 3 — Infrastructure automation
- [X] Terraform module that provisions container registry, secrets store, managed
      database/cache (if required), and HTTPS ingress (ALB/Nginx ingress for Kubernetes).
- [X] Helm chart / Kustomize manifests referencing the container image, secrets, config maps, and
      autoscaling thresholds.
- [X] Integrate secrets rotation via AWS Secrets Manager / GCP Secret Manager and document manual
      rotation fallback.
- [X] Acceptance: Staging environment bootstrap succeeds with one command and passes smoke tests.

Batch 4 — Observability and resilience
- [X] Health endpoints: `/healthz` (dependencies) and `/readyz` (queue depth).
- [X] Structured logging to stdout with request IDs; centralise with OpenTelemetry exporter.
- [X] Metrics: Emit download counts, error rates, queue latency; provide default Grafana dashboard.
- [X] SLOs: Define alert rules (availability, latency) and create PagerDuty/on-call runbook.
- [X] Acceptance: Synthetic checks alerting wired for staging/prod; dashboards populated (see `docs/observability/README.md` and runbook).

Batch 5 — Documentation and customer support
- [X] README section covering public mode env vars, default roles, quota system, and support
      contacts.
- [X] Publish a Trust & Safety playbook (abuse reports, takedowns, offboarding).
- [X] Knowledge base article for end users (how to request downloads, rate limits, FAQ).

### Publication Runbook — Cloud Release
1. Create release branch `release/web-vX.Y.Z` from main and bump app version.
2. Update `.env.public.example` with final secrets placeholders and verify `make lint test` passes.
3. Build container: `docker build -t registry.example.com/cd-collector:web-vX.Y.Z .` and push with
   version + `latest-public` tags.
4. Run staging smoke tests via `docker compose -f docker-compose.public.yml -p staging up` and execute
   Postman collection.
5. Promote image by updating Helm values (`image.tag`) and applying to staging via CI pipeline.
6. After staging sign-off, tag release `web-vX.Y.Z`, merge release branch, and approve production
   deployment in CI/CD (Helm upgrade against prod cluster).
7. Post-deploy validation: check `/readyz`, Grafana dashboard, and run end-to-end download.
8. Announce availability in changelog and notify support to monitor incoming tickets.

## Desktop Application Packaging (Windows/macOS/Linux)

### Plan
- Ship an installer-like experience for desktop users bundling backend + frontend, ensuring
  offline-friendly defaults and auto-launch in the default browser.

### Batches

Batch 0 — Environment alignment
- [ ] Create `entrypoint.py` that reads config, starts the Flask app via Waitress/Hypercorn, and
      opens browser after server boot.
- [ ] Refactor settings to allow `.env` overrides and sensible platform defaults (download path,
      ffmpeg location, cache directory).
- [ ] Add smoke tests to validate that critical CLI commands still work post-refactor.
- [ ] Acceptance: App can start with `python entrypoint.py` on Windows/macOS/Linux.

Batch 1 — Packaging pipeline
- [ ] PyInstaller spec: include `frontend/build`, templates, static assets, and mark hidden imports
      (SpotDL, Spotipy, SQLAlchemy plugins).
- [ ] Ensure bundled binaries (ffmpeg) are optional; detect presence and show actionable error if
      missing.
- [ ] Automate build via `scripts/package_desktop.py` that runs PyInstaller for each target.
- [ ] Acceptance: Build artifacts land under `dist/<platform>/` with working executables.

Batch 2 — UX polish and platform integration
- [ ] Windows: Add icon resources, product metadata, and event log friendly logging path
      (`%LOCALAPPDATA%/CD-Collector/logs`).
- [ ] macOS: Create `.app` bundle with Info.plist, hardened runtime entitlement template, and
      codesign instructions.
- [ ] Linux: Provide `.AppImage` or `.deb` recipe with desktop file and MIME types.
- [ ] Acceptance: Smoke test on clean VMs for each platform; confirm downloads complete and logs
      flush to expected directories.

Batch 3 — Installer and auto-update (stretch)
- [ ] Windows: Build NSIS/Inno Setup installer with Start Menu shortcut, uninstall script, and
      optional context menu integration.
- [ ] macOS: Generate DMG with background artwork and drag-to-Applications instructions.
- [ ] Auto-update: Evaluate Sparkle (macOS) / Squirrel.Windows / appimageupdate; document decision.
- [ ] Acceptance: Install/uninstall cycle verified; updates apply without data loss.

Batch 4 — Release management
- [ ] Versioning: Adopt semantic version tied to git tags and embed build metadata in app splash.
- [ ] QA checklist per release (functional, antivirus scan, Windows Defender SmartScreen).
- [ ] Distribute checksums (SHA256) and optional GPG signatures.
- [ ] Acceptance: Release candidate promoted to stable after QA sign-off checklist passes.

### Publication Runbook — Desktop Releases
1. Cut release branch `release/desktop-vX.Y.Z`; update `VERSION` file and changelog desktop section.
2. Run `python scripts/package_desktop.py --platform windows macos linux` inside clean CI runners.
3. Virus-scan artifacts (Windows Defender, macOS Gatekeeper notarization, ClamAV for Linux).
4. Upload installers and checksums to GitHub Releases (draft), attach upgrade notes, and request QA
   sign-off.
5. After approvals, publish GitHub Release, update website download links, and notify mailing list.
6. Monitor crash/log telemetry and roll back by withdrawing binaries if high-severity issues emerge.

## Telegram Bot Deployment

### Plan
- Provide a Telegram interface that allows whitelisted users to trigger downloads, monitor
  progress, and retrieve links while respecting rate limits and security constraints.

### Batches

Batch 0 — Foundations
- [ ] Create `src/bots/telegram_bot.py` using `python-telegram-bot` (v20+) with dependency injection
      for job submission and status queries.
- [ ] Load `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_IDS`, and `PUBLIC_BASE_URL` from config; add
      schema validation and helpful startup errors.
- [ ] Implement `/start`, `/help`, `/download <spotify_link>`, `/status <job_id>`, `/cancel <job_id>`
      command handlers with logging context.
- [ ] Acceptance: Local bot responds to whitelisted users and rejects others with clear messaging.

Batch 1 — Job orchestration and feedback
- [ ] Integrate with existing `JobQueue` or create `BotJobService` wrapper ensuring idempotent job
      creation.
- [ ] Subscribe to `ProgressBroker` to send incremental updates (percentage, track names) back to
      the originating chat.
- [ ] Provide rich completion summaries (title, duration, output path or download URL) and friendly
      error fallbacks.
- [ ] Acceptance: End-to-end playlist download triggered via Telegram completes with updates.

Batch 2 — Reliability and monitoring
- [ ] Add retry/backoff for Telegram API errors and network hiccups; centralise exception handling.
- [ ] Implement per-user rate limiting (token bucket) and global concurrency guard to protect
      backend resources.
- [ ] Emit structured logs and Prometheus counters (commands, successes, failures).
- [ ] Acceptance: Load test with bot emulator to ensure graceful throttling.

Batch 3 — Deployment options
- [ ] CLI runner `python -m src.bots.telegram_bot --config config/bot.toml` with graceful shutdown
      and health endpoints.
- [ ] Dockerfile stage `bot` to build lightweight container; share code volume with main image or
      reuse base layer.
- [ ] Systemd service template for bare-metal deployments; document environment files and log
      rotation.
- [ ] Acceptance: Bot can be deployed via Docker Compose service or systemd unit with minimal steps.

### Publication Runbook — Telegram Bot Release
1. Create release branch `release/telegram-vX.Y.Z`; update bot changelog and bump version constant in
   `src/bots/telegram_bot.py`.
2. Run unit/integration tests: `pytest tests/bots/test_telegram_bot.py` and manual smoke test against
   staging bot using sandbox Telegram chat.
3. Build and push bot container: `docker build -f Dockerfile.bot -t registry.example.com/cd-bot:vX.Y.Z .`.
4. Deploy to staging using `docker compose -f deploy/telegram/docker-compose.yml up -d`; verify
   health endpoint and command flow.
5. Promote image to production via CI/CD (Helm release or systemd update), ensuring secrets are
   rotated and `TELEGRAM_ALLOWED_USER_IDS` configured.
6. Post-release checklist: confirm monitoring dashboards, audit logs for unauthorized access, and
   broadcast update to whitelisted users if needed.

