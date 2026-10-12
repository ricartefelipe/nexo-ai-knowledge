"""Local interface contract."""

import pytest
from fastapi.testclient import TestClient

from nexo_ai.interface import assets
from nexo_ai.interface.assets import read_interface_file
from nexo_ai.main import create_app
from tests.conftest import build_settings


def _client() -> TestClient:
    return TestClient(create_app(build_settings()))


def test_page_is_html_and_does_not_inline_scripts() -> None:
    with _client() as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    policy = response.headers["content-security-policy"]
    assert "script-src 'self'" in policy
    assert "unsafe-inline" not in policy
    page = response.text
    assert 'lang="pt-BR"' in page
    assert 'id="upload-form"' in page
    assert 'id="query-form"' in page
    assert 'src="/assets/app.js"' in page
    assert "<script>" not in page
    assert "innerHTML" not in page


def test_assets_are_served_with_the_api_paths_they_call() -> None:
    with _client() as client:
        stylesheet = client.get("/assets/app.css")
        script = client.get("/assets/app.js")
    assert stylesheet.status_code == 200
    assert stylesheet.headers["content-type"].startswith("text/css")
    assert ".workspace" in stylesheet.text
    assert script.status_code == 200
    assert script.headers["content-type"].startswith("text/javascript")
    assert "innerHTML" not in script.text
    assert "insertAdjacentHTML" not in script.text
    for path in ("/health/ready", "/api/v1/documents", "/api/v1/queries"):
        assert path in script.text


def test_unknown_asset_is_a_problem() -> None:
    with _client() as client:
        response = client.get("/assets/index.html")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "O recurso não foi encontrado."


def test_packaged_reader_refuses_unknown_names() -> None:
    page = read_interface_file("index.html")
    assert b"Nexo AI" in page
    with pytest.raises(FileNotFoundError):
        read_interface_file("../settings.py")


def test_missing_packaged_file_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(assets, "_ALLOWED_FILES", frozenset({"missing.txt"}))
    with pytest.raises(FileNotFoundError):
        read_interface_file("missing.txt")
