from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies.auth import get_current_principal
from app.api.dependencies.db_pool import get_optional_db_pool
from app.core.errors import raise_api_error
from app.core.responses import build_success_response
from app.db.pool import DatabasePool
from app.schemas.auth_schemas import AuthenticatedPrincipal
from app.schemas.profile_schemas import CurrentUserInput, ProfileUpdateRequest, UpdateProfileInput
from app.services import profile_service

router = APIRouter()


def _to_current(p: AuthenticatedPrincipal) -> CurrentUserInput:
    return CurrentUserInput(
        user_id=p.user_id,
        session_id=p.session_id,
        role_id=p.role_id,
        role_name=p.role_name,
    )


@router.get("/me")
async def get_me(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    request: Request,
    pool: DatabasePool | None = Depends(get_optional_db_pool),
) -> dict:
    settings = request.app.state.settings
    if pool is None:
        out = profile_service.get_current_profile_stub(_to_current(principal))
        return build_success_response(out.model_dump(mode="json"))

    async with pool.acquire() as conn:
        try:
            out = await profile_service.get_current_profile_db(conn, _to_current(principal), settings)
        except ValueError as e:
            raise_api_error(404, error="not_found", message=str(e))
    return build_success_response(out.model_dump(mode="json"))


@router.patch("/me")
async def patch_me(
    payload: ProfileUpdateRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    request: Request,
    pool: DatabasePool | None = Depends(get_optional_db_pool),
) -> dict:
    settings = request.app.state.settings
    body = UpdateProfileInput(
        user_id=principal.user_id,
        session_id=principal.session_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        middle_name=payload.middle_name,
        email=payload.email,
    )
    if pool is None:
        out = profile_service.update_current_profile_stub(body)
        return build_success_response(out.model_dump(mode="json"))

    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                out = await profile_service.update_current_profile_db(conn, body, settings)
            except profile_service.EmailConflictError:
                raise_api_error(409, error="conflict", message="Email already registered")
            except ValueError as e:
                raise_api_error(422, error="validation_error", message=str(e))
    return build_success_response(out.model_dump(mode="json"))


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    pool: DatabasePool | None = Depends(get_optional_db_pool),
) -> None:
    if pool is None:
        profile_service.soft_delete_current_user_stub(_to_current(principal))
        return

    async with pool.acquire() as conn:
        async with conn.transaction():
            await profile_service.soft_delete_current_user_db(conn, _to_current(principal))
