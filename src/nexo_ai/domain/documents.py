"""Document identity and the ingestion state machine."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID


class DocumentStatus(StrEnum):
    """Persisted stages of one ingestion."""

    RECEIVED = "received"
    EXTRACTED = "extracted"
    CHUNKED = "chunked"
    EMBEDDED = "embedded"
    FAILED = "failed"


class DocumentError(Exception):
    """Failure whose message is safe to return to the caller."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnsupportedDocument(DocumentError):
    """The upload is not a PDF, Markdown, or text file."""


class InvalidDocument(DocumentError):
    """The upload cannot be ingested."""


class EmptyDocument(DocumentError):
    """Extraction produced no text."""


class EmbeddingNotConfigured(DocumentError):
    """Ingestion was requested without an embedding provider."""


class EmbeddingFailed(DocumentError):
    """The embedding provider did not return a usable vector."""


@dataclass(slots=True)
class Document:
    """One uploaded file and the last committed ingestion stage."""

    id: UUID
    filename: str
    media_type: str
    content_sha256: str
    byte_size: int
    status: DocumentStatus
    failure_detail: str | None
    chunk_count: int
    created_at: datetime
    updated_at: datetime
    embedding_model: str | None = None
    chunking_version: str | None = None

    def mark_extracted(self) -> None:
        self._move(DocumentStatus.RECEIVED, DocumentStatus.EXTRACTED)

    def mark_chunked(self, chunk_count: int) -> None:
        if chunk_count < 1:
            raise InvalidDocument("O documento não contém texto.")
        self._move(DocumentStatus.EXTRACTED, DocumentStatus.CHUNKED)
        self.chunk_count = chunk_count

    def mark_embedded(self) -> None:
        self._move(DocumentStatus.CHUNKED, DocumentStatus.EMBEDDED)

    def mark_failed(self, detail: str) -> None:
        if self.status is DocumentStatus.EMBEDDED:
            raise DocumentError("Um documento concluído não pode falhar.")
        if self.status is DocumentStatus.FAILED:
            raise DocumentError("O documento já está marcado como falha.")
        self.status = DocumentStatus.FAILED
        self.failure_detail = detail
        self.updated_at = datetime.now(UTC)

    def restart(self) -> None:
        if self.status is DocumentStatus.EMBEDDED:
            raise DocumentError("Um documento concluído não pode ser reiniciado.")
        self.status = DocumentStatus.RECEIVED
        self.failure_detail = None
        self.chunk_count = 0
        self.updated_at = datetime.now(UTC)

    def _move(self, expected: DocumentStatus, target: DocumentStatus) -> None:
        if self.status is not expected:
            raise DocumentError("A transição de estado do documento é inválida.")
        self.status = target
        self.failure_detail = None
        self.updated_at = datetime.now(UTC)
