"""access_role_rules — SQL-first matrix and admin CRUD."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

from app.repositories.types import AccessRuleMatrixRow, AccessRuleRow


@dataclass(frozen=True)
class AccessRuleLookupInput:
    role_id: UUID
    business_element_id: UUID


@dataclass(frozen=True)
class AccessRuleByRoleAndCodeInput:
    role_id: UUID
    business_element_code: str


@dataclass(frozen=True)
class AccessRuleMatrixQueryInput:
    role_name: str | None
    business_element_code: str | None
    limit: int
    offset: int


@dataclass(frozen=True)
class ConfiguredAccessRuleRow:
    id: UUID
    version: int
    updated_at: datetime
    role_id: UUID
    role_name: str
    business_element_id: UUID
    business_element_code: str
    read_permission: bool
    read_all_permission: bool
    create_permission: bool
    update_permission: bool
    update_all_permission: bool
    delete_permission: bool
    delete_all_permission: bool


@dataclass(frozen=True)
class MatrixCellRow:
    role_id: UUID
    role_name: str
    business_element_id: UUID
    business_element_code: str
    rule_id: UUID | None
    read_permission: bool
    read_all_permission: bool
    create_permission: bool
    update_permission: bool
    update_all_permission: bool
    delete_permission: bool
    delete_all_permission: bool
    is_configured: bool
    effective_deny_by_default: bool


@dataclass(frozen=True)
class CreateAccessRuleDbInput:
    role_id: UUID
    business_element_id: UUID
    read_permission: bool
    read_all_permission: bool
    create_permission: bool
    update_permission: bool
    update_all_permission: bool
    delete_permission: bool
    delete_all_permission: bool


@dataclass(frozen=True)
class UpdateAccessRuleDbInput:
    rule_id: UUID
    expected_version: int
    read_permission: bool
    read_all_permission: bool
    create_permission: bool
    update_permission: bool
    update_all_permission: bool
    delete_permission: bool
    delete_all_permission: bool


@dataclass(frozen=True)
class UpsertAccessRuleDbInput:
    role_id: UUID
    business_element_id: UUID
    read_permission: bool
    read_all_permission: bool
    create_permission: bool
    update_permission: bool
    update_all_permission: bool
    delete_permission: bool
    delete_all_permission: bool


def _access_rule_row_from_record(row: asyncpg.Record) -> AccessRuleRow:
    return AccessRuleRow(
        id=row["id"],
        role_id=row["role_id"],
        business_element_id=row["business_element_id"],
        read_permission=row["read_permission"],
        read_all_permission=row["read_all_permission"],
        create_permission=row["create_permission"],
        update_permission=row["update_permission"],
        update_all_permission=row["update_all_permission"],
        delete_permission=row["delete_permission"],
        delete_all_permission=row["delete_all_permission"],
        version=row["version"],
        updated_at=row["updated_at"],
    )


async def get_business_element_id_by_code(conn: asyncpg.Connection, code: str) -> UUID | None:
    row = await conn.fetchrow("SELECT id FROM business_elements WHERE code = $1", code)
    return None if row is None else row["id"]


async def get_rule_by_role_and_business_element_code(
    conn: asyncpg.Connection, payload: AccessRuleByRoleAndCodeInput
) -> AccessRuleRow | None:
    row = await conn.fetchrow(
        """
        SELECT
            arr.id,
            arr.role_id,
            arr.business_element_id,
            arr.read_permission,
            arr.read_all_permission,
            arr.create_permission,
            arr.update_permission,
            arr.update_all_permission,
            arr.delete_permission,
            arr.delete_all_permission,
            arr.version,
            arr.updated_at
        FROM access_role_rules arr
        JOIN business_elements be ON be.id = arr.business_element_id
        WHERE arr.role_id = $1 AND be.code = $2
        """,
        payload.role_id,
        payload.business_element_code,
    )
    if row is None:
        return None
    return _access_rule_row_from_record(row)


async def get_rule_by_role_and_element(
    conn: asyncpg.Connection, payload: AccessRuleLookupInput
) -> AccessRuleRow | None:
    row = await conn.fetchrow(
        """
        SELECT
            id, role_id, business_element_id,
            read_permission, read_all_permission, create_permission,
            update_permission, update_all_permission, delete_permission, delete_all_permission,
            version, updated_at
        FROM access_role_rules
        WHERE role_id = $1 AND business_element_id = $2
        """,
        payload.role_id,
        payload.business_element_id,
    )
    if row is None:
        return None
    return _access_rule_row_from_record(row)


async def get_rule_for_update(
    conn: asyncpg.Connection, payload: AccessRuleByRoleAndCodeInput
) -> AccessRuleRow | None:
    row = await conn.fetchrow(
        """
        SELECT
            arr.id,
            arr.role_id,
            arr.business_element_id,
            arr.read_permission,
            arr.read_all_permission,
            arr.create_permission,
            arr.update_permission,
            arr.update_all_permission,
            arr.delete_permission,
            arr.delete_all_permission,
            arr.version,
            arr.updated_at
        FROM access_role_rules arr
        INNER JOIN business_elements be ON be.id = arr.business_element_id
        WHERE arr.role_id = $1 AND be.code = $2
        FOR UPDATE OF arr
        """,
        payload.role_id,
        payload.business_element_code,
    )
    if row is None:
        return None
    return _access_rule_row_from_record(row)


async def count_matrix_cells(
    conn: asyncpg.Connection, payload: AccessRuleMatrixQueryInput
) -> int:
    val = await conn.fetchval(
        """
        SELECT COUNT(*)::bigint
        FROM roles r
        CROSS JOIN business_elements be
        LEFT JOIN access_role_rules arr
          ON arr.role_id = r.id AND arr.business_element_id = be.id
        WHERE ($1::text IS NULL OR r.name = $1)
          AND ($2::text IS NULL OR be.code = $2)
        """,
        payload.role_name,
        payload.business_element_code,
    )
    return int(val or 0)


async def list_matrix_cells(
    conn: asyncpg.Connection, payload: AccessRuleMatrixQueryInput
) -> tuple[MatrixCellRow, ...]:
    rows = await conn.fetch(
        """
        SELECT
            r.id AS role_id,
            r.name AS role_name,
            be.id AS business_element_id,
            be.code AS business_element_code,
            arr.id AS rule_id,
            COALESCE(arr.read_permission, FALSE) AS read_permission,
            COALESCE(arr.read_all_permission, FALSE) AS read_all_permission,
            COALESCE(arr.create_permission, FALSE) AS create_permission,
            COALESCE(arr.update_permission, FALSE) AS update_permission,
            COALESCE(arr.update_all_permission, FALSE) AS update_all_permission,
            COALESCE(arr.delete_permission, FALSE) AS delete_permission,
            COALESCE(arr.delete_all_permission, FALSE) AS delete_all_permission,
            (arr.id IS NOT NULL) AS is_configured,
            (
                arr.id IS NULL
                OR NOT (
                    COALESCE(arr.read_permission, FALSE)
                    OR COALESCE(arr.read_all_permission, FALSE)
                    OR COALESCE(arr.create_permission, FALSE)
                    OR COALESCE(arr.update_permission, FALSE)
                    OR COALESCE(arr.update_all_permission, FALSE)
                    OR COALESCE(arr.delete_permission, FALSE)
                    OR COALESCE(arr.delete_all_permission, FALSE)
                )
            ) AS effective_deny_by_default
        FROM roles r
        CROSS JOIN business_elements be
        LEFT JOIN access_role_rules arr
          ON arr.role_id = r.id AND arr.business_element_id = be.id
        WHERE ($1::text IS NULL OR r.name = $1)
          AND ($2::text IS NULL OR be.code = $2)
        ORDER BY r.name, be.code
        LIMIT $3 OFFSET $4
        """,
        payload.role_name,
        payload.business_element_code,
        payload.limit,
        payload.offset,
    )
    return tuple(
        MatrixCellRow(
            role_id=r["role_id"],
            role_name=r["role_name"],
            business_element_id=r["business_element_id"],
            business_element_code=r["business_element_code"],
            rule_id=r["rule_id"],
            read_permission=r["read_permission"],
            read_all_permission=r["read_all_permission"],
            create_permission=r["create_permission"],
            update_permission=r["update_permission"],
            update_all_permission=r["update_all_permission"],
            delete_permission=r["delete_permission"],
            delete_all_permission=r["delete_all_permission"],
            is_configured=r["is_configured"],
            effective_deny_by_default=r["effective_deny_by_default"],
        )
        for r in rows
    )


async def count_configured_rules(
    conn: asyncpg.Connection, payload: AccessRuleMatrixQueryInput
) -> int:
    val = await conn.fetchval(
        """
        SELECT COUNT(*)::bigint
        FROM access_role_rules arr
        JOIN roles r ON r.id = arr.role_id
        JOIN business_elements be ON be.id = arr.business_element_id
        WHERE ($1::text IS NULL OR r.name = $1)
          AND ($2::text IS NULL OR be.code = $2)
        """,
        payload.role_name,
        payload.business_element_code,
    )
    return int(val or 0)


async def list_configured_access_rules(
    conn: asyncpg.Connection, payload: AccessRuleMatrixQueryInput
) -> tuple[ConfiguredAccessRuleRow, ...]:
    rows = await conn.fetch(
        """
        SELECT
            arr.id,
            arr.version,
            arr.updated_at,
            r.id AS role_id,
            r.name AS role_name,
            be.id AS business_element_id,
            be.code AS business_element_code,
            arr.read_permission,
            arr.read_all_permission,
            arr.create_permission,
            arr.update_permission,
            arr.update_all_permission,
            arr.delete_permission,
            arr.delete_all_permission
        FROM access_role_rules arr
        JOIN roles r ON r.id = arr.role_id
        JOIN business_elements be ON be.id = arr.business_element_id
        WHERE ($1::text IS NULL OR r.name = $1)
          AND ($2::text IS NULL OR be.code = $2)
        ORDER BY r.name, be.code
        LIMIT $3 OFFSET $4
        """,
        payload.role_name,
        payload.business_element_code,
        payload.limit,
        payload.offset,
    )
    return tuple(
        ConfiguredAccessRuleRow(
            id=r["id"],
            version=r["version"],
            updated_at=r["updated_at"],
            role_id=r["role_id"],
            role_name=r["role_name"],
            business_element_id=r["business_element_id"],
            business_element_code=r["business_element_code"],
            read_permission=r["read_permission"],
            read_all_permission=r["read_all_permission"],
            create_permission=r["create_permission"],
            update_permission=r["update_permission"],
            update_all_permission=r["update_all_permission"],
            delete_permission=r["delete_permission"],
            delete_all_permission=r["delete_all_permission"],
        )
        for r in rows
    )


async def create_access_rule(
    conn: asyncpg.Connection, payload: CreateAccessRuleDbInput
) -> AccessRuleRow:
    row = await conn.fetchrow(
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
            delete_all_permission,
            version
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 1)
        RETURNING
            id, role_id, business_element_id,
            read_permission, read_all_permission, create_permission,
            update_permission, update_all_permission, delete_permission, delete_all_permission,
            version, updated_at
        """,
        payload.role_id,
        payload.business_element_id,
        payload.read_permission,
        payload.read_all_permission,
        payload.create_permission,
        payload.update_permission,
        payload.update_all_permission,
        payload.delete_permission,
        payload.delete_all_permission,
    )
    return _access_rule_row_from_record(row)


