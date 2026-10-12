"""Deterministic character windows for extracted document text."""

from nexo_ai.domain.chunks import TextChunk
from nexo_ai.domain.documents import EmptyDocument


def chunk_text(text: str, *, size: int, overlap: int) -> list[TextChunk]:
    """Split text into ordered windows. The windows keep paragraph breaks when they fit."""

    if size < 1:
        raise ValueError("chunk size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("chunk overlap must be smaller than the chunk size")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if normalized == "":
        raise EmptyDocument("O documento não contém texto.")

    chunks: list[TextChunk] = []
    start = 0
    length = len(normalized)
    while start < length:
        end = min(start + size, length)
        if end < length:
            window = normalized[start:end]
            break_at = max(window.rfind("\n"), window.rfind(" "))
            if break_at >= size // 2:
                end = start + break_at
        piece = normalized[start:end].strip()
        if piece:
            chunks.append(TextChunk(position=len(chunks), content=piece))
        if end >= length:
            break
        next_start = end - overlap
        if next_start <= start:
            next_start = end
        start = next_start
    if not chunks:
        raise EmptyDocument("O documento não contém texto.")
    return chunks
