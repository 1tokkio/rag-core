"""Liveness and readiness endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import Engine

from app.api.deps import get_engine
from app.db.session import check_connection

router = APIRouter()


@router.get("/health")
def health(engine: Annotated[Engine, Depends(get_engine)]) -> JSONResponse:
    database_ok = check_connection(engine)
    body = {
        "status": "ok" if database_ok else "degraded",
        "database": "ok" if database_ok else "down",
    }
    return JSONResponse(content=body, status_code=200 if database_ok else 503)