async def update_access_rule(
    conn: asyncpg.Connection, payload: UpdateAccessRuleDbInput
) -> AccessRuleRow | None:
    row = await conn.fetchrow(
        """
        UPDATE access_role_rules
        SET
            read_permission = $3,
            read_all_permission = $4,
            create_permission = $5,
            update_permission = $6,
            update_all_permission = $7,
            delete_permission = $8,
            delete_all_permission = $9,
            version = version + 1,
            updated_at = NOW()
        WHERE id = $1 AND version = $2
        RETURNING
            id, role_id, business_element_id,
            read_permission, read_all_permission, create_permission,
            update_permission, update_all_permission, delete_permission, delete_all_permission,
            version, updated_at
        """,
        payload.rule_id,
        payload.expected_version,
        payload.read_permission,
        payload.read_all_permission,
        payload.create_permission,
        payload.update_permission,
        payload.update_all_permission,
        payload.delete_permission,
        payload.delete_all_permission,
    )
    return None if row is None else _access_rule_row_from_record(row)


async def upsert_rule(conn: asyncpg.Connection, payload: UpsertAccessRuleDbInput) -> AccessRuleRow:
    row = await conn.fetchrow(
        """
        INSERT INTO access_role_rules (
            role_id, business_element_id,
            read_permission, read_all_permission, create_permission,
            update_permission, update_all_permission, delete_permission, delete_all_permission
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
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
        RETURNING
            id, role_id, business_element_id,
            read_permission, read_all_permission, create_permission,
            update_permission, update_all_permission, delete_permission, delete_all_permission,
            version, updated_at
        """,
        payload.role_id,
        payload.business_element_id,
        payload.read_permission,
        payload.read_all_permission,
        payload.create_permission,
        payload.update_permission,
        payload.update_all_permission,
        payload.delete_permission,
        payload.delete_all_permission,
    )
    return _access_rule_row_from_record(row)


