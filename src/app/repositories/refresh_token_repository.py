"""refresh_tokens — SQL operations (hash-only storage)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

from app.repositories.types import RefreshTokenPairRow, RefreshTokenRow


@dataclass(frozen=True)
class CreateRefreshTokenInput:
    session_id: UUID
    token_hash: str
    expires_at: datetime


@dataclass(frozen=True)
class RefreshTokenLookupInput:
    token_hash: str


@dataclass(frozen=True)
class RotateRefreshTokenInput:
    old_token_id: UUID
    new_token_hash: str
    new_expires_at: datetime


@dataclass(frozen=True)
class RevokeSessionTokensInput:
    session_id: UUID


@dataclass(frozen=True)
class RevokeUserTokensInput:
    user_id: UUID


def _row_refresh(r: asyncpg.Record) -> RefreshTokenRow:
    return RefreshTokenRow(
        id=r["id"],
        session_id=r["session_id"],
        token_hash=r["token_hash"],
        expires_at=r["expires_at"],
        rotated_at=r["rotated_at"],
        revoked_at=r["revoked_at"],
        replaced_by_id=r["replaced_by_id"],
    )


async def create_refresh_token(
    conn: asyncpg.Connection, payload: CreateRefreshTokenInput
) -> RefreshTokenRow:
    row = await conn.fetchrow(
        """
        INSERT INTO refresh_tokens (session_id, token_hash, expires_at)
        VALUES ($1, $2, $3)
        RETURNING id, session_id, token_hash, expires_at, rotated_at, revoked_at, replaced_by_id
        """,
        payload.session_id,
        payload.token_hash,
        payload.expires_at,
    )
    return _row_refresh(row)


async def get_token_for_update(
    conn: asyncpg.Connection, payload: RefreshTokenLookupInput
) -> RefreshTokenRow | None:
    row = await conn.fetchrow(
        """
        SELECT id, session_id, token_hash, expires_at, rotated_at, revoked_at, replaced_by_id
        FROM refresh_tokens
        WHERE token_hash = $1
        FOR UPDATE
        """,
        payload.token_hash,
    )
    return None if row is None else _row_refresh(row)


async def rotate_refresh_token(
    conn: asyncpg.Connection, payload: RotateRefreshTokenInput
) -> RefreshTokenPairRow:
    old = await conn.fetchrow(
        """
        SELECT id, session_id, token_hash, expires_at, rotated_at, revoked_at, replaced_by_id
        FROM refresh_tokens
        WHERE id = $1
        FOR UPDATE
        """,
        payload.old_token_id,
    )
    if old is None:
        msg = "refresh token not found"
        raise ValueError(msg)
    new_row = await conn.fetchrow(
        """
        INSERT INTO refresh_tokens (session_id, token_hash, expires_at, rotated_at)
        VALUES ($1, $2, $3, NOW())
        RETURNING id, session_id, token_hash, expires_at, rotated_at, revoked_at, replaced_by_id
        """,
        old["session_id"],
        payload.new_token_hash,
        payload.new_expires_at,
    )
    await conn.execute(
        """
        UPDATE refresh_tokens
        SET rotated_at = COALESCE(rotated_at, NOW()),
            revoked_at = NOW(),
            replaced_by_id = $2
        WHERE id = $1
        """,
        payload.old_token_id,
        new_row["id"],
    )
    old_refresh = _row_refresh(old)
    return RefreshTokenPairRow(
        old_token_id=old_refresh.id,
        new_refresh=_row_refresh(new_row),
    )


async def revoke_session_tokens(conn: asyncpg.Connection, payload: RevokeSessionTokensInput) -> int:
    status = await conn.execute(
        """
        UPDATE refresh_tokens
        SET revoked_at = NOW()
        WHERE session_id = $1 AND revoked_at IS NULL
        """,
        payload.session_id,
    )
    return int(status.split()[-1])


async def revoke_user_tokens(conn: asyncpg.Connection, payload: RevokeUserTokensInput) -> int:
    status = await conn.execute(
        """
        UPDATE refresh_tokens rt
        SET revoked_at = NOW()
        FROM auth_sessions s
        WHERE rt.session_id = s.id
          AND s.user_id = $1
          AND rt.revoked_at IS NULL
        """,
        payload.user_id,
    )
    return int(status.split()[-1])
