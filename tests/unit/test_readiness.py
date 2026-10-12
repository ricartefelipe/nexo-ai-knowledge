"""Database readiness without a live server."""

from __future__ import annotations

from typing import cast

from sqlalchemy.engine import Engine

from nexo_ai.infrastructure.persistence.database import create_db_engine
from nexo_ai.infrastructure.persistence.health import DatabaseReadinessProbe
from tests.conftest import build_settings


class _Result:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one(self) -> object:
        return self._value


class _Connection:
    def __init__(self, results: list[object], error: Exception | None) -> None:
        self._results = results
        self._error = error

    def execute(self, _statement: object, *_args: object, **_kwargs: object) -> _Result:
        if self._error is not None:
            raise self._error
        return _Result(self._results.pop(0))

    def __enter__(self) -> _Connection:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class _Engine:
    def __init__(self, results: list[object] | None = None, error: Exception | None = None) -> None:
        self._connection = _Connection(list(results or []), error)

    def connect(self) -> _Connection:
        return self._connection


def test_engine_uses_the_postgresql_dialect_without_connecting() -> None:
    engine = create_db_engine(build_settings())
    try:
        assert engine.dialect.name == "postgresql"
    finally:
        engine.dispose()


def test_probe_is_ready_when_vector_is_installed() -> None:
    probe = DatabaseReadinessProbe(cast(Engine, _Engine(results=[1, True])))
    report = probe.check()
    assert report.ready is True
    assert report.detail == "O banco de dados está pronto."


def test_probe_reports_a_missing_extension() -> None:
    probe = DatabaseReadinessProbe(cast(Engine, _Engine(results=[1, False])))
    report = probe.check()
    assert report.ready is False
    assert report.detail == "A extensão vector não está instalada."


def test_probe_hides_connection_failures() -> None:
    probe = DatabaseReadinessProbe(
        cast(Engine, _Engine(error=RuntimeError("password=super-secret")))
    )
    report = probe.check()
    assert report.ready is False
    assert report.detail == "O banco de dados está indisponível."
    assert "super-secret" not in report.detail
