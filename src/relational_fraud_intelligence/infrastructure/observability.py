"""OpenTelemetry & Prometheus observability bootstrap.

Call ``setup_observability(app, settings)`` during application startup to
instrument FastAPI with distributed tracing and Prometheus metrics.  When
``otel_enabled`` is ``False`` (the default), this module is a no-op so
existing deployments are unaffected.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

    from relational_fraud_intelligence.settings import AppSettings

logger = logging.getLogger(__name__)


def setup_observability(app: FastAPI, settings: AppSettings) -> None:
    """Wire OpenTelemetry tracing + Prometheus metrics into *app*."""
    if not settings.otel_enabled:
        logger.info("OpenTelemetry disabled (RFI_OTEL_ENABLED=false). Skipping.")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from prometheus_client import make_asgi_app
    except ImportError as exc:  # pragma: no cover
        logger.warning("OpenTelemetry packages not installed — skipping: %s", exc)
        return

    # --- Tracer provider ---------------------------------------------------
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "1.0.0",
            "deployment.environment": settings.app_env,
        }
    )
    provider = TracerProvider(resource=resource)

    # Optional OTLP exporter (Jaeger / Tempo / Grafana Cloud)
    if settings.otel_exporter_otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            otlp_exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(
                "OTLP trace exporter configured → %s",
                settings.otel_exporter_otlp_endpoint,
            )
        except ImportError:
            logger.warning(
                "opentelemetry-exporter-otlp-proto-grpc not installed — "
                "falling back to console span exporter."
            )
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    else:
        # Fallback: print spans to stdout (useful in local dev)
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)

    # Store on app state so lifespan shutdown can flush pending spans
    app.state.otel_tracer_provider = provider

    # --- FastAPI auto-instrumentation --------------------------------------
    FastAPIInstrumentor.instrument_app(app)
    logger.info("FastAPI instrumented with OpenTelemetry tracing.")

    # --- Prometheus metrics endpoint ---------------------------------------
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    logger.info("Prometheus metrics endpoint mounted at /metrics.")
