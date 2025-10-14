import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from flask import g, has_request_context, request

try:
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, OTLPLogExporter
    from opentelemetry.sdk.resources import Resource
except Exception:  # pragma: no cover - Opentelemetry optional
    LoggerProvider = None  # type: ignore
    LoggingHandler = None  # type: ignore


class RequestContextFilter(logging.Filter):
    """Attach request-scoped metadata to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(g, "request_id", None)
        if has_request_context():
            record.path = request.path
            record.method = request.method
            record.remote_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
        else:
            record.path = None
            record.method = None
            record.remote_addr = None
        return True


class JsonFormatter(logging.Formatter):
    """Render log records as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - formatting
        payload: Dict[str, Any] = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "path": getattr(record, "path", None),
            "method": getattr(record, "method", None),
            "remote_addr": getattr(record, "remote_addr", None),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _build_otlp_handler(app) -> Optional[logging.Handler]:
    """Configure OpenTelemetry logging handler if exporter is available."""
    if LoggerProvider is None or LoggingHandler is None:
        return None

    endpoint = (
        app.config.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    )
    if not endpoint:
        return None

    resource = Resource.create(
        {
            "service.name": app.config.get("OTEL_SERVICE_NAME", "cd-collector"),
        }
    )
    provider = LoggerProvider(resource=resource)
    exporter = OTLPLogExporter(endpoint=endpoint)
    provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    return LoggingHandler(level=logging.INFO, logger_provider=provider)


def configure_structured_logging(app) -> None:
    """Attach structured stdout logging (+ optional OTLP export) to the root logger."""
    root = logging.getLogger()

    context_filter = RequestContextFilter()
    json_formatter = JsonFormatter()

    has_json_stream = any(
        isinstance(handler, logging.StreamHandler)
        and isinstance(getattr(handler, "formatter", None), JsonFormatter)
        for handler in root.handlers
    )
    if not has_json_stream:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(json_formatter)
        stream_handler.addFilter(context_filter)
        root.addHandler(stream_handler)

    otlp_handler = _build_otlp_handler(app)
    if otlp_handler:
        otlp_handler.setFormatter(json_formatter)
        otlp_handler.addFilter(context_filter)
        root.addHandler(otlp_handler)
