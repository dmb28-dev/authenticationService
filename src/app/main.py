from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.middleware.error_handling import unhandled_error_middleware
from app.api.middleware.request_id import request_id_middleware
from app.api.router import build_api_router
from app.api.routes import health_routes
from app.core.config import AppSettings, load_settings
from app.core.errors import ApiHttpError, build_error_response
from app.core.logging import configure_logging
from app.db.pool import create_db_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = app.state.settings
    configure_logging(level=settings.log_level)
    if settings.database_url:
        app.state.db_pool = await create_db_pool(settings)
    else:
        app.state.db_pool = None
    try:
        yield
    finally:
        pool = getattr(app.state, "db_pool", None)
        if pool is not None:
            await pool.close()


def create_application(
    settings: AppSettings | None = None,
    *,
    dependency_overrides: Mapping[Callable[..., Any], Callable[..., Any]] | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="authenticationService", lifespan=lifespan)
    app.state.settings = settings
    if dependency_overrides:
        for dep, override in dependency_overrides.items():
            app.dependency_overrides[dep] = override

    app.middleware("http")(unhandled_error_middleware)
    app.middleware("http")(request_id_middleware)

    @app.exception_handler(ApiHttpError)
    async def api_http_handler(request: Request, exc: ApiHttpError):
        body = dict(exc.body)
        rid = getattr(request.state, "request_id", None)
        if rid:
            body["request_id"] = rid
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        rid = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=422,
            content=build_error_response(
                error="validation_error",
                message="Request validation failed",
                details=jsonable_encoder(exc.errors()),
                request_id=rid,
            ),
        )

    app.include_router(health_routes.router)
    app.include_router(build_api_router(), prefix="/api/v1")

    return app


app = create_application()
