"""PostgreSQL and pgvector integration."""

import pytest
from alembic import command
from alembic.config import Config
from alembic.util.exc import CommandError
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from nexo_ai.config.settings import get_settings
from nexo_ai.infrastructure.persistence.database import create_db_engine
from nexo_ai.main import create_app
from tests.conftest import build_settings

pytestmark = pytest.mark.integration

_REVISION = "0003_embedding_versioning"


def _alembic_config() -> Config:
    get_settings.cache_clear()
    return Config("alembic.ini")


def _extension_installed(database_url: str) -> bool:
    engine = create_db_engine(build_settings(database_url=database_url))
    try:
        with engine.connect() as connection:
            installed = bool(
                connection.execute(
                    text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
                ).scalar_one()
            )
    finally:
        engine.dispose()
    return installed


def test_migration_enables_vector_and_session_can_read(database_url: str) -> None:
    command.upgrade(_alembic_config(), "head")
    assert _extension_installed(database_url) is True

    settings = build_settings(database_url=database_url)
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ready",
            "database": "ok",
            "embedding_provider": "not_configured",
            "completion_provider": "not_configured",
            "embedding_model": "text-embedding-3-small",
        }
        factory: sessionmaker[Session] = app.state.session_factory
        session = factory()
        try:
            value: int = session.execute(text("SELECT 1")).scalar_one()
            version: str = session.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            session.commit()
        finally:
            session.close()
    assert value == 1
    assert version == _REVISION


def test_downgrade_refuses_dependent_objects_and_restores_cleanly(database_url: str) -> None:
    command.upgrade(_alembic_config(), "head")
    engine = create_db_engine(build_settings(database_url=database_url))
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS vector_probe"))
        connection.execute(
            text("CREATE TABLE vector_probe (id integer PRIMARY KEY, embedding vector(3))")
        )
    engine.dispose()

    with pytest.raises((SQLAlchemyError, CommandError)):
        command.downgrade(_alembic_config(), "base")
    assert _extension_installed(database_url) is True

    engine = create_db_engine(build_settings(database_url=database_url))
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE vector_probe"))
    engine.dispose()

    command.downgrade(_alembic_config(), "base")
    assert _extension_installed(database_url) is False

    command.upgrade(_alembic_config(), "head")
    assert _extension_installed(database_url) is True
