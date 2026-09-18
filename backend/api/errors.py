"""Canonical public error contract."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.details = details


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def _response(request: Request, error: AppError) -> JSONResponse:
    body: dict[str, Any] = {
        "error": {
            "code": error.code,
            "message": error.message,
            "retryable": error.retryable,
        },
        "request_id": _request_id(request),
    }
    if error.details is not None:
        body["error"]["details"] = error.details
    return JSONResponse(status_code=error.status_code, content=body)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return _response(request, exc)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = {"fields": [".".join(map(str, item["loc"])) for item in exc.errors()]}
        return _response(
            request,
            AppError("validation_error", "Request validation failed", details=details),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, _exc: Exception) -> JSONResponse:
        # Do not log exception text/tracebacks here: drivers may embed credentials or raw values.
        logger.error("Unhandled request error", extra={"request_id": _request_id(request)})
        return _response(
            request,
            AppError(
                "internal_error",
                "An unexpected error occurred",
                status_code=500,
                retryable=True,
            ),
        )
