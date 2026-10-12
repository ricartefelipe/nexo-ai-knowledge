"""Process entrypoint."""

import pytest
import uvicorn

from nexo_ai.config.settings import get_settings
from nexo_ai.main import main
from tests.conftest import LOCAL_DATABASE_URL


def test_main_uses_process_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(*_args: object, **kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", LOCAL_DATABASE_URL)
    monkeypatch.setenv("APP_HOST", "127.0.0.1")
    monkeypatch.setenv("APP_PORT", "8123")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    get_settings.cache_clear()
    monkeypatch.setattr(uvicorn, "run", fake_run)

    main()

    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8123
    assert captured["factory"] is True
    assert captured["access_log"] is False
    assert captured["log_level"] == "info"


def test_module_entrypoint_exposes_main() -> None:
    import nexo_ai.__main__ as entrypoint

    assert entrypoint.main is main
