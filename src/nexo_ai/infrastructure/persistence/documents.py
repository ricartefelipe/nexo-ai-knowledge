"""SQL persistence for documents and chunk vectors."""

import math
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql.elements import TextClause

from nexo_ai.domain.chunks import TextChunk
from nexo_ai.domain.documents import Document, DocumentStatus, EmbeddingFailed
from nexo_ai.domain.retrieval import SourceReference

_SELECT_BY_HASH = """
    SELECT id, filename, media_type, content_sha256, byte_size, status,
           failure_detail, chunk_count, created_at, updated_at
    FROM documents
    WHERE content_sha256 = :content_sha256
"""
_SELECT_BY_ID = """
    SELECT id, filename, media_type, content_sha256, byte_size, status,
           failure_detail, chunk_count, created_at, updated_at
    FROM documents
    WHERE id = :id
"""
_NEAREST_CHUNKS = """
    SELECT document_id, filename, position, content, distance
    FROM (
        SELECT d.id AS document_id,
               d.filename,
               c.position,
               c.content,
               (c.embedding <=> CAST(:embedding AS vector)) AS distance
        FROM document_chunks AS c
        JOIN documents AS d ON d.id = c.document_id
        WHERE d.status = 'embedded'
          AND c.embedding IS NOT NULL
    ) AS ranked
    WHERE distance <= :max_distance
    ORDER BY distance
    LIMIT :limit
"""


class SqlDocumentRepository:
    """Store documents with SQLAlchemy sessions opened per operation."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def find_by_hash(self, content_sha256: str) -> Document | None:
        return self._fetch(_SELECT_BY_HASH, {"content_sha256": content_sha256})

    def get(self, document_id: UUID) -> Document | None:
        return self._fetch(_SELECT_BY_ID, {"id": document_id})

    def add(self, document: Document) -> None:
        statement = text(
            """
            INSERT INTO documents (
                id, filename, media_type, content_sha256, byte_size, status,
                failure_detail, chunk_count, created_at, updated_at
            ) VALUES (
                :id, :filename, :media_type, :content_sha256, :byte_size, :status,
                :failure_detail, :chunk_count, :created_at, :updated_at
            )
            """
        )
        self._execute(statement, _document_params(document))

    def save(self, document: Document) -> None:
        statement = text(
            """
            UPDATE documents
            SET filename = :filename,
                media_type = :media_type,
                status = :status,
                failure_detail = :failure_detail,
                chunk_count = :chunk_count,
                updated_at = :updated_at
            WHERE id = :id
            """
        )
        self._execute(statement, _document_params(document))

    def replace_chunks(self, document_id: UUID, chunks: Sequence[TextChunk]) -> None:
        with self._session_factory() as session:
            session.execute(
                text("DELETE FROM document_chunks WHERE document_id = :document_id"),
                {"document_id": document_id},
            )
            for chunk in chunks:
                session.execute(
                    text(
                        """
                        INSERT INTO document_chunks (document_id, position, content, embedding)
                        VALUES (:document_id, :position, :content, NULL)
                        """
                    ),
                    {
                        "document_id": document_id,
                        "position": chunk.position,
                        "content": chunk.content,
                    },
                )
            session.commit()

    def save_embeddings(self, document_id: UUID, embeddings: Sequence[Sequence[float]]) -> None:
        with self._session_factory() as session:
            for position, vector in enumerate(embeddings):
                updated = session.execute(
                    text(
                        """
                        UPDATE document_chunks
                        SET embedding = CAST(:embedding AS vector)
                        WHERE document_id = :document_id AND position = :position
                        RETURNING position
                        """
                    ),
                    {
                        "document_id": document_id,
                        "position": position,
                        "embedding": _vector_literal(vector),
                    },
                ).scalar_one_or_none()
                if updated is None:
                    raise EmbeddingFailed("O fragmento não está disponível para receber o vetor.")
            session.commit()

    def nearest_chunks(
        self,
        embedding: Sequence[float],
        *,
        limit: int,
        max_distance: float,
    ) -> list[SourceReference]:
        with self._session_factory() as session:
            rows = (
                session.execute(
                    text(_NEAREST_CHUNKS),
                    {
                        "embedding": _vector_literal(embedding),
                        "max_distance": max_distance,
                        "limit": limit,
                    },
                )
                .mappings()
                .all()
            )
        return [_to_reference(cast(Mapping[str, Any], row)) for row in rows]

    def _fetch(self, statement: str, params: Mapping[str, object]) -> Document | None:
        with self._session_factory() as session:
            row = session.execute(text(statement), params).mappings().one_or_none()
        if row is None:
            return None
        return _to_document(cast(Mapping[str, Any], row))

    def _execute(self, statement: TextClause, params: Mapping[str, object]) -> None:
        with self._session_factory() as session:
            session.execute(statement, params)
            session.commit()


def _document_params(document: Document) -> dict[str, object]:
    return {
        "id": document.id,
        "filename": document.filename,
        "media_type": document.media_type,
        "content_sha256": document.content_sha256,
        "byte_size": document.byte_size,
        "status": document.status.value,
        "failure_detail": document.failure_detail,
        "chunk_count": document.chunk_count,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


def _to_document(row: Mapping[str, Any]) -> Document:
    return Document(
        id=_as_uuid(row["id"]),
        filename=_as_str(row["filename"]),
        media_type=_as_str(row["media_type"]),
        content_sha256=_as_str(row["content_sha256"]),
        byte_size=_as_int(row["byte_size"]),
        status=DocumentStatus(_as_str(row["status"])),
        failure_detail=_as_optional_str(row["failure_detail"]),
        chunk_count=_as_int(row["chunk_count"]),
        created_at=_as_datetime(row["created_at"]),
        updated_at=_as_datetime(row["updated_at"]),
    )


def _to_reference(row: Mapping[str, Any]) -> SourceReference:
    return SourceReference(
        document_id=_as_uuid(row["document_id"]),
        filename=_as_str(row["filename"]),
        position=_as_int(row["position"]),
        content=_as_str(row["content"]),
        distance=_as_float(row["distance"]),
    )


def _as_float(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError("distância inválida")
    if not math.isfinite(value):
        raise TypeError("distância inválida")
    return float(value)


def _vector_literal(values: Sequence[float]) -> str:
    parts: list[str] = []
    for value in values:
        if (
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(value)
        ):
            raise EmbeddingFailed("O provedor de embeddings devolveu um vetor inválido.")
        parts.append(format(float(value), ".17g"))
    return "[" + ",".join(parts) + "]"


def _as_str(value: object) -> str:
    if isinstance(value, str):
        return value
    raise TypeError("coluna textual inválida")


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    return _as_str(value)


def _as_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("coluna numérica inválida")
    return value


def _as_uuid(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    raise TypeError("identificador inválido")


def _as_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    raise TypeError("instante inválido")
