"""Readiness checks for PostgreSQL and the pgvector extension."""

import time
from dataclasses import dataclass
from typing import Protocol

import structlog
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    """Result of one readiness check."""

    ready: bool
    detail: str


class ReadinessProbe(Protocol):
    """Replaceable readiness check used by the API."""

    def check(self) -> ReadinessReport:
        """Return whether critical dependencies can serve traffic."""


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


class DatabaseReadinessProbe:
    """Confirm that PostgreSQL answers and the vector extension is installed."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def check(self) -> ReadinessReport:
        started = time.perf_counter()
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1")).scalar_one()
                installed = bool(
                    connection.execute(
                        text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
                    ).scalar_one()
                )
        except Exception as exc:
            logger.warning(
                "readiness_check",
                component="nexo_ai.persistence",
                operation="readiness_check",
                result="unavailable",
                error_type=type(exc).__name__,
                duration_ms=_elapsed_ms(started),
            )
            return ReadinessReport(ready=False, detail="O banco de dados está indisponível.")

        duration_ms = _elapsed_ms(started)
        if not installed:
            logger.info(
                "readiness_check",
                component="nexo_ai.persistence",
                operation="readiness_check",
                result="not_ready",
                duration_ms=duration_ms,
            )
            return ReadinessReport(ready=False, detail="A extensão vector não está instalada.")

        logger.info(
            "readiness_check",
            component="nexo_ai.persistence",
            operation="readiness_check",
            result="ready",
            duration_ms=duration_ms,
        )
        return ReadinessReport(ready=True, detail="O banco de dados está pronto.")


@dataclass(frozen=True, slots=True)
class Capabilities:
    """What the process can actually do beyond serving health: reported without secrets."""

    embedding_provider: bool
    completion_provider: bool
    embedding_model: str
