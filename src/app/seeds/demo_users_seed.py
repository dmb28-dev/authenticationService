"""Demo users for each role (idempotent by canonical email)."""

from __future__ import annotations

import uuid

import asyncpg
from argon2 import PasswordHasher

_ph = PasswordHasher()

USER_SPECS: tuple[tuple[str, str, str, str | None, str], ...] = (
    ("admin@example.com", "Admin", "User", None, "admin"),
    ("manager@example.com", "Manager", "User", None, "manager"),
    ("user@example.com", "Regular", "User", None, "user"),
    ("guest@example.com", "Guest", "User", None, "guest"),
)


async def _role_id(conn: asyncpg.Connection, name: str) -> uuid.UUID:
    row = await conn.fetchrow("SELECT id FROM roles WHERE name = $1", name)
    if row is None:
        msg = f"role not found: {name}"
        raise RuntimeError(msg)
    return row["id"]


async def run(conn: asyncpg.Connection) -> dict[str, int]:
    password_hash = _ph.hash("Demo#12345")
    n = 0
    for email, first_name, last_name, middle_name, role_name in USER_SPECS:
        role_id = await _role_id(conn, role_name)
        await conn.execute(
            """
            INSERT INTO users (
                email,
                password_hash,
                first_name,
                last_name,
                middle_name,
                role_id
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT ((LOWER(TRIM(email)))) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                middle_name = EXCLUDED.middle_name,
                role_id = EXCLUDED.role_id,
                updated_at = NOW()
            """,
            email,
            password_hash,
            first_name,
            last_name,
            middle_name,
            role_id,
        )
        n += 1
    return {"users_upserted": n}
