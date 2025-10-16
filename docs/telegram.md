
# Telegram Bot Deployment

## Plan
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

