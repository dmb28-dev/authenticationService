from __future__ import annotations

import asyncpg

from app.core.config import AppSettings

DatabasePool = asyncpg.Pool


async def create_db_pool(settings: AppSettings) -> DatabasePool:
    if not settings.database_url:
        msg = "database_url is not configured"
        raise ValueError(msg)
    return await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=settings.database_pool_min_size,
        max_size=settings.database_pool_max_size,
    )
