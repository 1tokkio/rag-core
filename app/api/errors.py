"""Maps application and validation errors to the public error envelope in docs/API.md."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import AppError


def error_body(code: str, message: str, fields: dict[str, Any]) -> dict[str, Any]:
    return {"detail": {"code": code, "message": message, "fields": fields}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, exc.fields),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Only location and message are exposed; raw input values are never echoed back.
        fields = {".".join(str(part) for part in err["loc"]): err["msg"] for err in exc.errors()}
        return JSONResponse(
            status_code=400,
            content=error_body("VALIDATION_ERROR", "Invalid request", fields),
        )
