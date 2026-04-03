from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


class ApiHttpError(Exception):
    """Carries a ready-to-serialize error JSON body and HTTP status."""

    def __init__(self, status_code: int, body: dict[str, Any]) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(body.get("message", "error"))


def build_error_response(
    *,
    error: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    rid = request_id or str(uuid4())
    body: dict[str, Any] = {
        "error": error,
        "message": message,
        "request_id": rid,
    }
    if details:
        body["details"] = details
    return jsonable_encoder(body)


def raise_api_error(
    status_code: int,
    *,
    error: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    request_id: str | None = None,
) -> None:
    raise ApiHttpError(
        status_code,
        build_error_response(
            error=error,
            message=message,
            details=details,
            request_id=request_id,
        ),
    )


def error_json_response(
    status_code: int,
    *,
    error: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=build_error_response(
            error=error,
            message=message,
            details=details,
            request_id=request_id,
        ),
    )
