"""RBAC dependency for mock document/report routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.api.dependencies.auth import get_current_principal
from app.api.dependencies.db_pool import get_optional_db_pool
from app.core.errors import raise_api_error
from app.db.pool import DatabasePool
from app.schemas.auth_schemas import AuthenticatedPrincipal
from app.services import access_service


class RequireMockAccess:
    def __init__(self, business_element_code: str, action: str) -> None:
        self.business_element_code = business_element_code
        self.action = action

    async def __call__(
        self,
        request: Request,
        principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
        pool: DatabasePool | None = Depends(get_optional_db_pool),
    ) -> AuthenticatedPrincipal:
        _ = request
        if pool is None:
            return principal
        async with pool.acquire() as conn:
            decision = await access_service.resolve_action_access_db(
                conn,
                role_id=principal.role_id,
                business_element_code=self.business_element_code,
                action=self.action,
            )
        if not decision.allow:
            raise_api_error(403, error="forbidden", message="Access denied")
        return principal
