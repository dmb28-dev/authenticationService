"""Row and payload types for repositories (asyncpg + RORO)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class UserRow:
    id: UUID
    email: str
    password_hash: str
    first_name: str
    last_name: str
    middle_name: str | None
    is_active: bool
    role_id: UUID
    created_at: datetime
    updated_at: datetime
    deactivated_at: datetime | None


@dataclass(frozen=True)
class RoleRow:
    id: UUID
    name: str
    description: str | None


@dataclass(frozen=True)
class AuthSessionRow:
    id: UUID
    user_id: UUID
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    revocation_reason: str | None


@dataclass(frozen=True)
class SessionWithUserRow:
    session_id: UUID
    user_id: UUID
    session_expires_at: datetime
    session_revoked_at: datetime | None
    email: str
    role_id: UUID
    role_name: str
    is_active: bool


@dataclass(frozen=True)
class RefreshTokenRow:
    id: UUID
    session_id: UUID
    token_hash: str
    expires_at: datetime
    rotated_at: datetime | None
    revoked_at: datetime | None
    replaced_by_id: UUID | None


@dataclass(frozen=True)
class RefreshTokenPairRow:
    old_token_id: UUID
    new_refresh: RefreshTokenRow


@dataclass(frozen=True)
class AccessRuleRow:
    id: UUID
    role_id: UUID
    business_element_id: UUID
    read_permission: bool
    read_all_permission: bool
    create_permission: bool
    update_permission: bool
    update_all_permission: bool
    delete_permission: bool
    delete_all_permission: bool
    version: int
    updated_at: datetime


@dataclass(frozen=True)
class AccessRuleMatrixRow:
    role_name: str
    business_element_code: str
    read_permission: bool
    read_all_permission: bool
    create_permission: bool
    update_permission: bool
    update_all_permission: bool
    delete_permission: bool
    delete_all_permission: bool


@dataclass(frozen=True)
class AuditRow:
    id: UUID
    access_role_rule_id: UUID
    changed_by_user_id: UUID
    changed_at: datetime
    change_type: str
    before_snapshot: dict[str, Any] | None
    after_snapshot: dict[str, Any]


@dataclass(frozen=True)
class MockDocumentRow:
    id: UUID
    owner_id: UUID
    title: str
    status: str
    created_at: datetime


@dataclass(frozen=True)
class MockReportRow:
    id: UUID
    owner_id: UUID
    title: str
    summary: str | None
    created_at: datetime


def _user_from_record(r: Any) -> UserRow:
    return UserRow(
        id=r["id"],
        email=r["email"],
        password_hash=r["password_hash"],
        first_name=r["first_name"],
        last_name=r["last_name"],
        middle_name=r["middle_name"],
        is_active=r["is_active"],
        role_id=r["role_id"],
        created_at=r["created_at"],
        updated_at=r["updated_at"],
        deactivated_at=r["deactivated_at"],
    )
