"""Vector search against PostgreSQL and pgvector."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from nexo_ai.api.dependencies.queries import get_answer_question
from nexo_ai.application.retrieve import AnswerQuestion
from nexo_ai.config.settings import get_settings
from nexo_ai.domain.chunks import TextChunk
from nexo_ai.domain.documents import Document, DocumentStatus
from nexo_ai.infrastructure.embeddings.openai import EMBEDDING_DIMENSIONS
from nexo_ai.infrastructure.persistence.database import create_db_engine, create_session_factory
from nexo_ai.infrastructure.persistence.documents import SqlDocumentRepository
from nexo_ai.main import create_app
from tests.conftest import build_settings
from tests.fakes import ScriptedCompletionClient

pytestmark = pytest.mark.integration


class _FixedEmbedding:
    def __init__(self, vector: list[float]) -> None:
        self.vector = vector
        self.calls: list[tuple[str, ...]] = []

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        batch = tuple(texts)
        self.calls.append(batch)
        if not batch:
            return []
        return [self.vector for _ in batch]


def _document(
    filename: str, content: str, vector: list[float], repository: SqlDocumentRepository
) -> None:
    now = datetime.now(UTC)
    document = Document(
        id=uuid4(),
        filename=filename,
        media_type="text/markdown",
        content_sha256=uuid4().hex + uuid4().hex,
        byte_size=len(content),
        status=DocumentStatus.RECEIVED,
        failure_detail=None,
        chunk_count=0,
        created_at=now,
        updated_at=now,
    )
    repository.add(document)
    document.mark_extracted()
    repository.save(document)
    document.mark_chunked(1)
    repository.replace_chunks(document.id, [TextChunk(position=0, content=content)])
    repository.save(document)
    repository.save_embeddings(document.id, [vector])
    document.mark_embedded()
    repository.save(document)


def test_query_returns_the_nearest_indexed_fragment(database_url: str) -> None:
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    settings = build_settings(database_url=database_url)
    engine = create_db_engine(settings)
    repository = SqlDocumentRepository(create_session_factory(engine))
    near = [1.0] * EMBEDDING_DIMENSIONS
    far = [-1.0] * EMBEDDING_DIMENSIONS
    embeddings = _FixedEmbedding(near)
    completion = ScriptedCompletionClient("O prazo é de 30 dias.")
    use_case = AnswerQuestion(
        search=repository,
        embeddings=embeddings,
        completion=completion,
        max_distance=0.5,
        match_limit=5,
        max_chars=200,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    app = create_app(settings)
    app.dependency_overrides[get_answer_question] = lambda: use_case
    try:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM document_chunks"))
            connection.execute(text("DELETE FROM documents"))
        _document("contrato.md", "O prazo é de 30 dias.", near, repository)
        _document("outro.md", "A sede fica em outra cidade.", far, repository)
        with TestClient(app) as client:
            response = client.post("/api/v1/queries", json={"question": "qual o prazo?"})
    finally:
        engine.dispose()

    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert body["answer"] == "O prazo é de 30 dias."
    assert len(body["references"]) == 1
    assert body["references"][0]["filename"] == "contrato.md"
    assert body["references"][0]["content"] == "O prazo é de 30 dias."
    assert body["references"][0]["distance"] == pytest.approx(0, abs=1e-6)
    assert completion.calls[-1][1][0].filename == "contrato.md"
