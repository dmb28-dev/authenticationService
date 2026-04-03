"""Profile and soft-delete use-cases (stub without DB, SQL with PostgreSQL)."""

from __future__ import annotations

from uuid import UUID

import asyncpg

from app.core.config import AppSettings
from app.core.logging import log_business_event, log_technical
from app.core.security import NormalizeEmailInput, normalize_email
from app.repositories import refresh_token_repository, session_repository, user_repository
from app.repositories.refresh_token_repository import RevokeUserTokensInput
from app.repositories.session_repository import RevokeAllUserSessionsInput
from app.repositories.user_repository import (
    EmailTakenExceptInput,
    UpdateUserProfileInput,
    UserByIdInput,
)
from app.schemas.auth_schemas import RoleBrief, UserProfileOutput
from app.schemas.profile_schemas import CurrentUserInput, UpdateProfileInput

_STUB_ROLE_ID = UUID("00000000-0000-4000-8000-0000000000b1")


def _profile_from_db(row: user_repository.UserProfileDbRow) -> UserProfileOutput:
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


def get_current_profile_stub(payload: CurrentUserInput) -> UserProfileOutput:
    return UserProfileOutput(
        id=payload.user_id,
        email="stub@example.com",
        first_name="Stub",
        last_name="User",
        middle_name=None,
        role=RoleBrief(id=payload.role_id, name=payload.role_name),
        is_active=True,
        created_at="2026-04-03T10:00:00Z",
    )


async def get_current_profile_db(
    conn: asyncpg.Connection,
    payload: CurrentUserInput,
    _settings: AppSettings,
) -> UserProfileOutput:
    row = await user_repository.get_user_profile_by_id(conn, UserByIdInput(user_id=payload.user_id))
    if row is None:
        msg = "user not found"
        raise ValueError(msg)
    return _profile_from_db(row)


def update_current_profile_stub(payload: UpdateProfileInput) -> UserProfileOutput:
    email = str(payload.email) if payload.email else "updated@example.com"
    fn = payload.first_name or "Updated"
    ln = payload.last_name or "User"
    return UserProfileOutput(
        id=payload.user_id,
        email=email,
        first_name=fn,
        last_name=ln,
        middle_name=payload.middle_name,
        role=RoleBrief(id=_STUB_ROLE_ID, name="user"),
        is_active=True,
        created_at="2026-04-03T10:00:00Z",
    )


class EmailConflictError(Exception):
    """Email already used by another account."""


async def update_current_profile_db(
    conn: asyncpg.Connection,
    payload: UpdateProfileInput,
    settings: AppSettings,
) -> UserProfileOutput:
    current = await user_repository.get_user_profile_by_id(conn, UserByIdInput(user_id=payload.user_id))
    if current is None:
        msg = "user not found"
        raise ValueError(msg)

    first_name = payload.first_name if payload.first_name is not None else current.first_name
    last_name = payload.last_name if payload.last_name is not None else current.last_name
    middle_name = current.middle_name
    if payload.middle_name is not None:
        middle_name = payload.middle_name

    email = current.email
    if payload.email is not None:
        email = normalize_email(NormalizeEmailInput(email=str(payload.email))).email
        if email != current.email:
            taken = await user_repository.is_email_taken_by_other(
                conn,
                EmailTakenExceptInput(email=email, except_user_id=payload.user_id),
            )
            if taken:
                raise EmailConflictError()

    try:
        updated = await user_repository.update_user_profile(
            conn,
            UpdateUserProfileInput(
                user_id=payload.user_id,
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                email=email,
            ),
        )
    except Exception as e:
        log_technical("profile.update.persistence_failure", exc_type=type(e).__name__)
        raise
    profile = await user_repository.get_user_profile_by_id(conn, UserByIdInput(user_id=updated.id))
    if profile is None:
        msg = "user not found after update"
        raise RuntimeError(msg)
    log_business_event("profile.updated", user_id=str(payload.user_id))
    return _profile_from_db(profile)


def soft_delete_current_user_stub(payload: CurrentUserInput) -> None:
    _ = payload


async def soft_delete_current_user_db(conn: asyncpg.Connection, payload: CurrentUserInput) -> None:
    try:
        await user_repository.deactivate_user(conn, user_repository.DeactivateUserInput(user_id=payload.user_id))
        await session_repository.revoke_all_user_sessions(
            conn,
            RevokeAllUserSessionsInput(user_id=payload.user_id, revocation_reason="soft_delete"),
        )
        await refresh_token_repository.revoke_user_tokens(
            conn,
            RevokeUserTokensInput(user_id=payload.user_id),
        )
    except Exception as e:
        log_technical("account.deactivate.failure", exc_type=type(e).__name__)
        raise
    log_business_event("account.deactivated", user_id=str(payload.user_id))
