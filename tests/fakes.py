"""In-memory doubles for ingestion tests."""

from collections.abc import Sequence
from uuid import UUID

from nexo_ai.domain.chunks import TextChunk
from nexo_ai.domain.documents import Document, EmbeddingFailed


class MemoryDocumentRepository:
    """Document store that keeps the objects handed to it."""

    def __init__(self) -> None:
        self.documents: dict[UUID, Document] = {}
        self.chunks: dict[UUID, list[TextChunk]] = {}
        self.embeddings: dict[UUID, list[list[float]]] = {}

    def find_by_hash(self, content_sha256: str) -> Document | None:
        for document in self.documents.values():
            if document.content_sha256 == content_sha256:
                return document
        return None

    def get(self, document_id: UUID) -> Document | None:
        return self.documents.get(document_id)

    def add(self, document: Document) -> None:
        self.documents[document.id] = document

    def save(self, document: Document) -> None:
        self.documents[document.id] = document

    def replace_chunks(self, document_id: UUID, chunks: Sequence[TextChunk]) -> None:
        self.chunks[document_id] = list(chunks)
        self.embeddings.pop(document_id, None)

    def save_embeddings(self, document_id: UUID, embeddings: Sequence[Sequence[float]]) -> None:
        self.embeddings[document_id] = [list(vector) for vector in embeddings]


class ScriptedEmbeddingClient:
    """Return deterministic vectors and record the texts it received."""

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions
        self.calls: list[tuple[str, ...]] = []

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        batch = tuple(texts)
        self.calls.append(batch)
        if not batch:
            return []
        return [[float(index + 1)] * self.dimensions for index in range(len(batch))]


class FailingEmbeddingClient:
    """Pass the empty configuration probe, then fail the real request."""

    def __init__(self) -> None:
        self.calls = 0

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls += 1
        if not texts:
            return []
        raise EmbeddingFailed("O provedor de embeddings falhou.")


class ExplodingRepository(MemoryDocumentRepository):
    """Raise while storing vectors, after the document row exists."""

    def save_embeddings(self, document_id: UUID, embeddings: Sequence[Sequence[float]]) -> None:
        raise RuntimeError("token=super-secret")
