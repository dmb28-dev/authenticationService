"""mock_reports — SQL operations (own/all predicates in SQL)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import asyncpg

from app.repositories.types import MockReportRow


@dataclass(frozen=True)
class ListReportsForOwnerInput:
    owner_id: UUID


@dataclass(frozen=True)
class ListReportsAccessInput:
    current_user_id: UUID
    can_read_all: bool
    limit: int
    offset: int


@dataclass(frozen=True)
class GetReportByIdInput:
    report_id: UUID


def _row(r: asyncpg.Record) -> MockReportRow:
    return MockReportRow(
        id=r["id"],
        owner_id=r["owner_id"],
        title=r["title"],
        summary=r["summary"],
        created_at=r["created_at"],
    )


async def list_reports_for_owner(
    conn: asyncpg.Connection, payload: ListReportsForOwnerInput
) -> tuple[MockReportRow, ...]:
    rows = await conn.fetch(
        """
        SELECT id, owner_id, title, summary, created_at
        FROM mock_reports
        WHERE owner_id = $1
        ORDER BY created_at DESC
        """,
        payload.owner_id,
    )
    return tuple(_row(r) for r in rows)


async def list_reports_with_access(
    conn: asyncpg.Connection, payload: ListReportsAccessInput
) -> tuple[tuple[MockReportRow, ...], int]:
    total = await conn.fetchval(
        """
        SELECT COUNT(*)::bigint
        FROM mock_reports
        WHERE ($1::bool OR owner_id = $2)
        """,
        payload.can_read_all,
        payload.current_user_id,
    )
    rows = await conn.fetch(
        """
        SELECT id, owner_id, title, summary, created_at
        FROM mock_reports
        WHERE ($1::bool OR owner_id = $2)
        ORDER BY created_at DESC
        LIMIT $3 OFFSET $4
        """,
        payload.can_read_all,
        payload.current_user_id,
        payload.limit,
        payload.offset,
    )
    return tuple(_row(r) for r in rows), int(total or 0)


async def get_report_by_id(
    conn: asyncpg.Connection, payload: GetReportByIdInput
) -> MockReportRow | None:
    row = await conn.fetchrow(
        """
        SELECT id, owner_id, title, summary, created_at
        FROM mock_reports
        WHERE id = $1
        """,
        payload.report_id,
    )
    if row is None:
        return None
    return _row(row)
