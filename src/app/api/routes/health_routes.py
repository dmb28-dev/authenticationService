"""Liveness, readiness, and metrics."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.observability import check_database_ready, snapshot

router = APIRouter(tags=["health"])


@router.get("/health")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def readiness(request: Request) -> JSONResponse:
    settings = request.app.state.settings
    pool = getattr(request.app.state, "db_pool", None)
    ok, reason = await check_database_ready(
        pool,
        timeout_ms=settings.readiness_query_timeout_ms,
    )
    if ok:
        return JSONResponse(status_code=200, content={"status": "ready"})
    body: dict[str, str | None] = {"status": "not_ready", "reason": reason}
    return JSONResponse(status_code=503, content=body)


@router.get("/metrics")
def metrics(request: Request) -> JSONResponse:
    settings = request.app.state.settings
    if not settings.metrics_enabled:
        return JSONResponse(status_code=404, content={"error": "not_found", "message": "Metrics disabled"})
    return JSONResponse(status_code=200, content=snapshot())
