from __future__ import annotations

import json
import logging
import sys
from types import SimpleNamespace

import pytest

from relational_fraud_intelligence import __main__ as api_entrypoint
from relational_fraud_intelligence.infrastructure.logging import (
    JsonLogFormatter,
    configure_logging,
)


@pytest.mark.parametrize(
    ("app_env", "expected_reload"),
    [
        ("local", True),
        ("ci", False),
    ],
)
def test_api_entrypoint_runs_uvicorn_with_expected_reload(
    monkeypatch: pytest.MonkeyPatch,
    app_env: str,
    expected_reload: bool,
) -> None:
    calls: dict[str, object] = {}

    def fake_run(*args: object, **kwargs: object) -> None:
        calls["args"] = args
        calls["kwargs"] = kwargs

    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=fake_run))
    monkeypatch.setenv("RFI_APP_ENV", app_env)
    monkeypatch.setenv("RFI_API_HOST", "127.0.0.1")
    monkeypatch.setenv("RFI_API_PORT", "9001")

    api_entrypoint.main()

    assert calls["args"] == ("relational_fraud_intelligence.app:create_app",)
    assert calls["kwargs"] == {
        "factory": True,
        "host": "127.0.0.1",
        "port": 9001,
        "reload": expected_reload,
    }


def test_json_log_formatter_emits_structured_payload() -> None:
    formatter = JsonLogFormatter()

    try:
        raise ValueError("boom")
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="relational_fraud_intelligence.audit",
        level=logging.ERROR,
        pathname=__file__,
        lineno=42,
        msg="request failed",
        args=(),
        exc_info=exc_info,
    )
    record.request_id = "req-123"
    record.path = "/api/v1/health"
    record.status_code = 500
    record.actor_username = "analyst"

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "ERROR"
    assert payload["logger"] == "relational_fraud_intelligence.audit"
    assert payload["message"] == "request failed"
    assert payload["request_id"] == "req-123"
    assert payload["path"] == "/api/v1/health"
    assert payload["status_code"] == 500
    assert payload["actor_username"] == "analyst"
    assert "ValueError: boom" in payload["exception"]


def test_configure_logging_applies_json_formatter_to_existing_handlers() -> None:
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level

    try:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        handler = logging.StreamHandler()
        root_logger.addHandler(handler)

        configure_logging()

        assert isinstance(handler.formatter, JsonLogFormatter)
    finally:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        for handler in original_handlers:
            root_logger.addHandler(handler)
        root_logger.setLevel(original_level)
