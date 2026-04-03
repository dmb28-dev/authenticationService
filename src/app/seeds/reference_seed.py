"""Upsert roles, business elements, and access rule matrix."""

from __future__ import annotations

from typing import Any

import asyncpg
from uuid import UUID

from app.domain import constants as c

ROLE_SPECS: tuple[tuple[str, str], ...] = (
    ("admin", "Administrator"),
    ("manager", "Manager"),
    ("user", "Standard user"),
    ("guest", "Guest"),
)

BE_SPECS: tuple[tuple[str, str], ...] = (
    (c.BE_DOCUMENTS, "Documents mock API"),
    (c.BE_REPORTS, "Reports mock API"),
    (c.BE_ACCESS_RULES, "Access rules admin API"),
)


async def _role_id_by_name(conn: asyncpg.Connection, name: str) -> UUID:
    row = await conn.fetchrow("SELECT id FROM roles WHERE name = $1", name)
    if row is None:
        msg = f"role not found: {name}"
        raise RuntimeError(msg)
    return row["id"]


async def _be_id_by_code(conn: asyncpg.Connection, code: str) -> UUID:
    row = await conn.fetchrow("SELECT id FROM business_elements WHERE code = $1", code)
    if row is None:
        msg = f"business element not found: {code}"
        raise RuntimeError(msg)
    return row["id"]


async def run(conn: asyncpg.Connection) -> dict[str, int]:
    roles_n = 0
    for name, description in ROLE_SPECS:
        await conn.execute(
            """
            INSERT INTO roles (name, description)
            VALUES ($1, $2)
            ON CONFLICT (name) DO UPDATE
            SET description = EXCLUDED.description
            """,
            name,
            description,
        )
        roles_n += 1

    be_n = 0
    for code, description in BE_SPECS:
        await conn.execute(
            """
            INSERT INTO business_elements (code, description)
            VALUES ($1, $2)
            ON CONFLICT (code) DO UPDATE
            SET description = EXCLUDED.description
            """,
            code,
            description,
        )
        be_n += 1

    admin = await _role_id_by_name(conn, "admin")
    manager = await _role_id_by_name(conn, "manager")
    user = await _role_id_by_name(conn, "user")
    guest = await _role_id_by_name(conn, "guest")

    be_docs = await _be_id_by_code(conn, c.BE_DOCUMENTS)
    be_reports = await _be_id_by_code(conn, c.BE_REPORTS)
    be_rules = await _be_id_by_code(conn, c.BE_ACCESS_RULES)

    matrix: list[tuple[UUID, UUID, dict[str, Any]]] = [
        (admin, be_docs, _all_true()),
        (admin, be_reports, _all_true()),
        (admin, be_rules, _all_true()),
        (manager, be_docs, _rw_own()),
        (manager, be_reports, _rw_own()),
        (manager, be_rules, _deny_all()),
        (user, be_docs, _read_create_own()),
        (user, be_reports, _read_create_own()),
        (user, be_rules, _deny_all()),
        (guest, be_docs, _read_only()),
        (guest, be_reports, _read_only()),
        (guest, be_rules, _deny_all()),
    ]

    rules_n = 0
    for role_id, be_id, perms in matrix:
        await conn.execute(
            """
            INSERT INTO access_role_rules (
                role_id,
                business_element_id,
                read_permission,
                read_all_permission,
                create_permission,
                update_permission,
                update_all_permission,
                delete_permission,
                delete_all_permission
            )
            VALUES (
                $1, $2,
                $3, $4, $5, $6, $7, $8, $9
            )
            ON CONFLICT (role_id, business_element_id) DO UPDATE SET
                read_permission = EXCLUDED.read_permission,
                read_all_permission = EXCLUDED.read_all_permission,
                create_permission = EXCLUDED.create_permission,
                update_permission = EXCLUDED.update_permission,
                update_all_permission = EXCLUDED.update_all_permission,
                delete_permission = EXCLUDED.delete_permission,
                delete_all_permission = EXCLUDED.delete_all_permission,
                version = access_role_rules.version + 1,
                updated_at = NOW()
            """,
            role_id,
            be_id,
            perms["read"],
            perms["read_all"],
            perms["create"],
            perms["update"],
            perms["update_all"],
            perms["delete"],
            perms["delete_all"],
        )
        rules_n += 1

    return {
        "roles_upserted": roles_n,
        "business_elements_upserted": be_n,
        "access_rules_upserted": rules_n,
    }


def _all_true() -> dict[str, bool]:
    return {
        "read": True,
        "read_all": True,
        "create": True,
        "update": True,
        "update_all": True,
        "delete": True,
        "delete_all": True,
    }


def _deny_all() -> dict[str, bool]:
    return {k: False for k in _all_true()}


def _read_only() -> dict[str, bool]:
    r = _deny_all()
    r["read"] = True
    return r


def _rw_own() -> dict[str, bool]:
    r = _deny_all()
    r["read"] = True
    r["create"] = True
    r["update"] = True
    r["delete"] = True
    return r


def _read_create_own() -> dict[str, bool]:
    r = _deny_all()
    r["read"] = True
    r["create"] = True
    r["update"] = True
    r["delete"] = True
    return r
