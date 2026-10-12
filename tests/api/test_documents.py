"""Document HTTP contract."""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from nexo_ai.api.dependencies.documents import get_document_repository, get_ingest_document
from nexo_ai.application.ingest import IngestDocument
from nexo_ai.domain.documents import DocumentStatus
from nexo_ai.infrastructure.extraction.text import extract_document
from nexo_ai.main import create_app
from tests.conftest import build_settings
from tests.fakes import MemoryDocumentRepository, ScriptedEmbeddingClient


def _app() -> tuple[TestClient, MemoryDocumentRepository]:
    repository = MemoryDocumentRepository()
    ingest_document = IngestDocument(
        repository=repository,
        embeddings=ScriptedEmbeddingClient(dimensions=4),
        extract=extract_document,
        chunk_size=20,
        chunk_overlap=0,
        max_bytes=100,
        dimensions=4,
    )
    app = create_app(build_settings())
    app.dependency_overrides[get_ingest_document] = lambda: ingest_document
    app.dependency_overrides[get_document_repository] = lambda: repository
    return TestClient(app), repository


def test_upload_indexes_text_and_lookup_hides_the_vector() -> None:
    client, repository = _app()
    with client:
        created = client.post(
            "/api/v1/documents",
            files={"file": ("notas.md", b"# Nota\n", "text/markdown")},
        )
        assert created.status_code == 201
        body = created.json()
        assert body["filename"] == "notas.md"
        assert body["media_type"] == "text/markdown"
        assert body["status"] == DocumentStatus.EMBEDDED.value
        assert body["chunk_count"] == 1
        assert body["failure_detail"] is None
        assert "embedding" not in body
        document_id = body["id"]
        found = client.get(f"/api/v1/documents/{document_id}")
    assert found.status_code == 200
    assert found.json()["id"] == document_id
    assert len(repository.embeddings[UUID(document_id)][0]) == 4


def test_repeated_bytes_return_the_existing_document() -> None:
    client, _repository = _app()
    with client:
        first = client.post(
            "/api/v1/documents", files={"file": ("a.md", b"mesmo", "text/markdown")}
        )
        second = client.post(
            "/api/v1/documents",
            files={"file": ("b.md", b"mesmo", "text/markdown")},
        )
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


def test_rejected_upload_is_a_problem_document() -> None:
    client, repository = _app()
    with client:
        response = client.post(
            "/api/v1/documents",
            files={"file": ("notas.docx", b"abc", "application/octet-stream")},
        )
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert (
        response.json()["detail"] == "O tipo de arquivo não é aceito. Envie PDF, Markdown ou TXT."
    )
    assert repository.documents == {}


def test_missing_document_is_a_problem_document() -> None:
    client, _repository = _app()
    missing = uuid4()
    with client:
        response = client.get(f"/api/v1/documents/{missing}")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "O documento não foi encontrado."
    assert response.json()["instance"] == f"/api/v1/documents/{missing}"
