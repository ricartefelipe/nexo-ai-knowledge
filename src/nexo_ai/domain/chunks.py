"""Text fragment produced by ingestion."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextChunk:
    """One ordered fragment of an extracted document."""

    position: int
    content: str
