"""auth_sessions — SQL operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

from app.repositories.types import AuthSessionRow, SessionWithUserRow


@dataclass(frozen=True)
class CreateAuthSessionInput:
    user_id: UUID
    expires_at: datetime


@dataclass(frozen=True)
class SessionLookupInput:
    session_id: UUID


@dataclass(frozen=True)
class RevokeSessionInput:
    session_id: UUID
    revocation_reason: str


@dataclass(frozen=True)
class RevokeAllUserSessionsInput:
    user_id: UUID
    revocation_reason: str


async def create_auth_session(
    conn: asyncpg.Connection, payload: CreateAuthSessionInput
) -> AuthSessionRow:
    row = await conn.fetchrow(
        """
        INSERT INTO auth_sessions (user_id, expires_at)
        VALUES ($1, $2)
        RETURNING id, user_id, created_at, expires_at, revoked_at, revocation_reason
        """,
        payload.user_id,
        payload.expires_at,
    )
    return AuthSessionRow(
        id=row["id"],
        user_id=row["user_id"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        revoked_at=row["revoked_at"],
        revocation_reason=row["revocation_reason"],
    )


async def get_session_with_user(
    conn: asyncpg.Connection, payload: SessionLookupInput
) -> SessionWithUserRow | None:
    row = await conn.fetchrow(
        """
        SELECT
            s.id AS session_id,
            s.user_id,
            s.expires_at AS session_expires_at,
            s.revoked_at AS session_revoked_at,
            u.email,
            u.role_id,
            r.name AS role_name,
            u.is_active
        FROM auth_sessions s
        JOIN users u ON u.id = s.user_id
        JOIN roles r ON r.id = u.role_id
        WHERE s.id = $1
        """,
        payload.session_id,
    )
    if row is None:
        return None
    return SessionWithUserRow(
        session_id=row["session_id"],
        user_id=row["user_id"],
        session_expires_at=row["session_expires_at"],
        session_revoked_at=row["session_revoked_at"],
        email=row["email"],
        role_id=row["role_id"],
        role_name=row["role_name"],
        is_active=row["is_active"],
    )


async def get_active_session_with_user(
    conn: asyncpg.Connection, payload: SessionLookupInput
) -> SessionWithUserRow | None:
    row = await conn.fetchrow(
        """
        SELECT
            s.id AS session_id,
            s.user_id,
            s.expires_at AS session_expires_at,
            s.revoked_at AS session_revoked_at,
            u.email,
            u.role_id,
            r.name AS role_name,
            u.is_active
        FROM auth_sessions s
        JOIN users u ON u.id = s.user_id
        JOIN roles r ON r.id = u.role_id
        WHERE s.id = $1
          AND s.revoked_at IS NULL
          AND s.expires_at > NOW()
          AND u.is_active IS TRUE
        """,
        payload.session_id,
    )
    if row is None:
        return None
    return SessionWithUserRow(
        session_id=row["session_id"],
        user_id=row["user_id"],
        session_expires_at=row["session_expires_at"],
        session_revoked_at=row["session_revoked_at"],
        email=row["email"],
        role_id=row["role_id"],
        role_name=row["role_name"],
        is_active=row["is_active"],
    )


async def revoke_session(conn: asyncpg.Connection, payload: RevokeSessionInput) -> None:
    await conn.execute(
        """
        UPDATE auth_sessions
        SET revoked_at = NOW(), revocation_reason = $2
        WHERE id = $1 AND revoked_at IS NULL
        """,
        payload.session_id,
        payload.revocation_reason,
    )


async def revoke_all_user_sessions(
    conn: asyncpg.Connection, payload: RevokeAllUserSessionsInput
) -> int:
    result = await conn.execute(
        """
        UPDATE auth_sessions
        SET revoked_at = NOW(), revocation_reason = $2
        WHERE user_id = $1 AND revoked_at IS NULL
        """,
        payload.user_id,
        payload.revocation_reason,
    )
    # asyncpg returns 'UPDATE N'
    return int(result.split()[-1])
