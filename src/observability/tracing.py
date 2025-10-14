import os

from flask import Flask

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except Exception:  # pragma: no cover - optional dependency
    FlaskInstrumentor = None  # type: ignore


def init_tracing(app: Flask) -> None:
    if FlaskInstrumentor is None:  # pragma: no cover - optional dependency
        return

    endpoint = app.config.get("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    if not endpoint:
        return

    headers = app.config.get("OTEL_EXPORTER_OTLP_HEADERS") or os.getenv(
        "OTEL_EXPORTER_OTLP_HEADERS"
    )

    resource = Resource.create(
        {
            "service.name": app.config.get("OTEL_SERVICE_NAME", "cd-collector"),
        }
    )

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint=endpoint,
        headers=headers,
        insecure=app.config.get("OTEL_EXPORTER_OTLP_INSECURE", True),
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FlaskInstrumentor().instrument_app(app)
