"""access_rule_audit — SQL operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import asyncpg

from app.repositories.types import AuditRow


@dataclass(frozen=True)
class CreateAuditEntryInput:
    access_role_rule_id: UUID
    changed_by_user_id: UUID
    change_type: str
    before_snapshot: dict[str, Any] | None
    after_snapshot: dict[str, Any]


CreateAccessRuleAuditInput = CreateAuditEntryInput


async def create_audit_entry(conn: asyncpg.Connection, payload: CreateAuditEntryInput) -> AuditRow:
    row = await conn.fetchrow(
        """
        INSERT INTO access_rule_audit (
            access_role_rule_id,
            changed_by_user_id,
            change_type,
            before_snapshot,
            after_snapshot
        )
        VALUES ($1, $2, $3, $4, $5)
        RETURNING
            id, access_role_rule_id, changed_by_user_id, changed_at,
            change_type, before_snapshot, after_snapshot
        """,
        payload.access_role_rule_id,
        payload.changed_by_user_id,
        payload.change_type,
        payload.before_snapshot,
        payload.after_snapshot,
    )
    return AuditRow(
        id=row["id"],
        access_role_rule_id=row["access_role_rule_id"],
        changed_by_user_id=row["changed_by_user_id"],
        changed_at=row["changed_at"],
        change_type=row["change_type"],
        before_snapshot=row["before_snapshot"],
        after_snapshot=row["after_snapshot"],
    )


async def create_access_rule_audit(
    conn: asyncpg.Connection, payload: CreateAccessRuleAuditInput
) -> AuditRow:
    return await create_audit_entry(conn, payload)
