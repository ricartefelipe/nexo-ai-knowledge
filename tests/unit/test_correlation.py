"""Correlation id rules."""

from uuid import UUID

from nexo_ai.api.middleware.correlation import resolve_correlation_id


def test_accepts_a_safe_caller_supplied_id() -> None:
    assert resolve_correlation_id("request-123.abc_DEF") == "request-123.abc_DEF"


def test_generates_an_id_when_the_header_is_missing_or_unsafe() -> None:
    generated = resolve_correlation_id(None)
    UUID(generated)

    unsafe_values = ["", "bad id", "line\nbreak", "id with space", "-" + "a" * 10, "a" * 129]
    for value in unsafe_values:
        resolved = resolve_correlation_id(value)
        assert resolved != value
        UUID(resolved)
