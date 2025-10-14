# Observability Runbook

## Contacts

- **Primary on-call**: PagerDuty schedule `CD-Collector Prod`
- **Escalation**: `#cd-collector-ops` Slack channel

## Health Checks

| Check | Endpoint | Expected Behaviour |
| --- | --- | --- |
| Liveness | `GET /healthz` | HTTP 200 with `status="ok"` |
| Readiness | `GET /readyz` | HTTP 200 with queue depth ≤ threshold |
| Metrics | `GET /metrics` | Scrapes without error |

## SLO Targets

| SLO | Target | Window |
| --- | --- | --- |
| Download API availability | ≥ 99.5% | rolling 30 days |
| Download completion latency | p95 ≤ 180s | rolling 7 days |
| Queue saturation | queue depth ≤ threshold 95% of time | rolling 7 days |

## Alert Rules

1. **Availability**: Trigger if `/readyz` fails for > 2 consecutive synthetic probes (1 min interval). Severity: high.
2. **Latency**: Trigger if `cdcollector_download_job_execution_seconds` p95 > 240s for 5 minutes. Severity: medium.
3. **Queue Saturation**: Trigger if `cdcollector_job_queue_depth` > threshold for 5 minutes. Severity: medium.
4. **OTLP Exporter**: Trigger if collector unreachable (log exporter errors) for > 5 minutes. Severity: low.

## Incident Response

1. Check Grafana dashboard (`Grafana > Dashboards > CD-Collector SaaS`) for active panels.
2. If readiness failing due to queue depth:
   - Scale worker replicas (if applicable) or investigate stuck downloads.
   - Consider toggling `ALLOW_STREAMING_EXPORT=0` to reduce load temporarily.
3. For latency spikes:
   - Inspect job durations histogram & logs (filter by `request_id`).
   - Validate external dependencies (Spotify, SpotDL providers).
4. For OTLP/exporter failures:
   - Verify collector availability.
   - Check environment variables for endpoint/auth changes.

## Playbooks

- **Restart Application**: `docker compose -f docker-compose.public.yml restart web`
- **Drain Queue**:
  1. Disable new download requests (set feature flag or route guard).
  2. Allow queue to drain; monitor `cdcollector_job_queue_depth` until zero.
  3. Re-enable requests after readiness stable for 5 minutes.

## Post-Incident Checklist

1. Capture `request_id` for failing requests and export logs via OTLP.
2. Create incident record in tracker with root cause and remediation.
3. Update runbook/SLOs if new patterns detected.
