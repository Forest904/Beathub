# Online Web Deployment (Public SaaS Mode)

## Plan
- Deliver a hosted version of CD-Collector that exposes discovery and download flows while
  suppressing local-only tooling (e.g., CD burning). Harden security boundaries and provide a
  reproducible deployment pipeline.

### Batches

Batch 0 — Discovery and requirements
- [ ] Audit every route and background job for assumptions about local storage or LAN access.
- [ ] Document required third-party services (Spotify, Genius, YouTube) and credential scopes.
- [ ] Capture compliance requirements (GDPR/DMCA takedown workflow, logging retention policy).
- [ ] Acceptance: Confluence-style page summarises constraints, data flows, and ownership.

Batch 1 — Feature flags and surface hardening
- [ ] Config: Introduce `PUBLIC_MODE`, `ENABLE_CD_BURNER`, and `ALLOW_STREAMING_EXPORT` flags; wire
      them through `create_app()` and CLI entrypoints.
- [ ] Backend: Guard `/api/items/*` streaming and any filesystem-returning endpoints when
      `PUBLIC_MODE=1`; emit structured 403 errors.
- [ ] Frontend: Add `/api/public-config` endpoint and hydrate a React context to hide gated
      navigation, buttons, and tooltips.
- [ ] Security: Enforce OAuth redirect allowlist, strict CORS, rate-limiting middleware, and
      Content Security Policy headers in Flask.
- [ ] Acceptance: Public build shows no burning/streaming options; blocked routes log policy
      violations.

Batch 2 — Build system and artifacts
- [ ] Dockerfile: Multi-stage with `node:XX` for React build, `python:XX-slim` runtime, non-root
      user, and healthcheck script.
- [ ] Docker Compose: Author `docker-compose.public.yml` with Postgres/Redis stubs (if needed),
      environment variables, and persistent `downloads/` volume.
- [ ] CI: GitHub Actions (or alternative) workflow to lint, test, build image, and push to a
      registry with semantic tags.
- [ ] Acceptance: `docker compose -f docker-compose.public.yml up` serves prod build locally.

Batch 3 — Infrastructure automation
- [ ] Terraform (or Pulumi) module that provisions container registry, secrets store, managed
      database/cache (if required), and HTTPS ingress (ALB/Nginx ingress for Kubernetes).
- [ ] Helm chart / Kustomize manifests referencing the container image, secrets, config maps, and
      autoscaling thresholds.
- [ ] Integrate secrets rotation via AWS Secrets Manager / GCP Secret Manager and document manual
      rotation fallback.
- [ ] Acceptance: Staging environment bootstrap succeeds with one command and passes smoke tests.

Batch 4 — Observability and resilience
- [ ] Health endpoints: `/healthz` (dependencies) and `/readyz` (queue depth).
- [ ] Structured logging to stdout with request IDs; centralise with OpenTelemetry exporter.
- [ ] Metrics: Emit download counts, error rates, queue latency; provide default Grafana dashboard.
- [ ] SLOs: Define alert rules (availability, latency) and create PagerDuty/on-call runbook.
- [ ] Acceptance: Synthetic checks alerting wired for staging/prod; dashboards populated.

Batch 5 — Documentation and customer support
- [ ] README section covering public mode env vars, default roles, quota system, and support
      contacts.
- [ ] Publish a Trust & Safety playbook (abuse reports, takedowns, offboarding).
- [ ] Knowledge base article for end users (how to request downloads, rate limits, FAQ).
- [ ] Acceptance: Documentation reviewed by support/security stakeholders.

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
