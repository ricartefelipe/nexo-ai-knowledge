"""HTTP schemas for document ingestion."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from nexo_ai.domain.documents import DocumentStatus


class DocumentResponse(BaseModel):
    """Public view of one document. Chunk text and vectors stay in the database."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    filename: str
    media_type: str
    content_sha256: str
    status: DocumentStatus
    chunk_count: int
    failure_detail: str | None
    embedding_model: str | None = None
    chunking_version: str | None = None
