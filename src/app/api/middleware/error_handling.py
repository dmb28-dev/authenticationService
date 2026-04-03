"""Map unexpected exceptions to unified error envelope."""

from __future__ import annotations

import traceback

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.errors import ApiHttpError, build_error_response
from app.core.logging import log_technical


async def unhandled_error_middleware(request: Request, call_next) -> Response:
    try:
        return await call_next(request)
    except ApiHttpError:
        raise
    except Exception as e:
        settings = request.app.state.settings
        log_technical(
            "unhandled_exception",
            exc_type=type(e).__name__,
            detail=str(e),
            path=str(request.url.path),
        )
        if settings.env == "development":
            log_technical("unhandled_traceback", traceback=traceback.format_exc())
        rid = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=500,
            content=build_error_response(
                error="internal_error",
                message="Internal server error",
                request_id=rid,
            ),
        )
