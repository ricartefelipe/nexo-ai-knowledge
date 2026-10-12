"""Structured log contract."""

import json

import pytest
import structlog

from nexo_ai.config.logging import configure_logging


def test_logs_include_operational_fields(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(correlation_id="abc123")
    try:
        structlog.get_logger().info(
            "readiness_check",
            component="nexo_ai.persistence",
            operation="readiness_check",
            result="ready",
            duration_ms=1.25,
        )
        payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    finally:
        structlog.contextvars.clear_contextvars()

    assert payload["event"] == "readiness_check"
    assert payload["timestamp"]
    assert payload["level"] == "info"
    assert payload["component"] == "nexo_ai.persistence"
    assert payload["operation"] == "readiness_check"
    assert payload["correlation_id"] == "abc123"
    assert payload["result"] == "ready"
    assert payload["duration_ms"] == 1.25
