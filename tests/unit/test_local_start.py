"""The local start command stays a single script."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_start_script_brings_up_the_compose_stack() -> None:
    script = (ROOT / "scripts" / "start.sh").read_text(encoding="utf-8")
    assert "cp .env.example .env" in script
    assert "docker compose up --build" in script
    assert script.startswith("#!/bin/sh\n")


def test_compose_reads_env_without_replacing_the_database_host() -> None:
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert "path: .env" in compose
    assert "required: false" in compose
    assert "postgresql+psycopg://nexo:nexo@db:5432/nexo" in compose
