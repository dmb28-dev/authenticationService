"""Optional PostgreSQL pool (missing when `APP_DATABASE_URL` is empty)."""

from __future__ import annotations

from fastapi import Request

from app.db.pool import DatabasePool


def get_optional_db_pool(request: Request) -> DatabasePool | None:
    return getattr(request.app.state, "db_pool", None)
