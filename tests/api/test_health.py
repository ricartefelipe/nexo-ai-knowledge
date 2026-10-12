"""Health HTTP contract."""

from fastapi.testclient import TestClient

from nexo_ai.api.dependencies.health import get_readiness_probe
from nexo_ai.api.middleware.correlation import CORRELATION_ID_HEADER
from nexo_ai.infrastructure.persistence.health import ReadinessReport
from nexo_ai.main import create_app
from tests.conftest import build_settings


class _ExplodingProbe:
    def check(self) -> ReadinessReport:
        raise AssertionError("liveness must not check the database")


class _UnavailableProbe:
    def check(self) -> ReadinessReport:
        return ReadinessReport(ready=False, detail="O banco de dados está indisponível.")


def test_liveness_does_not_require_a_database() -> None:
    settings = build_settings(database_url="postgresql+psycopg://nexo:nexo@127.0.0.1:1/nexo")
    app = create_app(settings)
    app.dependency_overrides[get_readiness_probe] = lambda: _ExplodingProbe()
    with TestClient(app) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["content-type"].startswith("application/json")


def test_readiness_returns_problem_details_when_the_probe_is_not_ready() -> None:
    app = create_app(build_settings())
    app.dependency_overrides[get_readiness_probe] = lambda: _UnavailableProbe()
    with TestClient(app) as client:
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["detail"] == "O banco de dados está indisponível."


def test_readiness_reports_a_closed_database_without_leaking_the_url() -> None:
    settings = build_settings(
        database_url="postgresql+psycopg://nexo:nexo@127.0.0.1:1/nexo",
        db_connect_timeout=1,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/health/ready", headers={CORRELATION_ID_HEADER: "ready-check-1"})
    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers[CORRELATION_ID_HEADER] == "ready-check-1"
    payload = response.json()
    assert payload["status"] == 503
    assert payload["title"] == "Service Unavailable"
    assert payload["detail"] == "O banco de dados está indisponível."
    assert payload["instance"] == "/health/ready"
    assert payload["correlation_id"] == "ready-check-1"
    assert "postgresql+psycopg" not in response.text
    assert "Traceback" not in response.text


def test_correlation_id_is_generated_when_the_header_is_unsafe() -> None:
    app = create_app(build_settings())
    with TestClient(app) as client:
        response = client.get("/health/live", headers={CORRELATION_ID_HEADER: "bad id"})
    assert response.status_code == 200
    generated = response.headers[CORRELATION_ID_HEADER]
    assert generated != "bad id"
    assert " " not in generated


def test_openapi_exposes_the_implemented_routes() -> None:
    app = create_app(build_settings())
    with TestClient(app) as client:
        document = client.get("/openapi.json")
    assert document.status_code == 200
    assert set(document.json()["paths"]) == {
        "/health/live",
        "/health/ready",
        "/api/v1/documents",
        "/api/v1/documents/{document_id}",
        "/api/v1/queries",
    }
