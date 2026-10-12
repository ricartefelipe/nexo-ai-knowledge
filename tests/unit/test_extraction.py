"""File extraction."""

from io import BytesIO
from typing import Any, cast

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from nexo_ai.domain.documents import InvalidDocument, UnsupportedDocument
from nexo_ai.infrastructure.extraction.text import extract_document


def test_markdown_and_text_keep_their_media_types() -> None:
    markdown = extract_document("notas.md", b"# Titulo\n")
    assert markdown.media_type == "text/markdown"
    assert markdown.text == "# Titulo\n"
    plain = extract_document("notas.TXT", b"linha\n")
    assert plain.media_type == "text/plain"
    assert plain.text == "linha\n"


def test_invalid_text_and_suffix_are_rejected() -> None:
    with pytest.raises(InvalidDocument, match="UTF-8"):
        extract_document("notas.txt", b"\xff")
    with pytest.raises(UnsupportedDocument, match="PDF, Markdown ou TXT"):
        extract_document("notas.docx", b"abc")


def test_pdf_text_is_extracted_and_protected_files_are_rejected() -> None:
    extracted = extract_document("notas.pdf", _pdf_with_text())
    assert extracted.media_type == "application/pdf"
    assert extracted.text == "Hello PDF"

    protected = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.encrypt("secret")
    writer.write(protected)
    with pytest.raises(InvalidDocument, match="senha"):
        extract_document("notas.pdf", protected.getvalue())
    with pytest.raises(InvalidDocument, match="não é um PDF"):
        extract_document("notas.pdf", b"not-a-pdf")
    with pytest.raises(InvalidDocument, match="não pôde ser lido"):
        extract_document("notas.pdf", b"%PDF-1.4\nnot a real body")


def _pdf_with_text() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=144)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    page[NameObject("/Resources")] = resources
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 24 Tf 72 100 Td (Hello PDF) Tj ET")
    page.replace_contents(cast(Any, stream))
    raw = BytesIO()
    writer.write(raw)
    return raw.getvalue()
