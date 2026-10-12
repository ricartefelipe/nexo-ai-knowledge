"""A grounded answer and the stored fragments that support it."""

from dataclasses import dataclass
from uuid import UUID

from nexo_ai.domain.documents import DocumentError


class RetrievalError(DocumentError):
    """The question could not be answered. The message is safe for the caller."""


class CompletionNotConfigured(RetrievalError):
    """A query was requested without a language-model credential."""


class CompletionFailed(RetrievalError):
    """The language model did not return a usable answer."""


@dataclass(frozen=True, slots=True)
class SourceReference:
    """One indexed fragment close to the question."""

    document_id: UUID
    filename: str
    position: int
    content: str
    distance: float


@dataclass(frozen=True, slots=True)
class Answer:
    """Answer text plus the fragments used. Ungrounded answers cite nothing."""

    text: str
    grounded: bool
    references: tuple[SourceReference, ...]
