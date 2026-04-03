"""RBAC: deny-by-default rules from `access_role_rules` (SQL lookup)."""

from __future__ import annotations

from uuid import UUID

import asyncpg

from app.domain import constants as c
from app.repositories import access_rule_repository
from app.repositories.access_rule_repository import AccessRuleByRoleAndCodeInput
from app.repositories.types import AccessRuleRow
from app.schemas.rbac_schemas import (
    AccessDecisionOutput,
    OwnershipCheckInput,
    OwnershipDecisionOutput,
    ResolveAccessInput,
)


def resolve_action_access(payload: ResolveAccessInput) -> AccessDecisionOutput:
    _ = payload
    return AccessDecisionOutput(allow=True, requires_ownership_check=True, scope_all=False)


def _decision_from_rule(rule: AccessRuleRow | None, action: str) -> AccessDecisionOutput:
    if rule is None:
        return AccessDecisionOutput(allow=False, requires_ownership_check=False, scope_all=False)
    if action == c.ACTION_READ:
        allow = rule.read_permission or rule.read_all_permission
        scope_all = rule.read_all_permission
        requires_own = bool(rule.read_permission and not rule.read_all_permission)
        return AccessDecisionOutput(allow=allow, requires_ownership_check=requires_own, scope_all=scope_all)
    if action == c.ACTION_CREATE:
        allow = rule.create_permission
        return AccessDecisionOutput(allow=allow, requires_ownership_check=False, scope_all=False)
    if action == c.ACTION_UPDATE:
        allow = rule.update_permission or rule.update_all_permission
        scope_all = rule.update_all_permission
        requires_own = bool(rule.update_permission and not rule.update_all_permission)
        return AccessDecisionOutput(allow=allow, requires_ownership_check=requires_own, scope_all=scope_all)
    if action == c.ACTION_DELETE:
        allow = rule.delete_permission or rule.delete_all_permission
        scope_all = rule.delete_all_permission
        requires_own = bool(rule.delete_permission and not rule.delete_all_permission)
        return AccessDecisionOutput(allow=allow, requires_ownership_check=requires_own, scope_all=scope_all)
    return AccessDecisionOutput(allow=False, requires_ownership_check=False, scope_all=False)


async def resolve_action_access_db(
    conn: asyncpg.Connection,
    *,
    role_id: UUID,
    business_element_code: str,
    action: str,
) -> AccessDecisionOutput:
    rule = await access_rule_repository.get_rule_by_role_and_business_element_code(
        conn,
        AccessRuleByRoleAndCodeInput(role_id=role_id, business_element_code=business_element_code),
    )
    return _decision_from_rule(rule, action)


def check_object_ownership(payload: OwnershipCheckInput) -> OwnershipDecisionOutput:
    return OwnershipDecisionOutput(is_owner=payload.current_user_id == payload.object_owner_id)
