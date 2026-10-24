"""HTTP response models for the document endpoints."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

DocumentStatus = Literal["processing", "ready", "failed"]


class DocumentCreated(BaseModel):
    id: uuid.UUID
    filename: str
    file_type: str
    status: DocumentStatus
    chunk_count: int
    created_at: datetime


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    file_type: str
    status: DocumentStatus
    chunk_count: int
    created_at: datetime


class DocumentList(BaseModel):
    items: list[DocumentSummary]
    limit: int
    offset: int
    total: int


class DocumentDetail(BaseModel):
    id: uuid.UUID
    filename: str
    file_type: str
    mime_type: str
    title: str | None
    checksum: str
    status: DocumentStatus
    chunk_size: int
    chunk_overlap: int
    chunk_count: int
    created_at: datetime
    updated_at: datetime
