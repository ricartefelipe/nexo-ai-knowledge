"""PDF, Markdown, and text extraction."""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

from nexo_ai.domain.documents import InvalidDocument, UnsupportedDocument
from nexo_ai.domain.text import ExtractedDocument

_MEDIA_TYPES = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
}


def extract_document(filename: str, content: bytes) -> ExtractedDocument:
    """Read text from a supported file. The original bytes are not modified."""

    suffix = Path(filename).suffix.lower()
    media_type = _MEDIA_TYPES.get(suffix)
    if media_type is None:
        raise UnsupportedDocument("O tipo de arquivo não é aceito. Envie PDF, Markdown ou TXT.")
    text = _pdf_text(content) if suffix == ".pdf" else _decode_utf8(content)
    return ExtractedDocument(media_type=media_type, text=text)


def _decode_utf8(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        raise InvalidDocument("O texto não está em UTF-8.") from None


def _pdf_text(content: bytes) -> str:
    if not content.startswith(b"%PDF"):
        raise InvalidDocument("O arquivo não é um PDF válido.")
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted:
            raise InvalidDocument("O PDF está protegido por senha.")
        pages = [(page.extract_text() or "") for page in reader.pages]
    except InvalidDocument:
        raise
    except FileNotDecryptedError:
        raise InvalidDocument("O PDF está protegido por senha.") from None
    except PdfReadError:
        raise InvalidDocument("O PDF não pôde ser lido.") from None
    return "\n".join(pages)
