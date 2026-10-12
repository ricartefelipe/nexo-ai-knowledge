"""Shared test fixtures."""

from collections.abc import Iterator

import pytest

from nexo_ai.config.logging import configure_logging
from nexo_ai.config.settings import AppEnvironment, Settings, get_settings

LOCAL_DATABASE_URL = "postgresql+psycopg://nexo:nexo@127.0.0.1:5432/nexo"


@pytest.fixture(autouse=True)
def reset_runtime_state() -> Iterator[None]:
    get_settings.cache_clear()
    configure_logging("WARNING")
    yield
    get_settings.cache_clear()


def build_settings(
    *,
    app_env: AppEnvironment | str = AppEnvironment.TEST,
    database_url: str = LOCAL_DATABASE_URL,
    app_host: str = "127.0.0.1",
    log_level: str = "WARNING",
    db_connect_timeout: int = 5,
) -> Settings:
    return Settings(
        _env_file=None,
        app_env=app_env,
        database_url=database_url,
        app_host=app_host,
        log_level=log_level,
        db_connect_timeout=db_connect_timeout,
    )
