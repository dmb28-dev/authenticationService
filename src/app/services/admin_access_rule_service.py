"""Admin access rules: stubs without DB; matrix + upsert + audit with PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import asyncpg
from asyncpg.exceptions import UniqueViolationError

from app.core.config import AppSettings
from app.core.logging import log_business_event, log_technical
from app.repositories import access_rule_repository, audit_repository, role_repository
from app.repositories.access_rule_repository import (
    AccessRuleByRoleAndCodeInput,
    AccessRuleMatrixQueryInput,
    CreateAccessRuleDbInput,
    MatrixCellRow,
    UpdateAccessRuleDbInput,
)
from app.repositories.audit_repository import CreateAccessRuleAuditInput
from app.repositories.role_repository import RoleIdInput
from app.repositories.types import AccessRuleRow
from app.schemas.access_rule_schemas import (
    AccessRuleItem,
    AccessRuleMatrixOutput,
    AccessRuleOutput,
    BusinessElementRef,
    ListAccessRulesInput,
    MatrixCell,
    PermissionsBlock,
    RoleRef,
    UpsertAccessRuleInput,
)

_R1 = UUID("10000000-0000-4000-8000-000000000001")
_R2 = UUID("20000000-0000-4000-8000-000000000002")
_BE1 = UUID("30000000-0000-4000-8000-000000000003")


class AccessRuleNotFoundError(Exception):
    """Role, business element, or rule row missing."""


class AccessRuleVersionConflictError(Exception):
    """Optimistic lock failure or create when row exists."""


def _iso(dt: datetime) -> str:
    s = dt.astimezone(timezone.utc).isoformat()
    if s.endswith("+00:00"):
        return s[:-6] + "Z"
    return s


def _perm_block_from_row(row: AccessRuleRow) -> PermissionsBlock:
    return PermissionsBlock(
        read=row.read_permission,
        read_all=row.read_all_permission,
        create=row.create_permission,
        update=row.update_permission,
        update_all=row.update_all_permission,
        delete=row.delete_permission,
        delete_all=row.delete_all_permission,
    )


def _snapshot_from_row(row: AccessRuleRow) -> dict:
    return {
        "read": row.read_permission,
        "read_all": row.read_all_permission,
        "create": row.create_permission,
        "update": row.update_permission,
        "update_all": row.update_all_permission,
        "delete": row.delete_permission,
        "delete_all": row.delete_all_permission,
        "version": row.version,
    }


def _access_rule_item(
    row: AccessRuleRow,
    *,
    role_name: str,
    business_element_code: str,
) -> AccessRuleItem:
    return AccessRuleItem(
        id=row.id,
        version=int(row.version),
        role=RoleRef(id=row.role_id, name=role_name),
        business_element=BusinessElementRef(id=row.business_element_id, code=business_element_code),
        permissions=_perm_block_from_row(row),
        updated_at=_iso(row.updated_at),
    )


def _matrix_cell(mc: MatrixCellRow) -> MatrixCell:
    return MatrixCell(
        role=RoleRef(id=mc.role_id, name=mc.role_name),
        business_element=BusinessElementRef(id=mc.business_element_id, code=mc.business_element_code),
        is_configured=mc.is_configured,
        effective_deny_by_default=mc.effective_deny_by_default,
    )


def list_access_rules_stub(payload: ListAccessRulesInput) -> AccessRuleMatrixOutput:
    _ = payload
    item = AccessRuleItem(
        id=_R1,
        version=1,
        role=RoleRef(id=UUID("40000000-0000-4000-8000-000000000004"), name="manager"),
        business_element=BusinessElementRef(id=_BE1, code="documents"),
        permissions=PermissionsBlock(
            read=True,
            read_all=True,
            create=True,
            update=False,
            update_all=True,
            delete=False,
            delete_all=False,
        ),
        updated_at="2026-04-03T10:10:00Z",
    )
    matrix = [
        MatrixCell(
            role=RoleRef(id=_R2, name="user"),
            business_element=BusinessElementRef(
                id=UUID("50000000-0000-4000-8000-000000000005"), code="reports"
            ),
            is_configured=False,
            effective_deny_by_default=True,
        )
    ]
    return AccessRuleMatrixOutput(
        data=[item],
        matrix=matrix,
        meta={"limit": payload.limit, "offset": payload.offset, "total": 1},
    )


async def list_access_rules_db(
    conn: asyncpg.Connection,
    payload: ListAccessRulesInput,
    _settings: AppSettings,
) -> AccessRuleMatrixOutput:
    _ = _settings
    q = AccessRuleMatrixQueryInput(
        role_name=payload.role_name,
        business_element_code=payload.business_element_code,
        limit=payload.limit,
        offset=payload.offset,
    )
    total = await access_rule_repository.count_matrix_cells(conn, q)
    matrix_rows = await access_rule_repository.list_matrix_cells(conn, q)
    configured = await access_rule_repository.list_configured_access_rules(conn, q)
    data_items = [
        _access_rule_item(
            AccessRuleRow(
                id=r.id,
                role_id=r.role_id,
                business_element_id=r.business_element_id,
                read_permission=r.read_permission,
                read_all_permission=r.read_all_permission,
                create_permission=r.create_permission,
                update_permission=r.update_permission,
                update_all_permission=r.update_all_permission,
                delete_permission=r.delete_permission,
                delete_all_permission=r.delete_all_permission,
                version=r.version,
                updated_at=r.updated_at,
            ),
            role_name=r.role_name,
            business_element_code=r.business_element_code,
        )
        for r in configured
    ]
    log_business_event("admin.access_rules.list", admin_user_id=str(payload.admin_user_id))
    return AccessRuleMatrixOutput(
        data=data_items,
        matrix=[_matrix_cell(m) for m in matrix_rows],
        meta={"limit": payload.limit, "offset": payload.offset, "total": total},
    )


def upsert_access_rule_stub(payload: UpsertAccessRuleInput) -> AccessRuleOutput:
    _ = payload.version
    rule = AccessRuleItem(
        id=_R1,
        version=payload.version + 1,
        role=RoleRef(id=payload.role_id, name="manager"),
        business_element=BusinessElementRef(id=_BE1, code=payload.business_element_code),
        permissions=PermissionsBlock(
            read=payload.permissions.read,
            read_all=payload.permissions.read_all,
            create=payload.permissions.create,
            update=payload.permissions.update,
            update_all=payload.permissions.update_all,
            delete=payload.permissions.delete,
            delete_all=payload.permissions.delete_all,
        ),
        updated_at="2026-04-03T10:12:00Z",
    )
    return AccessRuleOutput(rule=rule, created=payload.version == 0)


async def upsert_access_rule_db(
    conn: asyncpg.Connection,
    payload: UpsertAccessRuleInput,
    _settings: AppSettings,
) -> AccessRuleOutput:
    _ = _settings
    role = await role_repository.get_role_by_id(conn, RoleIdInput(role_id=payload.role_id))
    if role is None:
        raise AccessRuleNotFoundError
    be_id = await access_rule_repository.get_business_element_id_by_code(conn, payload.business_element_code)
    if be_id is None:
        raise AccessRuleNotFoundError

    perms = payload.permissions
    create_payload = CreateAccessRuleDbInput(
        role_id=payload.role_id,
        business_element_id=be_id,
        read_permission=perms.read,
        read_all_permission=perms.read_all,
        create_permission=perms.create,
        update_permission=perms.update,
        update_all_permission=perms.update_all,
        delete_permission=perms.delete,
        delete_all_permission=perms.delete_all,
    )

    async with conn.transaction():
        locked = await access_rule_repository.get_rule_for_update(
            conn,
            AccessRuleByRoleAndCodeInput(
                role_id=payload.role_id,
                business_element_code=payload.business_element_code,
            ),
        )

        if payload.version == 0:
            if locked is not None:
                log_technical("admin.access_rules.upsert.conflict", reason="create_when_exists")
                raise AccessRuleVersionConflictError
            try:
                new_row = await access_rule_repository.create_access_rule(conn, create_payload)
            except UniqueViolationError as e:
                log_technical("admin.access_rules.upsert.conflict", reason="unique_violation")
                raise AccessRuleVersionConflictError from e
            await audit_repository.create_access_rule_audit(
                conn,
                CreateAccessRuleAuditInput(
                    access_role_rule_id=new_row.id,
                    changed_by_user_id=payload.admin_user_id,
                    change_type="create",
                    before_snapshot=None,
                    after_snapshot=_snapshot_from_row(new_row),
                ),
            )
            log_business_event(
                "admin.access_rules.upsert",
                admin_user_id=str(payload.admin_user_id),
                rule_id=str(new_row.id),
                created="true",
            )
            return AccessRuleOutput(
                rule=_access_rule_item(
                    new_row,
                    role_name=role.name,
                    business_element_code=payload.business_element_code,
                ),
                created=True,
            )

        if locked is None:
            raise AccessRuleNotFoundError
        if locked.version != payload.version:
            log_technical("admin.access_rules.upsert.version_mismatch", expected=str(payload.version))
            raise AccessRuleVersionConflictError

        upd = UpdateAccessRuleDbInput(
            rule_id=locked.id,
            expected_version=payload.version,
            read_permission=perms.read,
            read_all_permission=perms.read_all,
            create_permission=perms.create,
            update_permission=perms.update,
            update_all_permission=perms.update_all,
            delete_permission=perms.delete,
            delete_all_permission=perms.delete_all,
        )
        before_snap = _snapshot_from_row(locked)
        updated = await access_rule_repository.update_access_rule(conn, upd)
        if updated is None:
            log_technical("admin.access_rules.upsert.version_mismatch", reason="update_no_row")
            raise AccessRuleVersionConflictError
        await audit_repository.create_access_rule_audit(
            conn,
            CreateAccessRuleAuditInput(
                access_role_rule_id=updated.id,
                changed_by_user_id=payload.admin_user_id,
                change_type="update",
                before_snapshot=before_snap,
                after_snapshot=_snapshot_from_row(updated),
            ),
        )
        log_business_event(
            "admin.access_rules.upsert",
            admin_user_id=str(payload.admin_user_id),
            rule_id=str(updated.id),
            created="false",
        )
        return AccessRuleOutput(
            rule=_access_rule_item(
                updated,
                role_name=role.name,
                business_element_code=payload.business_element_code,
            ),
            created=False,
        )
