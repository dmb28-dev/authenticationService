from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ResolveAccessInput(BaseModel):
    role_id: UUID
    business_element_code: str = Field(min_length=1)
    action: str = Field(min_length=1)


class AccessDecisionOutput(BaseModel):
    allow: bool
    requires_ownership_check: bool
    scope_all: bool = False


class OwnershipCheckInput(BaseModel):
    current_user_id: UUID
    object_owner_id: UUID


class OwnershipDecisionOutput(BaseModel):
    is_owner: bool
