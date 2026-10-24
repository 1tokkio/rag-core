"""Document ingestion and inspection endpoints under /api/v1/documents."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Query, UploadFile
from sqlalchemy import func, select

from app.api.deps import SessionDep, SettingsDep
from app.api.schemas import DocumentCreated, DocumentDetail, DocumentList, DocumentSummary
from app.core.errors import AppError
from app.db.models import Chunk, Document
from app.ingestion.service import ingest_document

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("", status_code=201, response_model=DocumentCreated)
def create_document(
    session: SessionDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File()],
    chunk_size: Annotated[int | None, Form()] = None,
    chunk_overlap: Annotated[int | None, Form()] = None,
    title: Annotated[str | None, Form(max_length=255)] = None,
) -> DocumentCreated:
    # Read one byte past the limit so an oversized upload is detected without loading it all.
    data = file.file.read(settings.max_upload_bytes + 1)
    document = ingest_document(
        session,
        settings=settings,
        filename=file.filename or "",
        data=data,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        title=title,
    )
    return DocumentCreated(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        status=document.status,
        chunk_count=len(document.chunks),
        created_at=document.created_at,
    )


@router.get("", response_model=DocumentList)
def list_documents(
    session: SessionDep,
    status: Literal["processing", "ready", "failed"] | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentList:
    chunk_counts = (
        select(Chunk.document_id, func.count(Chunk.id).label("chunk_count"))
        .group_by(Chunk.document_id)
        .subquery()
    )
    query = select(Document, func.coalesce(chunk_counts.c.chunk_count, 0)).outerjoin(
        chunk_counts, chunk_counts.c.document_id == Document.id
    )
    count_query = select(func.count()).select_from(Document)
    if status is not None:
        query = query.where(Document.status == status)
        count_query = count_query.where(Document.status == status)

    rows = session.execute(
        query.order_by(Document.created_at.desc(), Document.id).limit(limit).offset(offset)
    ).all()
    items = [
        DocumentSummary(
            id=document.id,
            filename=document.filename,
            file_type=document.file_type,
            status=document.status,
            chunk_count=chunk_count,
            created_at=document.created_at,
        )
        for document, chunk_count in rows
    ]
    return DocumentList(
        items=items,
        limit=limit,
        offset=offset,
        total=session.scalar(count_query) or 0,
    )


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: uuid.UUID, session: SessionDep) -> DocumentDetail:
    document = session.get(Document, document_id)
    if document is None:
        raise AppError(404, "DOCUMENT_NOT_FOUND", "Document does not exist")
    chunk_count = session.scalar(
        select(func.count(Chunk.id)).where(Chunk.document_id == document.id)
    )
    return DocumentDetail(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        mime_type=document.mime_type,
        title=document.title,
        checksum=document.checksum,
        status=document.status,
        chunk_size=document.chunk_size,
        chunk_overlap=document.chunk_overlap,
        chunk_count=chunk_count or 0,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