async def list_rule_matrix(
    conn: asyncpg.Connection, payload: AccessRuleMatrixQueryInput
) -> tuple[AccessRuleMatrixRow, ...]:
    """Backward-compatible matrix rows without pagination metadata (uses same filter SQL)."""
    rows = await conn.fetch(
        """
        SELECT
            r.name AS role_name,
            be.code AS business_element_code,
            COALESCE(arr.read_permission, FALSE) AS read_permission,
            COALESCE(arr.read_all_permission, FALSE) AS read_all_permission,
            COALESCE(arr.create_permission, FALSE) AS create_permission,
            COALESCE(arr.update_permission, FALSE) AS update_permission,
            COALESCE(arr.update_all_permission, FALSE) AS update_all_permission,
            COALESCE(arr.delete_permission, FALSE) AS delete_permission,
            COALESCE(arr.delete_all_permission, FALSE) AS delete_all_permission
        FROM roles r
        CROSS JOIN business_elements be
        LEFT JOIN access_role_rules arr
          ON arr.role_id = r.id AND arr.business_element_id = be.id
        WHERE ($1::text IS NULL OR r.name = $1)
          AND ($2::text IS NULL OR be.code = $2)
        ORDER BY r.name, be.code
        LIMIT $3 OFFSET $4
        """,
        payload.role_name,
        payload.business_element_code,
        payload.limit,
        payload.offset,
    )
    return tuple(
        AccessRuleMatrixRow(
            role_name=r["role_name"],
            business_element_code=r["business_element_code"],
            read_permission=r["read_permission"],
            read_all_permission=r["read_all_permission"],
            create_permission=r["create_permission"],
            update_permission=r["update_permission"],
            update_all_permission=r["update_all_permission"],
            delete_permission=r["delete_permission"],
            delete_all_permission=r["delete_all_permission"],
        )
        for r in rows
    )
