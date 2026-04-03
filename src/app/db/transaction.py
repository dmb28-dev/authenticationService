from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg

from app.db.pool import DatabasePool


@asynccontextmanager
async def transaction(pool: DatabasePool) -> AsyncIterator[asyncpg.Connection]:
    async with pool.acquire() as conn:
        async with conn.transaction():
            yield conn
