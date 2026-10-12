"""The local start command does not create configuration files."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_start_script_only_runs_compose() -> None:
    script = (ROOT / "scripts" / "start.sh").read_text(encoding="utf-8")
    assert script.startswith("#!/bin/sh\n")
    assert "docker compose up --build" in script
    assert ".env" not in script
    assert "cp " not in script


def test_compose_starts_without_an_env_file() -> None:
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert "env_file" not in compose
    assert "EMBEDDING_API_KEY: ${EMBEDDING_API_KEY:-}" in compose
    assert "COMPLETION_API_KEY: ${COMPLETION_API_KEY:-}" in compose
    assert "postgresql+psycopg://nexo:nexo@db:5432/nexo" in compose
