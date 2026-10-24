"""Liveness and readiness endpoints. Liveness never touches PostgreSQL."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import Engine

from app.api.deps import get_engine
from app.core.errors import AppError
from app.db.session import check_connection

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def health_ready(engine: Annotated[Engine, Depends(get_engine)]) -> dict[str, str]:
    if not check_connection(engine):
        raise AppError(
            status_code=503,
            code="DATABASE_UNAVAILABLE",
            message="Database is not ready",
        )
    return {"status": "ready", "database": "ok"}
