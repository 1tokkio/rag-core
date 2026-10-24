"""Document readers for PDF, TXT and Markdown. Each returns normalized text and page spans."""

import io
from dataclasses import dataclass, field
from pathlib import PurePath

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.errors import AppError

# Text pages in a PDF are joined with this separator; offsets are measured on the joined text.
PAGE_SEPARATOR = "\n\n"

SUPPORTED_TYPES: dict[str, tuple[str, str]] = {
    ".pdf": ("pdf", "application/pdf"),
    ".txt": ("txt", "text/plain"),
    ".md": ("md", "text/markdown"),
}


@dataclass(frozen=True)
class PageSpan:
    page_number: int
    start_offset: int


@dataclass(frozen=True)
class ParsedDocument:
    file_type: str
    mime_type: str
    text: str
    title: str | None
    pages: list[PageSpan] = field(default_factory=list)


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def detect_file_type(filename: str) -> tuple[str, str]:
    suffix = PurePath(filename).suffix.lower()
    if suffix not in SUPPORTED_TYPES:
        raise AppError(
            status_code=400,
            code="UNSUPPORTED_FILE_TYPE",
            message="Only PDF, TXT and Markdown files are supported",
            fields={"filename": filename},
        )
    return SUPPORTED_TYPES[suffix]


def parse_document(filename: str, data: bytes) -> ParsedDocument:
    file_type, mime_type = detect_file_type(filename)
    if file_type == "pdf":
        return _parse_pdf(data, mime_type)
    return _parse_text(data, file_type, mime_type)


def _parse_text(data: bytes, file_type: str, mime_type: str) -> ParsedDocument:
    try:
        # utf-8-sig drops a leading byte order mark if present.
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AppError(400, "INVALID_FILE", "File is not valid UTF-8 text") from exc

    text = normalize_newlines(text).strip()
    _ensure_extractable(text)
    title = _markdown_title(text) if file_type == "md" else None
    return ParsedDocument(file_type=file_type, mime_type=mime_type, text=text, title=title)


def _parse_pdf(data: bytes, mime_type: str) -> ParsedDocument:
    if not data.startswith(b"%PDF-"):
        raise AppError(400, "INVALID_FILE", "File content is not a PDF")

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise AppError(400, "INVALID_FILE", "Encrypted PDFs are not supported")
        page_texts = [page.extract_text() or "" for page in reader.pages]
    except PdfReadError as exc:
        raise AppError(400, "INVALID_FILE", "PDF could not be read") from exc

    parts: list[str] = []
    pages: list[PageSpan] = []
    cursor = 0
    for page_number, raw in enumerate(page_texts, start=1):
        page_text = normalize_newlines(raw).strip()
        if not page_text:
            continue  # Pages without text are skipped but keep their page numbers.
        if parts:
            cursor += len(PAGE_SEPARATOR)
        pages.append(PageSpan(page_number=page_number, start_offset=cursor))
        parts.append(page_text)
        cursor += len(page_text)

    text = PAGE_SEPARATOR.join(parts)
    _ensure_extractable(text)
    return ParsedDocument(
        file_type="pdf",
        mime_type=mime_type,
        text=text,
        title=None,
        pages=pages,
    )


def _markdown_title(text: str) -> str | None:
    for line in text.split("\n"):
        if line.startswith("# "):
            title = line[2:].strip()
            return title or None
    return None


def _ensure_extractable(text: str) -> None:
    if not text:
        raise AppError(
            status_code=422,
            code="NO_EXTRACTABLE_TEXT",
            message="The file contains no extractable text",
        )
