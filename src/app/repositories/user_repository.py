"""Users table — SQL operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

from app.repositories.types import UserRow, _user_from_record


@dataclass(frozen=True)
class CreateUserInput:
    email: str
    password_hash: str
    first_name: str
    last_name: str
    middle_name: str | None
    role_id: UUID


@dataclass(frozen=True)
class UserByEmailInput:
    email: str


@dataclass(frozen=True)
class UserByIdInput:
    user_id: UUID


@dataclass(frozen=True)
class EmailLookupInput:
    email: str


@dataclass(frozen=True)
class EmailTakenExceptInput:
    email: str
    except_user_id: UUID


@dataclass(frozen=True)
class UserProfileDbRow:
    id: UUID
    email: str
    first_name: str
    last_name: str
    middle_name: str | None
    is_active: bool
    created_at: datetime
    role_id: UUID
    role_name: str


@dataclass(frozen=True)
class UpdateUserProfileInput:
    user_id: UUID
    first_name: str
    last_name: str
    middle_name: str | None
    email: str


@dataclass(frozen=True)
class DeactivateUserInput:
    user_id: UUID


async def create_user(conn: asyncpg.Connection, payload: CreateUserInput) -> UserRow:
    row = await conn.fetchrow(
        """
        INSERT INTO users (
            email, password_hash, first_name, last_name, middle_name, role_id
        )
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING
            id, email, password_hash, first_name, last_name, middle_name,
            is_active, role_id, created_at, updated_at, deactivated_at
        """,
        payload.email,
        payload.password_hash,
        payload.first_name,
        payload.last_name,
        payload.middle_name,
        payload.role_id,
    )
    return _user_from_record(row)


async def get_user_by_email(conn: asyncpg.Connection, payload: UserByEmailInput) -> UserRow | None:
    row = await conn.fetchrow(
        """
        SELECT
            id, email, password_hash, first_name, last_name, middle_name,
            is_active, role_id, created_at, updated_at, deactivated_at
        FROM users
        WHERE LOWER(TRIM(email)) = LOWER(TRIM($1))
        """,
        payload.email,
    )
    return None if row is None else _user_from_record(row)


async def is_email_taken(conn: asyncpg.Connection, payload: EmailLookupInput) -> bool:
    row = await conn.fetchrow(
        """
        SELECT 1 AS ok
        FROM users
        WHERE LOWER(TRIM(email)) = LOWER(TRIM($1))
        LIMIT 1
        """,
        payload.email,
    )
    return row is not None


async def is_email_taken_by_other(conn: asyncpg.Connection, payload: EmailTakenExceptInput) -> bool:
    row = await conn.fetchrow(
        """
        SELECT 1 AS ok
        FROM users
        WHERE LOWER(TRIM(email)) = LOWER(TRIM($1))
          AND id <> $2
        LIMIT 1
        """,
        payload.email,
        payload.except_user_id,
    )
    return row is not None


async def get_user_profile_by_id(
    conn: asyncpg.Connection, payload: UserByIdInput
) -> UserProfileDbRow | None:
    row = await conn.fetchrow(
        """
        SELECT
            u.id,
            u.email,
            u.first_name,
            u.last_name,
            u.middle_name,
            u.is_active,
            u.created_at,
            r.id AS role_id,
            r.name AS role_name
        FROM users u
        JOIN roles r ON r.id = u.role_id
        WHERE u.id = $1
        """,
        payload.user_id,
    )
    if row is None:
        return None
    return UserProfileDbRow(
        id=row["id"],
        email=row["email"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        middle_name=row["middle_name"],
        is_active=row["is_active"],
        created_at=row["created_at"],
        role_id=row["role_id"],
        role_name=row["role_name"],
    )


async def get_user_by_id(conn: asyncpg.Connection, payload: UserByIdInput) -> UserRow | None:
    row = await conn.fetchrow(
        """
        SELECT
            id, email, password_hash, first_name, last_name, middle_name,
            is_active, role_id, created_at, updated_at, deactivated_at
        FROM users
        WHERE id = $1
        """,
        payload.user_id,
    )
    return None if row is None else _user_from_record(row)


async def update_user_profile(conn: asyncpg.Connection, payload: UpdateUserProfileInput) -> UserRow:
    row = await conn.fetchrow(
        """
        UPDATE users
        SET
            first_name = $2,
            last_name = $3,
            middle_name = $4,
            email = $5,
            updated_at = NOW()
        WHERE id = $1
        RETURNING
            id, email, password_hash, first_name, last_name, middle_name,
            is_active, role_id, created_at, updated_at, deactivated_at
        """,
        payload.user_id,
        payload.first_name,
        payload.last_name,
        payload.middle_name,
        payload.email,
    )
    if row is None:
        msg = "user not found"
        raise ValueError(msg)
    return _user_from_record(row)


async def deactivate_user(conn: asyncpg.Connection, payload: DeactivateUserInput) -> UserRow:
    row = await conn.fetchrow(
        """
        UPDATE users
        SET
            is_active = FALSE,
            deactivated_at = NOW(),
            updated_at = NOW()
        WHERE id = $1
        RETURNING
            id, email, password_hash, first_name, last_name, middle_name,
            is_active, role_id, created_at, updated_at, deactivated_at
        """,
        payload.user_id,
    )
    if row is None:
        msg = "user not found"
        raise ValueError(msg)
    return _user_from_record(row)
