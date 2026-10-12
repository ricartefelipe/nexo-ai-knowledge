"""Embedding port used by ingestion."""

from collections.abc import Sequence
from typing import Protocol


class EmbeddingClient(Protocol):
    """Turn text fragments into vectors of the configured dimension."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per input, in the same order."""
