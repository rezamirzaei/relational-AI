from __future__ import annotations

import json
import logging
from typing import Any


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
        }
        if hasattr(record, "request_id"):
            payload["request_id"] = record.request_id
        if hasattr(record, "path"):
            payload["path"] = record.path
        if hasattr(record, "status_code"):
            payload["status_code"] = record.status_code
        if hasattr(record, "actor_username"):
            payload["actor_username"] = record.actor_username

        # Inject OpenTelemetry trace context when available
        try:
            from opentelemetry import trace as otel_trace

            span = otel_trace.get_current_span()
            ctx = span.get_span_context()
            if ctx and ctx.trace_id:
                payload["trace_id"] = format(ctx.trace_id, "032x")
                payload["span_id"] = format(ctx.span_id, "016x")
        except Exception:  # noqa: BLE001 – OTel may not be installed/active
            pass

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=logging.INFO)

    formatter = JsonLogFormatter()
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
