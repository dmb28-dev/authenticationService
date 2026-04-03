"""Authentication: stub mode without DB; full session + refresh rotation with PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import asyncpg
import jwt

from app.core.config import AppSettings
from app.core.logging import log_business_event, log_technical
from app.core.security import (
    AccessTokenPayload,
    GenerateRefreshTokenInput,
    HashPasswordInput,
    HashRefreshTokenInput,
    NormalizeEmailInput,
    ParseAccessTokenInput,
    build_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    normalize_email,
    parse_access_token,
    stub_access_token,
    stub_refresh_token,
    verify_password,
)
from app.repositories import refresh_token_repository, role_repository, session_repository, user_repository
from app.repositories.refresh_token_repository import (
    CreateRefreshTokenInput,
    RefreshTokenLookupInput,
    RevokeSessionTokensInput,
    RotateRefreshTokenInput,
)
from app.repositories.role_repository import RoleByNameInput
from app.repositories.session_repository import (
    CreateAuthSessionInput,
    RevokeSessionInput,
    SessionLookupInput,
)
from app.repositories.user_repository import (
    CreateUserInput,
    EmailLookupInput,
    UserByEmailInput,
    UserByIdInput,
)
from app.schemas.auth_schemas import (
    AccessTokenInput,
    AuthenticatedPrincipal,
    LoginInput,
    LoginOutput,
    LogoutInput,
    RefreshInput,
    RefreshOutput,
    RegisterUserInput,
    RoleBrief,
    UserProfileOutput,
)

_STUB_USER_ID = UUID("00000000-0000-4000-8000-000000000001")
_STUB_SESSION_ID = UUID("00000000-0000-4000-8000-0000000000a1")
_STUB_ROLE_ID = UUID("00000000-0000-4000-8000-0000000000b1")


class EmailConflictError(Exception):
    """Business conflict: email is already registered."""


class InvalidCredentialsError(Exception):
    """Invalid login or inactive user."""


class InvalidAccessTokenError(Exception):
    """JWT invalid or session/user not active."""


class RefreshTokenReuseError(Exception):
    """Rotated refresh token reused; session revoked."""


def _profile_output_from_db_row(row: user_repository.UserProfileDbRow) -> UserProfileOutput:
    created = row.created_at.isoformat()
    if created.endswith("+00:00"):
        created = created[:-6] + "Z"
    return UserProfileOutput(
        id=row.id,
        email=row.email,
        first_name=row.first_name,
        last_name=row.last_name,
        middle_name=row.middle_name,
        role=RoleBrief(id=row.role_id, name=row.role_name),
        is_active=row.is_active,
        created_at=created,
    )


def register_user_stub(payload: RegisterUserInput) -> UserProfileOutput:
    if payload.password != payload.password_confirmation:
        msg = "passwords do not match"
        raise ValueError(msg)
    return UserProfileOutput(
        id=_STUB_USER_ID,
        email=str(payload.email).lower().strip(),
        first_name=payload.first_name,
        last_name=payload.last_name,
        middle_name=payload.middle_name,
        role=RoleBrief(id=_STUB_ROLE_ID, name="user"),
        is_active=True,
        created_at="2026-04-03T10:00:00Z",
    )


async def register_user_db(
    conn: asyncpg.Connection,
    payload: RegisterUserInput,
    settings: AppSettings,
) -> UserProfileOutput:
    if payload.password != payload.password_confirmation:
        msg = "passwords do not match"
        raise ValueError(msg)
    norm = normalize_email(NormalizeEmailInput(email=str(payload.email))).email
    if await user_repository.is_email_taken(conn, EmailLookupInput(email=norm)):
        raise EmailConflictError()
    role = await role_repository.get_role_by_name(
        conn, RoleByNameInput(name=settings.default_registration_role_name)
    )
    if role is None:
        msg = "default registration role is not configured"
        raise RuntimeError(msg)
    hashed = hash_password(HashPasswordInput(password=payload.password))
    user = await user_repository.create_user(
        conn,
        CreateUserInput(
            email=norm,
            password_hash=hashed.password_hash,
            first_name=payload.first_name,
            last_name=payload.last_name,
            middle_name=payload.middle_name,
            role_id=role.id,
        ),
    )
    profile = await user_repository.get_user_profile_by_id(conn, UserByIdInput(user_id=user.id))
    if profile is None:
        msg = "user profile not found after insert"
        raise RuntimeError(msg)
    return _profile_output_from_db_row(profile)


def login_user_stub(payload: LoginInput) -> LoginOutput:
    if str(payload.email).lower() == "bad@example.com":
        log_business_event("auth.login.failed", reason="stub_invalid_credentials")
        raise InvalidCredentialsError()
    profile = UserProfileOutput(
        id=_STUB_USER_ID,
        email=str(payload.email).lower(),
        first_name="Stub",
        last_name="User",
        middle_name=None,
        role=RoleBrief(id=_STUB_ROLE_ID, name="user"),
        is_active=True,
        created_at="2026-04-03T10:00:00Z",
    )
    log_business_event("auth.login.success", mode="stub", user_id=str(_STUB_USER_ID))
    return LoginOutput(
        access_token=stub_access_token(),
        refresh_token=stub_refresh_token(),
        access_token_expires_in=900,
        refresh_token_expires_in=2592000,
        session_id=_STUB_SESSION_ID,
        user=profile,
    )


async def login_user_db(
    conn: asyncpg.Connection,
    payload: LoginInput,
    settings: AppSettings,
) -> LoginOutput:
    norm = normalize_email(NormalizeEmailInput(email=str(payload.email))).email
    user = await user_repository.get_user_by_email(conn, UserByEmailInput(email=norm))
    if user is None:
        log_business_event("auth.login.failed", reason="user_not_found")
        raise InvalidCredentialsError()
    if not verify_password(password_hash=user.password_hash, password=payload.password):
        log_business_event("auth.login.failed", reason="invalid_password", user_id=str(user.id))
        raise InvalidCredentialsError()
    if not user.is_active:
        log_business_event("auth.login.failed", reason="inactive_user", user_id=str(user.id))
        raise InvalidCredentialsError()
    profile = await user_repository.get_user_profile_by_id(conn, UserByIdInput(user_id=user.id))
    if profile is None:
        log_business_event("auth.login.failed", reason="profile_missing", user_id=str(user.id))
        raise InvalidCredentialsError()

    try:
        now = datetime.now(timezone.utc)
        session_expires = now + timedelta(seconds=settings.refresh_token_ttl_seconds)
        session = await session_repository.create_auth_session(
            conn,
            CreateAuthSessionInput(user_id=user.id, expires_at=session_expires),
        )
        plain_refresh = generate_refresh_token(GenerateRefreshTokenInput()).token
        r_hash = hash_refresh_token(HashRefreshTokenInput(token=plain_refresh))
        refresh_expires = now + timedelta(seconds=settings.refresh_token_ttl_seconds)
        await refresh_token_repository.create_refresh_token(
            conn,
            CreateRefreshTokenInput(
                session_id=session.id,
                token_hash=r_hash.token_hash,
                expires_at=refresh_expires,
            ),
        )
        access_expires = now + timedelta(seconds=settings.access_token_ttl_seconds)
        access_out = build_access_token(
            AccessTokenPayload(
                user_id=user.id,
                session_id=session.id,
                issued_at=now,
                expires_at=access_expires,
            ),
            settings,
        )
    except Exception as e:
        log_technical("auth.login.session_or_token_failure", exc_type=type(e).__name__)
        raise

    log_business_event("auth.login.success", user_id=str(user.id))
    return LoginOutput(
        access_token=access_out.token,
        refresh_token=plain_refresh,
        access_token_expires_in=settings.access_token_ttl_seconds,
        refresh_token_expires_in=settings.refresh_token_ttl_seconds,
        session_id=session.id,
        user=_profile_output_from_db_row(profile),
    )


def refresh_access_token_stub(payload: RefreshInput) -> RefreshOutput:
    _ = payload.refresh_token
    return RefreshOutput(
        access_token="stub.new.access.jwt",
        refresh_token="stub.new.refresh.token",
        access_token_expires_in=900,
        refresh_token_expires_in=2592000,
        session_id=_STUB_SESSION_ID,
    )


async def refresh_access_token_db(
    conn: asyncpg.Connection,
    payload: RefreshInput,
    settings: AppSettings,
) -> RefreshOutput:
    now = datetime.now(timezone.utc)
    plain = payload.refresh_token.strip()
    r_hash = hash_refresh_token(HashRefreshTokenInput(token=plain))
    row = await refresh_token_repository.get_token_for_update(
        conn, RefreshTokenLookupInput(token_hash=r_hash.token_hash)
    )
    if row is None:
        log_business_event("auth.refresh.failed", reason="token_not_found")
        raise InvalidAccessTokenError()
    if row.rotated_at is not None:
        log_business_event("auth.refresh.reuse_detected")
        await session_repository.revoke_session(
            conn,
            RevokeSessionInput(session_id=row.session_id, revocation_reason="refresh_reuse"),
        )
        await refresh_token_repository.revoke_session_tokens(
            conn, RevokeSessionTokensInput(session_id=row.session_id)
        )
        raise RefreshTokenReuseError()
    if row.revoked_at is not None:
        log_business_event("auth.refresh.failed", reason="revoked")
        raise InvalidAccessTokenError()
    if row.expires_at <= now:
        log_business_event("auth.refresh.failed", reason="expired")
        raise InvalidAccessTokenError()

    active = await session_repository.get_active_session_with_user(
        conn, SessionLookupInput(session_id=row.session_id)
    )
    if active is None:
        log_business_event("auth.refresh.failed", reason="session_inactive")
        raise InvalidAccessTokenError()

    try:
        plain_new = generate_refresh_token(GenerateRefreshTokenInput()).token
        new_hash = hash_refresh_token(HashRefreshTokenInput(token=plain_new))
        new_expires = now + timedelta(seconds=settings.refresh_token_ttl_seconds)
        await refresh_token_repository.rotate_refresh_token(
            conn,
            RotateRefreshTokenInput(
                old_token_id=row.id,
                new_token_hash=new_hash.token_hash,
                new_expires_at=new_expires,
            ),
        )
        access_expires = now + timedelta(seconds=settings.access_token_ttl_seconds)
        access_out = build_access_token(
            AccessTokenPayload(
                user_id=active.user_id,
                session_id=active.session_id,
                issued_at=now,
                expires_at=access_expires,
            ),
            settings,
        )
    except Exception as e:
        log_technical("auth.refresh.rotation_failure", exc_type=type(e).__name__)
        raise

    log_business_event("auth.refresh.success", user_id=str(active.user_id))
    return RefreshOutput(
        access_token=access_out.token,
        refresh_token=plain_new,
        access_token_expires_in=settings.access_token_ttl_seconds,
        refresh_token_expires_in=settings.refresh_token_ttl_seconds,
        session_id=active.session_id,
    )


def logout_session_stub(payload: LogoutInput) -> None:
    _ = payload


async def logout_session_db(conn: asyncpg.Connection, session_id: UUID) -> None:
    await session_repository.revoke_session(
        conn, RevokeSessionInput(session_id=session_id, revocation_reason="logout")
    )
    await refresh_token_repository.revoke_session_tokens(
        conn, RevokeSessionTokensInput(session_id=session_id)
    )
    log_business_event("auth.logout")


def authenticate_access_token(payload: AccessTokenInput) -> AuthenticatedPrincipal:
    _ = payload.access_token
    return AuthenticatedPrincipal(
        user_id=payload.user_id,
        session_id=payload.session_id,
        role_id=_STUB_ROLE_ID,
        role_name="user",
    )


async def authenticate_access_token_db(
    conn: asyncpg.Connection,
    token: str,
    settings: AppSettings,
) -> AuthenticatedPrincipal:
    try:
        claims = parse_access_token(ParseAccessTokenInput(token=token, settings=settings))
    except jwt.PyJWTError as e:
        raise InvalidAccessTokenError from e
    active = await session_repository.get_active_session_with_user(
        conn, SessionLookupInput(session_id=claims.session_id)
    )
    if active is None:
        raise InvalidAccessTokenError()
    if active.user_id != claims.user_id:
        raise InvalidAccessTokenError()
    return AuthenticatedPrincipal(
        user_id=active.user_id,
        session_id=active.session_id,
        role_id=active.role_id,
        role_name=active.role_name,
    )
