"""Guards around values stored in and read from document rows."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from nexo_ai.domain.documents import EmbeddingFailed
from nexo_ai.infrastructure.persistence.documents import (
    _as_datetime,
    _as_float,
    _as_int,
    _as_str,
    _as_uuid,
    _to_document,
    _to_reference,
    _vector_literal,
)


def test_vector_literal_formats_numbers_and_rejects_invalid_values() -> None:
    assert _vector_literal([1, 0.5]) == "[1,0.5]"
    with pytest.raises(EmbeddingFailed, match="inválido"):
        _vector_literal([float("nan")])
    with pytest.raises(EmbeddingFailed, match="inválido"):
        _vector_literal([True])


def test_row_conversion_rejects_corrupt_values() -> None:
    document_id = uuid4()
    now = datetime(2026, 10, 12, tzinfo=UTC)
    row = {
        "id": str(document_id),
        "filename": "notas.md",
        "media_type": "text/markdown",
        "content_sha256": "a" * 64,
        "byte_size": 4,
        "status": "embedded",
        "failure_detail": None,
        "chunk_count": 1,
        "created_at": now,
        "updated_at": now,
    }
    document = _to_document(row)
    assert document.id == document_id
    assert document.failure_detail is None
    with pytest.raises(TypeError):
        _as_str(1)
    with pytest.raises(TypeError):
        _as_int(True)
    with pytest.raises(TypeError):
        _as_uuid(1)
    with pytest.raises(TypeError):
        _as_datetime("2026-10-12")
    with pytest.raises(TypeError, match="distância"):
        _as_float(True)
    with pytest.raises(TypeError, match="distância"):
        _as_float(float("nan"))
    reference = _to_reference(
        {
            "document_id": document_id,
            "filename": "notas.md",
            "position": 0,
            "content": "prazo",
            "distance": 0.25,
        }
    )
    assert reference.document_id == document_id
    assert reference.distance == 0.25
