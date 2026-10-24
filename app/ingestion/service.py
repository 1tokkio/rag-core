"""Ingestion use case: validate, parse, chunk and persist one document atomically."""

import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import PurePath

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.db.models import Chunk, Document
from app.ingestion.chunking import split_text, validate_chunk_config
from app.ingestion.parsers import parse_document


def ingest_document(
    session: Session,
    *,
    settings: Settings,
    filename: str,
    data: bytes,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    title: str | None = None,
) -> Document:
    """Persist a document and its chunks, or persist nothing and raise AppError."""
    size = chunk_size if chunk_size is not None else settings.default_chunk_size
    overlap = chunk_overlap if chunk_overlap is not None else settings.default_chunk_overlap
    validate_chunk_config(size, overlap, settings.max_chunk_size)

    if len(data) > settings.max_upload_bytes:
        raise AppError(
            status_code=413,
            code="FILE_TOO_LARGE",
            message=f"File exceeds the limit of {settings.max_upload_bytes} bytes",
        )

    checksum = hashlib.sha256(data).hexdigest()
    existing_id = _find_document_id(session, checksum)
    if existing_id is not None:
        raise _duplicate_error(existing_id)

    safe_filename = PurePath(filename).name
    parsed = parse_document(safe_filename, data)
    chunks = split_text(parsed.text, size, overlap, parsed.pages)

    now = datetime.now(UTC)
    document = Document(
        id=uuid.uuid4(),
        filename=safe_filename,
        file_type=parsed.file_type,
        mime_type=parsed.mime_type,
        title=title or parsed.title,
        checksum=checksum,
        chunk_size=size,
        chunk_overlap=overlap,
        status="ready",
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    document.chunks = [
        Chunk(
            id=uuid.uuid4(),
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            content_hash=hashlib.sha256(chunk.content.encode("utf-8")).hexdigest(),
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
            page_number=chunk.page_number,
            created_at=now,
        )
        for chunk in chunks
    ]

    session.add(document)
    try:
        session.commit()
    except IntegrityError as exc:
        # A concurrent request stored the same checksum between our check and our insert.
        session.rollback()
        existing_id = _find_document_id(session, checksum)
        if existing_id is None:
            raise AppError(500, "PERSISTENCE_ERROR", "Document could not be stored") from exc
        raise _duplicate_error(existing_id) from exc
    return document


def _find_document_id(session: Session, checksum: str) -> uuid.UUID | None:
    return session.scalar(select(Document.id).where(Document.checksum == checksum))


def _duplicate_error(existing_id: uuid.UUID) -> AppError:
    return AppError(
        status_code=409,
        code="DOCUMENT_ALREADY_EXISTS",
        message="A document with this checksum already exists",
        fields={"existing_document_id": str(existing_id)},
    )
