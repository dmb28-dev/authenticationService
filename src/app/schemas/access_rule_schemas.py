from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PermissionsBlock(BaseModel):
    read: bool = False
    read_all: bool = False
    create: bool = False
    update: bool = False
    update_all: bool = False
    delete: bool = False
    delete_all: bool = False


class RoleRef(BaseModel):
    id: UUID
    name: str


class BusinessElementRef(BaseModel):
    id: UUID
    code: str


class AccessRuleItem(BaseModel):
    id: UUID
    version: int
    role: RoleRef
    business_element: BusinessElementRef
    permissions: PermissionsBlock
    updated_at: str


class MatrixCell(BaseModel):
    role: RoleRef
    business_element: BusinessElementRef
    is_configured: bool
    effective_deny_by_default: bool


class AccessRuleMatrixOutput(BaseModel):
    data: list[AccessRuleItem]
    matrix: list[MatrixCell]
    meta: dict[str, int]


class ListAccessRulesInput(BaseModel):
    admin_user_id: UUID
    role_name: str | None = None
    business_element_code: str | None = None
    limit: int = 50
    offset: int = 0


class UpsertPermissionsBlock(BaseModel):
    """Full permission snapshot required for PUT (no omitted fields)."""

    model_config = ConfigDict(extra="forbid")

    read: bool
    read_all: bool
    create: bool
    update: bool
    update_all: bool
    delete: bool
    delete_all: bool


class UpsertAccessRuleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=0)
    permissions: UpsertPermissionsBlock


class UpsertAccessRuleInput(BaseModel):
    admin_user_id: UUID
    role_id: UUID
    business_element_code: str
    version: int
    permissions: UpsertPermissionsBlock


class AccessRuleOutput(BaseModel):
    rule: AccessRuleItem
    created: bool = False
