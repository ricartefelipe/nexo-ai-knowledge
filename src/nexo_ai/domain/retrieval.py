"""A grounded answer and the stored fragments that support it."""

from dataclasses import dataclass
from enum import StrEnum
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


class SupportStatus(StrEnum):
    """How far the answer is backed by the returned fragments.

    `no_sources`: nothing indexed was close enough; the model was not called.
    `supported`: the model cited the fragments and its text overlaps them.
    `unsupported`: fragments were found, but the text does not cite them or does not
    share content with them — the answer is returned for inspection, not as verified.
    """

    NO_SOURCES = "no_sources"
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class Answer:
    """Answer text, its support status and the fragments that were close enough.

    `grounded` is true only for `supported`: finding sources is not the same as being
    backed by them.
    """

    text: str
    support: SupportStatus
    references: tuple[SourceReference, ...]

    @property
    def grounded(self) -> bool:
        return self.support is SupportStatus.SUPPORTED

    @property
    def sources_found(self) -> bool:
        return len(self.references) > 0
