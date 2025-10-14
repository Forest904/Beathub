# Observability Overview

This directory documents the observability stack for CD-Collector in public (SaaS) mode.

## Endpoints

- `GET /healthz` – liveness probe. Checks database connectivity, SpotDL availability, and reports current job queue depth.
- `GET /readyz` – readiness probe. Returns HTTP 200 when the in-process queue depth is below `READINESS_QUEUE_THRESHOLD` (default `25`). Exposes the threshold and live depth.
- `GET /metrics` – Prometheus scrape endpoint with application metrics (downloads, queue statistics, histograms).

## Logging & Tracing

- All logs are emitted in JSON to stdout with `request_id`, HTTP metadata, and exception stacks.
- The request ID is propagated via the `X-Request-ID` header (incoming header respected, otherwise generated). Responses always echo the header.
- When `OTEL_EXPORTER_OTLP_ENDPOINT` (and optional headers) are configured, logs and traces are exported to the configured OTLP collector.
- The Flask app is instrumented with OpenTelemetry (TracerProvider + OTLP exporter). Configure `OTEL_SERVICE_NAME` to adjust the service label.

## Metrics

The following Prometheus metrics are emitted:

| Metric | Type | Description |
| --- | --- | --- |
| `cdcollector_download_attempts_total` | Counter | Number of download requests received (sync + async). |
| `cdcollector_download_success_total` | Counter | Completed downloads. |
| `cdcollector_download_failure_total` | Counter | Failed downloads after retries. |
| `cdcollector_job_queue_depth` | Gauge | Current in-process queue depth. |
| `cdcollector_job_queue_wait_seconds` | Histogram | Time spent waiting in the queue before execution. |
| `cdcollector_download_job_execution_seconds` | Histogram | Execution duration of download jobs. |

See `grafana-dashboard.json` for a starter Grafana dashboard covering these metrics.

## Health & Alerting

- Liveness: `/healthz` (HTTP 200 indicates healthy dependencies).
- Readiness: `/readyz` (HTTP 200 indicates queue depth is acceptable).
- Suggested alert rules are detailed in `runbook.md`, including availability and latency SLOs mapped to PagerDuty incidents and synthetic probe thresholds.

## Synthetic Checks

- HTTP probe `/readyz` every 30s from each region to detect saturation (alert if ≥2 consecutive failures).
- Selenium/API flow to POST `/api/download` (async mode) and verify queue drain within 2 minutes.

## Configuration Summary

| Variable | Purpose |
| --- | --- |
| `READINESS_QUEUE_THRESHOLD` | Max queue depth before readiness flips to 503 (default 25). |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector URL for logs/traces. |
| `OTEL_EXPORTER_OTLP_HEADERS` | Optional headers for OTLP exporter (e.g., auth tokens). |
| `OTEL_EXPORTER_OTLP_INSECURE` | Set `0` to require TLS when exporting. |
| `OTEL_SERVICE_NAME` | Service label used by OpenTelemetry resources (defaults to `cd-collector`). |

Refer to `runbook.md` for detailed operator procedures.
