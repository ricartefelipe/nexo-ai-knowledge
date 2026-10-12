"""Document ingestion dependencies."""

from starlette.requests import Request

from nexo_ai.application.ingest import DocumentRepository, IngestDocument
from nexo_ai.config.settings import Settings


def get_ingest_document(request: Request) -> IngestDocument:
    """Return the ingestion use case stored by the composition root."""

    ingest_document: IngestDocument = request.app.state.ingest_document
    return ingest_document


def get_document_repository(request: Request) -> DocumentRepository:
    """Return the document repository stored by the composition root."""

    repository: DocumentRepository = request.app.state.document_repository
    return repository


def get_document_max_bytes(request: Request) -> int:
    """Return the configured upload limit."""

    settings: Settings = request.app.state.settings
    return settings.document_max_bytes
