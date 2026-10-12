"""Settings validation."""

import pytest
from pydantic import ValidationError

from nexo_ai.config.settings import AppEnvironment, Settings, get_settings
from tests.conftest import LOCAL_DATABASE_URL, build_settings


def test_local_defaults_when_environment_is_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "APP_ENV",
        "APP_HOST",
        "APP_PORT",
        "LOG_LEVEL",
        "DB_POOL_SIZE",
        "DB_MAX_OVERFLOW",
        "DB_POOL_TIMEOUT",
        "DB_CONNECT_TIMEOUT",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(_env_file=None, database_url=LOCAL_DATABASE_URL)
    assert settings.app_env is AppEnvironment.LOCAL
    assert settings.app_host == "127.0.0.1"
    assert settings.app_port == 8000
    assert settings.log_level == "INFO"
    assert settings.db_pool_size == 5
    assert settings.db_max_overflow == 10
    assert settings.db_pool_timeout == 30
    assert settings.db_connect_timeout == 5


def test_get_settings_reads_process_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DATABASE_URL", LOCAL_DATABASE_URL)
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.app_env is AppEnvironment.LOCAL
    assert settings.database_url == LOCAL_DATABASE_URL


def test_database_url_is_hidden_from_repr() -> None:
    settings = build_settings(
        database_url="postgresql+psycopg://nexo:super-secret@127.0.0.1:5432/nexo"
    )
    assert "super-secret" not in repr(settings)


def test_rejects_unparseable_database_url() -> None:
    with pytest.raises(ValidationError) as caught:
        build_settings(database_url="bad-url-super-secret")
    assert "super-secret" not in str(caught.value)


def test_rejects_non_postgres_driver() -> None:
    with pytest.raises(ValidationError) as caught:
        build_settings(database_url="postgresql+asyncpg://nexo:nexo@127.0.0.1:5432/nexo")
    assert "super-secret" not in str(caught.value)
    assert "postgresql+psycopg" in str(caught.value)


def test_rejects_database_url_without_database_name() -> None:
    with pytest.raises(ValidationError):
        build_settings(database_url="postgresql+psycopg://nexo:nexo@127.0.0.1:5432/")


def test_rejects_database_url_with_newline() -> None:
    with pytest.raises(ValidationError) as caught:
        build_settings(database_url="postgresql+psycopg://nexo:secret\n@127.0.0.1:5432/nexo")
    assert "secret" not in str(caught.value)


def test_rejects_invalid_log_level() -> None:
    with pytest.raises(ValidationError):
        build_settings(log_level="verbose")


def test_normalizes_log_level_and_environment() -> None:
    settings = build_settings(app_env="TeSt", log_level="debug")
    assert settings.app_env is AppEnvironment.TEST
    assert settings.log_level == "DEBUG"


def test_rejects_empty_host() -> None:
    with pytest.raises(ValidationError):
        build_settings(app_host="  ")


def test_rejects_pool_size_below_one() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_env="test",
            database_url=LOCAL_DATABASE_URL,
            db_pool_size=0,
        )


def test_production_requires_host_password_and_specific_interface() -> None:
    with pytest.raises(ValidationError) as missing_password:
        build_settings(
            app_env="production",
            app_host="10.0.0.8",
            database_url="postgresql+psycopg://nexo@db.internal:5432/nexo",
        )
    assert "password" in str(missing_password.value)
    assert "db.internal" not in str(missing_password.value)

    with pytest.raises(ValidationError) as missing_host:
        build_settings(
            app_env="production",
            app_host="10.0.0.8",
            database_url="postgresql+psycopg://nexo:super-secret@/nexo",
        )
    assert "super-secret" not in str(missing_host.value)

    with pytest.raises(ValidationError) as wildcard_host:
        build_settings(
            app_env="production",
            app_host="0.0.0.0",
            database_url="postgresql+psycopg://nexo:super-secret@db.internal:5432/nexo",
        )
    assert "super-secret" not in str(wildcard_host.value)

    settings = build_settings(
        app_env="production",
        app_host="10.0.0.8",
        database_url="postgresql+psycopg://nexo:super-secret@db.internal:5432/nexo",
    )
    assert settings.app_env is AppEnvironment.PRODUCTION


def test_embedding_settings_hide_the_key_and_reject_bad_urls() -> None:
    settings = build_settings(
        embedding_api_key="local-test-key", completion_api_key="completion-key"
    )
    assert "local-test-key" not in repr(settings)
    assert "completion-key" not in repr(settings)
    assert settings.embedding_model == "text-embedding-3-small"
    normalized = build_settings(embedding_base_url="https://example.test/v1/")
    assert normalized.embedding_base_url == "https://example.test/v1"
    with pytest.raises(ValidationError):
        build_settings(embedding_base_url="ftp://example.test/v1")
    with pytest.raises(ValidationError):
        build_settings(embedding_api_key="secret\nvalue")
    with pytest.raises(ValidationError):
        build_settings(document_chunk_size=200, document_chunk_overlap=200)


def test_local_environment_may_bind_all_interfaces() -> None:
    settings = build_settings(app_env="local", app_host="0.0.0.0")
    assert settings.app_host == "0.0.0.0"
