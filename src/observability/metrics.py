from __future__ import annotations

import time
from typing import Optional

from flask import Blueprint, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest

metrics_blueprint = Blueprint("metrics_bp", __name__)

CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

DOWNLOAD_ATTEMPTS = Counter(
    "cdcollector_download_attempts_total",
    "Total number of download attempts received by the API.",
)
DOWNLOAD_SUCCESSES = Counter(
    "cdcollector_download_success_total",
    "Total number of successful downloads.",
)
DOWNLOAD_FAILURES = Counter(
    "cdcollector_download_failure_total",
    "Total number of failed downloads.",
)
JOB_QUEUE_DEPTH = Gauge(
    "cdcollector_job_queue_depth",
    "Current number of jobs waiting in the in-process queue.",
)
JOB_QUEUE_WAIT_TIME = Histogram(
    "cdcollector_job_queue_wait_seconds",
    "Time spent in the queue before a job starts execution.",
    buckets=(0.5, 1, 2, 5, 10, 30, 60, float("inf")),
)
JOB_EXECUTION_TIME = Histogram(
    "cdcollector_download_job_execution_seconds",
    "Execution time for individual download jobs.",
    buckets=(5, 10, 20, 40, 60, 120, 300, 600, float("inf")),
)


def record_download_attempt() -> None:
    DOWNLOAD_ATTEMPTS.inc()


def record_download_success(duration_seconds: Optional[float] = None) -> None:
    DOWNLOAD_SUCCESSES.inc()
    if duration_seconds is not None:
        JOB_EXECUTION_TIME.observe(duration_seconds)


def record_download_failure(duration_seconds: Optional[float] = None) -> None:
    DOWNLOAD_FAILURES.inc()
    if duration_seconds is not None:
        JOB_EXECUTION_TIME.observe(duration_seconds)


def observe_queue_wait_time(wait_seconds: float) -> None:
    JOB_QUEUE_WAIT_TIME.observe(wait_seconds)


def update_queue_gauge(depth: int) -> None:
    JOB_QUEUE_DEPTH.set(max(0, depth))


@metrics_blueprint.route("/metrics")
def metrics_endpoint() -> Response:
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
