"""Roles table — SQL operations."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import asyncpg

from app.repositories.types import RoleRow


@dataclass(frozen=True)
class RoleByNameInput:
    name: str


@dataclass(frozen=True)
class RoleIdInput:
    role_id: UUID


async def get_role_by_id(conn: asyncpg.Connection, payload: RoleIdInput) -> RoleRow | None:
    row = await conn.fetchrow(
        "SELECT id, name, description FROM roles WHERE id = $1",
        payload.role_id,
    )
    if row is None:
        return None
    return RoleRow(id=row["id"], name=row["name"], description=row["description"])


async def get_role_by_name(conn: asyncpg.Connection, payload: RoleByNameInput) -> RoleRow | None:
    row = await conn.fetchrow(
        "SELECT id, name, description FROM roles WHERE name = $1",
        payload.name,
    )
    if row is None:
        return None
    return RoleRow(id=row["id"], name=row["name"], description=row["description"])


async def is_admin_role(conn: asyncpg.Connection, payload: RoleIdInput) -> bool:
    row = await conn.fetchrow(
        "SELECT 1 AS ok FROM roles WHERE id = $1 AND name = 'admin'",
        payload.role_id,
    )
    return row is not None


async def list_roles(conn: asyncpg.Connection) -> tuple[RoleRow, ...]:
    rows = await conn.fetch("SELECT id, name, description FROM roles ORDER BY name")
    return tuple(RoleRow(id=r["id"], name=r["name"], description=r["description"]) for r in rows)
