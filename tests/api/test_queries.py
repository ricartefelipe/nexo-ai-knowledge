"""Query HTTP contract."""

from uuid import uuid4

from fastapi.testclient import TestClient

from nexo_ai.api.dependencies.queries import get_answer_question
from nexo_ai.application.retrieve import AnswerQuestion
from nexo_ai.domain.retrieval import SourceReference
from nexo_ai.main import create_app
from tests.conftest import build_settings
from tests.fakes import MemoryChunkSearch, ScriptedCompletionClient, ScriptedEmbeddingClient


def _client(matches: list[SourceReference]) -> TestClient:
    use_case = AnswerQuestion(
        search=MemoryChunkSearch(matches),
        embeddings=ScriptedEmbeddingClient(dimensions=4),
        completion=ScriptedCompletionClient(),
        max_distance=0.5,
        match_limit=5,
        max_chars=200,
        dimensions=4,
    )
    app = create_app(build_settings())
    app.dependency_overrides[get_answer_question] = lambda: use_case
    return TestClient(app)


def test_query_returns_the_answer_and_the_source() -> None:
    source = SourceReference(
        document_id=uuid4(),
        filename="contrato.md",
        position=0,
        content="O prazo de entrega é de 30 dias corridos.",
        distance=0.2,
    )
    with _client([source]) as client:
        response = client.post("/api/v1/queries", json={"question": "qual o prazo?"})
    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert body["support"] == "supported"
    assert body["sources_found"] is True
    assert body["answer"] == "O prazo de entrega é de 30 dias corridos [1]."
    assert body["references"] == [
        {
            "document_id": str(source.document_id),
            "filename": "contrato.md",
            "position": 0,
            "content": "O prazo de entrega é de 30 dias corridos.",
            "distance": 0.2,
        }
    ]


def test_query_without_sources_is_explicit() -> None:
    with _client([]) as client:
        response = client.post("/api/v1/queries", json={"question": "qual o prazo?"})
    assert response.status_code == 200
    assert response.json()["grounded"] is False
    assert response.json()["support"] == "no_sources"
    assert response.json()["sources_found"] is False
    assert response.json()["references"] == []
    assert "não respondem" in response.json()["answer"]


def test_empty_question_is_a_problem_document() -> None:
    with _client([]) as client:
        response = client.post("/api/v1/queries", json={"question": "  "})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "A pergunta está vazia."
