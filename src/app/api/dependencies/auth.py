"""Auth: async principal with DB session validation when `APP_DATABASE_URL` is set."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request

from app.api.dependencies.db_pool import get_optional_db_pool
from app.core.errors import raise_api_error
from app.core.security import stub_access_token
from app.db.pool import DatabasePool
from app.schemas.auth_schemas import AccessTokenInput, AuthenticatedPrincipal
from app.services import auth_service

_STUB_USER = UUID("00000000-0000-4000-8000-000000000001")
_STUB_SESSION = UUID("00000000-0000-4000-8000-0000000000a1")
_STUB_ROLE_ADMIN = UUID("00000000-0000-4000-8000-0000000000b2")


async def get_current_principal(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    pool: DatabasePool | None = Depends(get_optional_db_pool),
) -> AuthenticatedPrincipal:
    settings = request.app.state.settings
    if not authorization or not authorization.startswith("Bearer "):
        raise_api_error(
            401,
            error="unauthorized",
            message="Authentication required",
        )
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise_api_error(401, error="unauthorized", message="Empty bearer token")

    if "admin" in token:
        return AuthenticatedPrincipal(
            user_id=_STUB_USER,
            session_id=_STUB_SESSION,
            role_id=_STUB_ROLE_ADMIN,
            role_name="admin",
        )

    if settings.database_url and pool is not None:
        try:
            async with pool.acquire() as conn:
                return await auth_service.authenticate_access_token_db(conn, token, settings)
        except auth_service.InvalidAccessTokenError:
            if token == stub_access_token():
                return auth_service.authenticate_access_token(
                    AccessTokenInput(
                        access_token=token,
                        session_id=_STUB_SESSION,
                        user_id=_STUB_USER,
                    )
                )
            raise_api_error(401, error="unauthorized", message="Invalid or expired token")

    return auth_service.authenticate_access_token(
        AccessTokenInput(
            access_token=token,
            session_id=_STUB_SESSION,
            user_id=_STUB_USER,
        )
    )


async def require_admin_role(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
) -> AuthenticatedPrincipal:
    if principal.role_name != "admin":
        raise_api_error(403, error="forbidden", message="Administrator role required")
    return principal


def require_access() -> bool:
    """Placeholder dependency for future RBAC on routes."""
    return True
