from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies.auth import get_current_principal
from app.api.dependencies.db_pool import get_optional_db_pool
from app.core.errors import raise_api_error
from app.core.observability import (
    auth_login_failure,
    auth_login_success,
    auth_logout,
    auth_refresh_failure,
    auth_refresh_reuse,
    auth_refresh_success,
    record_route_latency,
)
from app.core.responses import build_success_response
from app.db.pool import DatabasePool
from app.schemas.auth_schemas import (
    AuthenticatedPrincipal,
    LoginInput,
    LogoutInput,
    RefreshInput,
    RegisterUserInput,
)
from app.services import auth_service

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_endpoint(
    payload: RegisterUserInput,
    request: Request,
    pool: DatabasePool | None = Depends(get_optional_db_pool),
) -> dict:
    settings = request.app.state.settings
    if pool is None:
        try:
            out = auth_service.register_user_stub(payload)
        except ValueError as e:
            raise_api_error(422, error="validation_error", message=str(e))
        return build_success_response(out.model_dump(mode="json"))

    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                out = await auth_service.register_user_db(conn, payload, settings)
            except auth_service.EmailConflictError:
                raise_api_error(409, error="conflict", message="Email already registered")
            except ValueError as e:
                raise_api_error(422, error="validation_error", message=str(e))
    return build_success_response(out.model_dump(mode="json"))


@router.post("/login")
async def login_endpoint(
    payload: LoginInput,
    request: Request,
    pool: DatabasePool | None = Depends(get_optional_db_pool),
) -> dict:
    t0 = time.perf_counter()
    settings = request.app.state.settings
    try:
        if pool is None:
            try:
                out = auth_service.login_user_stub(payload)
            except auth_service.InvalidCredentialsError:
                auth_login_failure()
                raise_api_error(401, error="unauthorized", message="Invalid credentials")
            auth_login_success()
        else:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    try:
                        out = await auth_service.login_user_db(conn, payload, settings)
                    except auth_service.InvalidCredentialsError:
                        auth_login_failure()
                        raise_api_error(401, error="unauthorized", message="Invalid credentials")
            auth_login_success()
    finally:
        record_route_latency("auth_login", time.perf_counter() - t0)
    return build_success_response(
        {
            "access_token": out.access_token,
            "refresh_token": out.refresh_token,
            "access_token_expires_in": out.access_token_expires_in,
            "refresh_token_expires_in": out.refresh_token_expires_in,
            "session_id": str(out.session_id),
            "user": out.user.model_dump(mode="json"),
        }
    )


@router.post("/refresh")
async def refresh_endpoint(
    payload: RefreshInput,
    request: Request,
    pool: DatabasePool | None = Depends(get_optional_db_pool),
) -> dict:
    t0 = time.perf_counter()
    settings = request.app.state.settings
    try:
        if pool is None:
            out = auth_service.refresh_access_token_stub(payload)
            auth_refresh_success()
        else:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    try:
                        out = await auth_service.refresh_access_token_db(conn, payload, settings)
                    except auth_service.InvalidAccessTokenError:
                        auth_refresh_failure()
                        raise_api_error(401, error="unauthorized", message="Invalid or expired refresh token")
                    except auth_service.RefreshTokenReuseError:
                        auth_refresh_reuse()
                        raise_api_error(401, error="unauthorized", message="Refresh token reuse detected")
            auth_refresh_success()
    finally:
        record_route_latency("auth_refresh", time.perf_counter() - t0)
    return build_success_response(
        {
            "access_token": out.access_token,
            "refresh_token": out.refresh_token,
            "access_token_expires_in": out.access_token_expires_in,
            "refresh_token_expires_in": out.refresh_token_expires_in,
            "session_id": str(out.session_id),
        }
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_endpoint(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    request: Request,
    pool: DatabasePool | None = Depends(get_optional_db_pool),
) -> None:
    t0 = time.perf_counter()
    try:
        if pool is None:
            auth_service.logout_session_stub(
                LogoutInput(
                    access_token="",
                    session_id=principal.session_id,
                    user_id=principal.user_id,
                )
            )
        else:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    await auth_service.logout_session_db(conn, principal.session_id)
        auth_logout()
    finally:
        record_route_latency("auth_logout", time.perf_counter() - t0)
