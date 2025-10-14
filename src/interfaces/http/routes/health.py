from __future__ import annotations

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from src.database.db_manager import db
from src.observability.metrics import update_queue_gauge

health_bp = Blueprint("health_bp", __name__)


def _job_queue_depth() -> int:
    queue = current_app.extensions.get("download_jobs")
    if queue is None:
        return 0
    try:
        return queue.qsize()
    except Exception:  # pragma: no cover - defensive
        return 0


@health_bp.route("/healthz")
def healthz():
    status = 200
    checks = {}

    try:
        db.session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # pragma: no cover - DB failure path
        status = 503
        checks["database"] = f"error: {exc}"

    spotdl_client = current_app.extensions.get("spotdl_client")
    if spotdl_client:
        checks["spotdl"] = "ok"
    else:
        checks["spotdl"] = "unavailable"

    depth = _job_queue_depth()
    checks["job_queue_depth"] = depth

    overall = "ok" if status == 200 else "degraded"
    return jsonify({"status": overall, "checks": checks}), status


@health_bp.route("/readyz")
def readyz():
    depth = _job_queue_depth()
    update_queue_gauge(depth)
    threshold = int(current_app.config.get("READINESS_QUEUE_THRESHOLD", 25))
    healthy = depth <= threshold
    status = 200 if healthy else 503
    payload = {
        "status": "ready" if healthy else "blocked",
        "job_queue_depth": depth,
        "threshold": threshold,
    }
    return jsonify(payload), status
