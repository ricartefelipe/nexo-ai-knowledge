"""Document state machine."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from nexo_ai.domain.documents import Document, DocumentError, DocumentStatus


def _document(status: DocumentStatus = DocumentStatus.RECEIVED) -> Document:
    now = datetime(2026, 10, 12, tzinfo=UTC)
    return Document(
        id=uuid4(),
        filename="notas.md",
        media_type="text/markdown",
        content_sha256="a" * 64,
        byte_size=4,
        status=status,
        failure_detail=None,
        chunk_count=0,
        created_at=now,
        updated_at=now,
    )


def test_document_moves_through_the_ingestion_stages() -> None:
    document = _document()
    document.mark_extracted()
    document.mark_chunked(2)
    document.mark_embedded()
    assert document.status is DocumentStatus.EMBEDDED
    assert document.chunk_count == 2
    assert document.failure_detail is None


def test_failed_document_can_restart_and_completed_document_cannot() -> None:
    document = _document()
    document.mark_failed("A ingestão falhou.")
    assert document.status is DocumentStatus.FAILED
    document.restart()
    assert document.status.value == "received"
    assert document.chunk_count == 0
    assert document.failure_detail is None

    completed = _document(DocumentStatus.EMBEDDED)
    with pytest.raises(DocumentError, match="concluído"):
        completed.restart()
    with pytest.raises(DocumentError, match="concluído"):
        completed.mark_failed("A ingestão falhou.")


def test_invalid_transition_is_rejected() -> None:
    document = _document()
    with pytest.raises(DocumentError, match="transição"):
        document.mark_embedded()
    with pytest.raises(DocumentError, match="texto"):
        document.mark_extracted()
        document.mark_chunked(0)
