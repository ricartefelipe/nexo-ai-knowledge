"""Text extracted from an uploaded file."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    """Media type and text. The original bytes stay with the caller."""

    media_type: str
    text: str
