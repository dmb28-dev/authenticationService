"""Demo mock documents and reports with stable UUIDs."""

from __future__ import annotations

import uuid

import asyncpg

DOC_1 = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1")
DOC_2 = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2")
RPT_1 = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1")


async def _user_id_by_email(conn: asyncpg.Connection, email: str) -> uuid.UUID:
    row = await conn.fetchrow(
        "SELECT id FROM users WHERE LOWER(TRIM(email)) = LOWER(TRIM($1))",
        email,
    )
    if row is None:
        msg = f"user not found: {email}"
        raise RuntimeError(msg)
    return row["id"]


async def run(conn: asyncpg.Connection) -> dict[str, int]:
    admin_id = await _user_id_by_email(conn, "admin@example.com")
    user_id = await _user_id_by_email(conn, "user@example.com")

    docs = 0
    await conn.execute(
        """
        INSERT INTO mock_documents (id, owner_id, title, status)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (id) DO UPDATE SET
            owner_id = EXCLUDED.owner_id,
            title = EXCLUDED.title,
            status = EXCLUDED.status
        """,
        DOC_1,
        admin_id,
        "Admin sample document",
        "published",
    )
    docs += 1
    await conn.execute(
        """
        INSERT INTO mock_documents (id, owner_id, title, status)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (id) DO UPDATE SET
            owner_id = EXCLUDED.owner_id,
            title = EXCLUDED.title,
            status = EXCLUDED.status
        """,
        DOC_2,
        user_id,
        "User sample document",
        "draft",
    )
    docs += 1

    reports = 0
    await conn.execute(
        """
        INSERT INTO mock_reports (id, owner_id, title, summary)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (id) DO UPDATE SET
            owner_id = EXCLUDED.owner_id,
            title = EXCLUDED.title,
            summary = EXCLUDED.summary
        """,
        RPT_1,
        admin_id,
        "Weekly summary",
        "Demo report body",
    )
    reports += 1

    return {"mock_documents_created": docs, "mock_reports_created": reports}
