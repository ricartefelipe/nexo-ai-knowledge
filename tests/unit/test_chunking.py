"""Character windows."""

import pytest

from nexo_ai.domain.chunking import chunk_text
from nexo_ai.domain.documents import EmptyDocument


def test_chunks_keep_a_late_break_and_overlap() -> None:
    chunks = chunk_text("aaaa\nbbbbcccc", size=8, overlap=2)
    assert [chunk.content for chunk in chunks] == ["aaaa", "aa\nbbbbc", "bcccc"]
    assert [chunk.position for chunk in chunks] == [0, 1, 2]


def test_chunks_cover_text_without_a_break() -> None:
    chunks = chunk_text("abcdefghij", size=4, overlap=1)
    assert [chunk.content for chunk in chunks] == ["abcd", "defg", "ghij"]


def test_overlap_cannot_walk_backwards() -> None:
    chunks = chunk_text("aaaa\nxxYYYYYYYY", size=8, overlap=6)
    assert chunks[0].content == "aaaa"
    assert chunks[1].content.startswith("xx")


def test_blank_text_is_rejected() -> None:
    with pytest.raises(EmptyDocument, match="não contém texto"):
        chunk_text("  \n\t", size=8, overlap=2)
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("abc", size=4, overlap=4)
    with pytest.raises(ValueError, match="positive"):
        chunk_text("abc", size=0, overlap=0)
