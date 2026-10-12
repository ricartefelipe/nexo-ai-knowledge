"""Ingestion use case."""

from collections.abc import Sequence

import pytest

from nexo_ai.application.ingest import IngestDocument
from nexo_ai.domain.documents import DocumentError, DocumentStatus, EmbeddingNotConfigured
from nexo_ai.infrastructure.embeddings.openai import UnconfiguredEmbeddingClient
from nexo_ai.infrastructure.extraction.text import extract_document
from tests.fakes import (
    ExplodingRepository,
    FailingEmbeddingClient,
    MemoryDocumentRepository,
    ScriptedEmbeddingClient,
)


def _use_case(
    repository: MemoryDocumentRepository,
    embeddings: ScriptedEmbeddingClient | FailingEmbeddingClient | UnconfiguredEmbeddingClient,
) -> IngestDocument:
    return IngestDocument(
        repository=repository,
        embeddings=embeddings,
        extract=extract_document,
        chunk_size=8,
        chunk_overlap=2,
        max_bytes=100,
        dimensions=4,
    )


def test_ingest_persists_each_stage_and_returns_the_same_document_for_the_same_bytes() -> None:
    repository = MemoryDocumentRepository()
    embeddings = ScriptedEmbeddingClient(dimensions=4)
    use_case = _use_case(repository, embeddings)

    first = use_case.execute(filename="../notas.md", content=b"aaaa\nbbbbcccc")
    assert first.created is True
    assert first.document.filename == "notas.md"
    assert first.document.media_type == "text/markdown"
    assert first.document.status is DocumentStatus.EMBEDDED
    assert first.document.chunk_count == 3
    assert repository.chunks[first.document.id][0].content == "aaaa"
    assert len(repository.embeddings[first.document.id][0]) == 4
    assert embeddings.calls[0] == ()
    assert embeddings.calls[1] == ("aaaa", "aa\nbbbbc", "bcccc")

    second = use_case.execute(filename="outro.md", content=b"aaaa\nbbbbcccc")
    assert second.created is False
    assert second.document.id == first.document.id
    assert len(repository.documents) == 1


def test_provider_failure_is_persisted_and_a_later_upload_can_finish() -> None:
    repository = MemoryDocumentRepository()
    failing = _use_case(repository, FailingEmbeddingClient())
    with pytest.raises(DocumentError, match="falhou"):
        failing.execute(filename="notas.md", content=b"conteudo")
    failed = next(iter(repository.documents.values()))
    assert failed.status is DocumentStatus.FAILED
    assert failed.failure_detail == "O provedor de embeddings falhou."

    recovered = _use_case(repository, ScriptedEmbeddingClient(dimensions=4))
    result = recovered.execute(filename="notas.md", content=b"conteudo")
    assert result.created is False
    assert result.document.id == failed.id
    assert result.document.status is DocumentStatus.EMBEDDED


def test_unexpected_storage_error_does_not_expose_the_message() -> None:
    repository = ExplodingRepository()
    use_case = _use_case(repository, ScriptedEmbeddingClient(dimensions=4))
    with pytest.raises(DocumentError, match="ingestão falhou") as caught:
        use_case.execute(filename="notas.md", content=b"conteudo")
    assert "super-secret" not in str(caught.value)
    document = next(iter(repository.documents.values()))
    assert document.status is DocumentStatus.FAILED
    assert document.failure_detail == "A ingestão falhou."
    assert "super-secret" not in (document.failure_detail or "")


def test_local_rejection_does_not_store_a_document() -> None:
    repository = MemoryDocumentRepository()
    use_case = _use_case(repository, ScriptedEmbeddingClient(dimensions=4))
    with pytest.raises(DocumentError, match="vazio"):
        use_case.execute(filename="notas.md", content=b"")
    with pytest.raises(DocumentError, match="tamanho"):
        use_case.execute(filename="notas.md", content=b"x" * 101)
    with pytest.raises(DocumentError, match="não é aceito"):
        use_case.execute(filename="notas.docx", content=b"abc")
    assert repository.documents == {}


def test_invalid_name_and_unexpected_vector_do_not_pretend_success() -> None:
    repository = MemoryDocumentRepository()
    use_case = _use_case(repository, ScriptedEmbeddingClient(dimensions=4))
    with pytest.raises(DocumentError, match="inválido"):
        use_case.execute(filename="..", content=b"abc")
    assert repository.documents == {}

    class ShortVectors(ScriptedEmbeddingClient):
        def embed(self, texts: Sequence[str]) -> list[list[float]]:
            if not texts:
                return []
            return [[1.0, 2.0]]

    short = _use_case(repository, ShortVectors(dimensions=4))
    with pytest.raises(DocumentError, match="dimensão"):
        short.execute(filename="notas.md", content=b"abc")
    failed = next(iter(repository.documents.values()))
    assert failed.status is DocumentStatus.FAILED


def test_missing_provider_does_not_store_a_document() -> None:
    repository = MemoryDocumentRepository()
    use_case = _use_case(repository, UnconfiguredEmbeddingClient())
    with pytest.raises(EmbeddingNotConfigured, match="não está configurado"):
        use_case.execute(filename="notas.md", content=b"abc")
    assert repository.documents == {}
