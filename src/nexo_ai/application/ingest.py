"""Ingest one document and persist each completed stage."""

import hashlib
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

import structlog

from nexo_ai.application.embeddings import EmbeddingClient
from nexo_ai.domain.chunking import chunk_text
from nexo_ai.domain.chunks import TextChunk
from nexo_ai.domain.documents import Document, DocumentError, DocumentStatus, UnsupportedDocument
from nexo_ai.domain.text import ExtractedDocument

logger = structlog.get_logger()


# Bump when chunk_text changes how fragments are cut; documents keep the version that cut them.
CHUNKING_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class IngestResult:
    """Outcome of one upload. `created` is false when the same bytes were already stored."""

    document: Document
    created: bool


class DocumentRepository(Protocol):
    """Persistence for documents and their chunks."""

    def find_by_hash(self, content_sha256: str) -> Document | None:
        """Return the document stored for these exact bytes, if any."""

    def get(self, document_id: UUID) -> Document | None:
        """Return one document by its identifier."""

    def add(self, document: Document) -> None:
        """Insert a document that has not been stored before."""

    def save(self, document: Document) -> None:
        """Update the document stage and counters."""

    def replace_chunks(self, document_id: UUID, chunks: Sequence[TextChunk]) -> None:
        """Replace all fragments of a document. Embeddings are cleared."""

    def delete(self, document_id: UUID) -> bool:
        """Remove the document and every chunk and vector derived from it."""
        ...

    def save_embeddings(self, document_id: UUID, embeddings: Sequence[Sequence[float]]) -> None:
        """Store one vector per fragment, in position order."""


class IngestDocument:
    """Receive bytes, extract text, chunk, embed, and record the resulting stage."""

    def __init__(
        self,
        repository: DocumentRepository,
        embeddings: EmbeddingClient,
        extract: Callable[[str, bytes], ExtractedDocument],
        *,
        chunk_size: int,
        chunk_overlap: int,
        max_bytes: int,
        dimensions: int,
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        self._repository = repository
        self._embeddings = embeddings
        self._extract = extract
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._max_bytes = max_bytes
        self._dimensions = dimensions
        self._embedding_model = embedding_model

    def execute(self, *, filename: str, content: bytes) -> IngestResult:
        """Ingest one file. A repeated hash of an embedded document is returned as-is."""

        started = time.perf_counter()
        safe_name = _safe_filename(filename)
        if content == b"":
            raise DocumentError("O arquivo está vazio.")
        if len(content) > self._max_bytes:
            raise DocumentError("O arquivo excede o tamanho máximo.")
        self._embeddings.embed(())
        extracted = self._extract(safe_name, content)
        chunks = chunk_text(
            extracted.text,
            size=self._chunk_size,
            overlap=self._chunk_overlap,
        )

        digest = hashlib.sha256(content).hexdigest()
        existing = self._repository.find_by_hash(digest)
        if (
            existing is not None
            and existing.status is DocumentStatus.EMBEDDED
            and existing.embedding_model == self._embedding_model
        ):
            return IngestResult(document=existing, created=False)

        now = datetime.now(UTC)
        created = existing is None
        if existing is None:
            document = Document(
                id=uuid4(),
                filename=safe_name,
                media_type=extracted.media_type,
                content_sha256=digest,
                byte_size=len(content),
                status=DocumentStatus.RECEIVED,
                failure_detail=None,
                chunk_count=0,
                created_at=now,
                updated_at=now,
            )
            self._repository.add(document)
        else:
            document = existing
            document.filename = safe_name
            document.media_type = extracted.media_type
            document.restart()
            self._repository.save(document)
            self._repository.replace_chunks(document.id, ())

        try:
            document.mark_extracted()
            self._repository.save(document)
            document.mark_chunked(len(chunks))
            self._repository.replace_chunks(document.id, chunks)
            self._repository.save(document)
            vectors = self._embeddings.embed([chunk.content for chunk in chunks])
            _require_vectors(vectors, len(chunks), self._dimensions)
            self._repository.save_embeddings(document.id, vectors)
            document.embedding_model = self._embedding_model
            document.chunking_version = CHUNKING_VERSION
            document.mark_embedded()
            self._repository.save(document)
        except DocumentError as exc:
            _record_failure(self._repository, document, exc.message)
            _log_ingest(document, started, result="error")
            raise
        except Exception as exc:
            _record_failure(self._repository, document, "A ingestão falhou.")
            _log_ingest(document, started, result="error", error_type=type(exc).__name__)
            raise DocumentError("A ingestão falhou.") from None

        _log_ingest(document, started, result="ok")
        return IngestResult(document=document, created=created)


def _safe_filename(filename: str) -> str:
    name = Path(filename).name
    if name in {"", ".", ".."}:
        raise UnsupportedDocument("O nome do arquivo é inválido.")
    return name


def _require_vectors(vectors: Sequence[Sequence[float]], count: int, dimensions: int) -> None:
    if len(vectors) != count or any(len(vector) != dimensions for vector in vectors):
        raise DocumentError("O provedor de embeddings devolveu um vetor com dimensão inesperada.")


def _record_failure(repository: DocumentRepository, document: Document, detail: str) -> None:
    if document.status is DocumentStatus.FAILED:
        return
    document.mark_failed(detail)
    repository.save(document)


def _log_ingest(
    document: Document,
    started: float,
    *,
    result: str,
    error_type: str | None = None,
) -> None:
    logger.info(
        "document_ingested",
        component="nexo_ai.ingestion",
        operation="ingest_document",
        result=result,
        document_id=str(document.id),
        document_status=document.status.value,
        chunk_count=document.chunk_count,
        duration_ms=round((time.perf_counter() - started) * 1000, 3),
        error_type=error_type,
    )
