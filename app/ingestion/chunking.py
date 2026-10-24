"""Character-based chunking with overlap. Offsets point into the normalized document text."""

from bisect import bisect_right
from dataclasses import dataclass

from app.core.errors import AppError
from app.ingestion.parsers import PageSpan


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    content: str
    start_offset: int
    end_offset: int
    page_number: int | None


def validate_chunk_config(chunk_size: int, chunk_overlap: int, max_chunk_size: int) -> None:
    if not 1 <= chunk_size <= max_chunk_size:
        raise AppError(
            status_code=400,
            code="VALIDATION_ERROR",
            message=f"chunk_size must be between 1 and {max_chunk_size}",
            fields={"chunk_size": str(chunk_size)},
        )
    if not 0 <= chunk_overlap < chunk_size:
        raise AppError(
            status_code=400,
            code="VALIDATION_ERROR",
            message="chunk_overlap must be >= 0 and smaller than chunk_size",
            fields={"chunk_overlap": str(chunk_overlap)},
        )


def split_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    pages: list[PageSpan] | None = None,
) -> list[TextChunk]:
    """Split text into ordered, non-empty chunks. Assumes a validated configuration."""
    if chunk_size < 1 or not 0 <= chunk_overlap < chunk_size:
        raise ValueError("invalid chunk configuration")

    step = chunk_size - chunk_overlap
    spans: list[tuple[str, int, int]] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        raw = text[start:end]
        content = raw.strip()
        if content:
            content_start = start + (len(raw) - len(raw.lstrip()))
            spans.append((content, content_start, content_start + len(content)))
        if end == len(text):
            break
        start += step

    page_starts = [page.start_offset for page in pages] if pages else []
    chunks: list[TextChunk] = []
    for index, (content, start_offset, end_offset) in enumerate(spans):
        chunks.append(
            TextChunk(
                chunk_index=index,
                content=content,
                start_offset=start_offset,
                end_offset=end_offset,
                page_number=_page_for_offset(pages, page_starts, start_offset),
            )
        )
    return chunks


def _page_for_offset(
    pages: list[PageSpan] | None, page_starts: list[int], offset: int
) -> int | None:
    if not pages:
        return None
    position = bisect_right(page_starts, offset) - 1
    return pages[position].page_number if position >= 0 else None
