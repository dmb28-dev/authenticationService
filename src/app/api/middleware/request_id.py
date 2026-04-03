"""Assign and propagate request correlation id."""

from __future__ import annotations

from uuid import uuid4

from starlette.requests import Request
from starlette.responses import Response


async def request_id_middleware(request: Request, call_next) -> Response:
    settings = request.app.state.settings
    header_name = settings.request_id_header_name
    incoming = request.headers.get(header_name)
    request_id = incoming or str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers[header_name] = request_id
    return response
