"""Shared test fixtures."""

import os
from collections.abc import Iterator

import pytest
from sqlalchemy.engine import make_url

from nexo_ai.config.logging import configure_logging
from nexo_ai.config.settings import AppEnvironment, Settings, get_settings

LOCAL_DATABASE_URL = "postgresql+psycopg://nexo:nexo@127.0.0.1:5432/nexo"
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "db"}


@pytest.fixture(autouse=True)
def reset_runtime_state() -> Iterator[None]:
    get_settings.cache_clear()
    configure_logging("WARNING")
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail("DATABASE_URL is required for integration tests")
    host = make_url(url).host
    if host not in _LOCAL_HOSTS:
        pytest.fail("Integration tests refuse to run against a non-local database host")
    return url


def build_settings(
    *,
    app_env: AppEnvironment | str = AppEnvironment.TEST,
    database_url: str = LOCAL_DATABASE_URL,
    app_host: str = "127.0.0.1",
    log_level: str = "WARNING",
    db_connect_timeout: int = 5,
    embedding_api_key: str = "",
    embedding_base_url: str = "https://api.openai.com/v1",
    completion_api_key: str = "",
    document_chunk_size: int = 1000,
    document_chunk_overlap: int = 200,
) -> Settings:
    return Settings(
        _env_file=None,
        app_env=app_env,
        database_url=database_url,
        app_host=app_host,
        log_level=log_level,
        db_connect_timeout=db_connect_timeout,
        embedding_api_key=embedding_api_key,
        embedding_base_url=embedding_base_url,
        completion_api_key=completion_api_key,
        document_chunk_size=document_chunk_size,
        document_chunk_overlap=document_chunk_overlap,
    )
