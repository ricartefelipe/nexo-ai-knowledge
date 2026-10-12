"""Document ingestion against PostgreSQL and pgvector."""

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from nexo_ai.api.dependencies.documents import get_document_repository, get_ingest_document
from nexo_ai.application.ingest import IngestDocument
from nexo_ai.config.settings import get_settings
from nexo_ai.infrastructure.embeddings.openai import EMBEDDING_DIMENSIONS
from nexo_ai.infrastructure.extraction.text import extract_document
from nexo_ai.infrastructure.persistence.database import create_db_engine, create_session_factory
from nexo_ai.infrastructure.persistence.documents import SqlDocumentRepository
from nexo_ai.main import create_app
from tests.conftest import build_settings
from tests.fakes import ScriptedEmbeddingClient

pytestmark = pytest.mark.integration


def test_upload_stores_a_vector_and_a_repeat_does_not_duplicate(database_url: str) -> None:
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    settings = build_settings(database_url=database_url)
    engine = create_db_engine(settings)
    repository = SqlDocumentRepository(create_session_factory(engine))
    embeddings = ScriptedEmbeddingClient(EMBEDDING_DIMENSIONS)
    ingest_document = IngestDocument(
        repository=repository,
        embeddings=embeddings,
        extract=extract_document,
        chunk_size=1000,
        chunk_overlap=200,
        max_bytes=10_000,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    app = create_app(settings)
    app.dependency_overrides[get_ingest_document] = lambda: ingest_document
    app.dependency_overrides[get_document_repository] = lambda: repository
    try:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM document_chunks"))
            connection.execute(text("DELETE FROM documents"))
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/documents",
                files={"file": ("notas.md", b"# Nota de teste\n", "text/markdown")},
            )
            assert created.status_code == 201
            document_id = created.json()["id"]
            repeated = client.post(
                "/api/v1/documents",
                files={"file": ("notas.md", b"# Nota de teste\n", "text/markdown")},
            )
            assert repeated.status_code == 200
            assert repeated.json()["id"] == document_id
            found = client.get(f"/api/v1/documents/{document_id}")
            assert found.status_code == 200
            assert found.json()["status"] == "embedded"
            with engine.connect() as connection:
                dimension: int = connection.execute(
                    text(
                        """
                        SELECT atttypmod
                        FROM pg_attribute
                        WHERE attrelid = 'document_chunks'::regclass
                          AND attname = 'embedding'
                        """
                    )
                ).scalar_one()
                stored: int = connection.execute(
                    text(
                        """
                        SELECT vector_dims(embedding)
                        FROM document_chunks
                        WHERE document_id = :document_id
                        """
                    ),
                    {"document_id": document_id},
                ).scalar_one()
                count: int = connection.execute(text("SELECT count(*) FROM documents")).scalar_one()
    finally:
        engine.dispose()

    assert dimension == EMBEDDING_DIMENSIONS
    assert stored == EMBEDDING_DIMENSIONS
    assert count == 1
