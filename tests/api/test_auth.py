"""API credential: a no-op in the local profile, mandatory wherever a token is configured."""

from fastapi.testclient import TestClient

from nexo_ai.api.dependencies.documents import get_document_repository
from nexo_ai.api.dependencies.health import get_readiness_probe
from nexo_ai.infrastructure.persistence.health import ReadinessReport
from nexo_ai.main import create_app
from tests.conftest import build_settings
from tests.fakes import MemoryDocumentRepository

TOKEN = "k" * 40


class _ReadyProbe:
    def check(self) -> ReadinessReport:
        return ReadinessReport(ready=True, detail="")


def _client(token: str) -> TestClient:
    app = create_app(build_settings(api_auth_token=token))
    app.dependency_overrides[get_document_repository] = MemoryDocumentRepository
    app.dependency_overrides[get_readiness_probe] = _ReadyProbe
    return TestClient(app)


def test_without_a_configured_token_the_api_stays_open_for_local_use() -> None:
    with _client("") as client:
        assert (
            client.get("/api/v1/documents/00000000-0000-0000-0000-000000000000").status_code == 404
        )
        assert client.get("/").status_code == 200


def test_configured_token_protects_documents_queries_and_interface_but_not_health() -> None:
    with _client(TOKEN) as client:
        missing = client.get("/api/v1/documents/00000000-0000-0000-0000-000000000000")
        assert missing.status_code == 401
        assert missing.json()["detail"] == "Credencial ausente ou inválida."
        assert client.post("/api/v1/queries", json={"question": "x"}).status_code == 401
        assert client.get("/").status_code == 401
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 200

        wrong = client.get(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": "Bearer " + "x" * 40},
        )
        assert wrong.status_code == 401
        bearer = client.get(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        assert bearer.status_code == 404
        api_key = client.get(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000",
            headers={"X-Api-Key": TOKEN},
        )
        assert api_key.status_code == 404
