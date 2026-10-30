"""Document upload and lookup."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status

from nexo_ai.api.dependencies.documents import (
    get_document_max_bytes,
    get_document_repository,
    get_ingest_document,
)
from nexo_ai.api.schemas.documents import DocumentResponse
from nexo_ai.api.schemas.problem import ProblemDetails
from nexo_ai.application.ingest import DocumentRepository, IngestDocument
from nexo_ai.domain.documents import Document, DocumentError

router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {
            "model": DocumentResponse,
            "description": "Os mesmos bytes já estavam indexados.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ProblemDetails},
    },
)
def create_document(
    response: Response,
    file: Annotated[UploadFile, File()],
    ingest_document: Annotated[IngestDocument, Depends(get_ingest_document)],
    max_bytes: Annotated[int, Depends(get_document_max_bytes)],
) -> DocumentResponse:
    """Ingest one PDF, Markdown, or text file."""

    filename = file.filename or ""
    content = file.file.read(max_bytes + 1)
    try:
        result = ingest_document.execute(filename=filename, content=content)
    except DocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.message,
        ) from None
    response.status_code = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    return _response(result.document)


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": ProblemDetails}},
)
def read_document(
    document_id: UUID,
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
) -> DocumentResponse:
    """Return the persisted ingestion stage of one document."""

    document = repository.get(document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O documento não foi encontrado.",
        )
    return _response(document)


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"model": ProblemDetails}},
)
def delete_document(
    document_id: UUID,
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
) -> Response:
    """Remove one document with every fragment and vector derived from it."""
    if not repository.delete(document_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O documento não foi encontrado.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        media_type=document.media_type,
        content_sha256=document.content_sha256,
        status=document.status,
        chunk_count=document.chunk_count,
        failure_detail=document.failure_detail,
        embedding_model=document.embedding_model,
        chunking_version=document.chunking_version,
    )
