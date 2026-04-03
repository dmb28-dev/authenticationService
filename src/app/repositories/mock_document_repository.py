"""mock_documents — SQL operations (own/all predicates in SQL)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import asyncpg

from app.repositories.types import MockDocumentRow


@dataclass(frozen=True)
class ListDocumentsForOwnerInput:
    owner_id: UUID


@dataclass(frozen=True)
class ListDocumentsAccessInput:
    current_user_id: UUID
    can_read_all: bool
    limit: int
    offset: int


@dataclass(frozen=True)
class GetDocumentByIdInput:
    document_id: UUID


@dataclass(frozen=True)
class InsertDocumentInput:
    owner_id: UUID
    title: str


@dataclass(frozen=True)
class UpdateDocumentDbInput:
    document_id: UUID
    current_user_id: UUID
    can_update_all: bool
    title: str | None
    status: str | None


@dataclass(frozen=True)
class DeleteDocumentDbInput:
    document_id: UUID
    current_user_id: UUID
    can_delete_all: bool


async def list_documents_for_owner(
    conn: asyncpg.Connection, payload: ListDocumentsForOwnerInput
) -> tuple[MockDocumentRow, ...]:
    rows = await conn.fetch(
        """
        SELECT id, owner_id, title, status, created_at
        FROM mock_documents
        WHERE owner_id = $1
        ORDER BY created_at DESC
        """,
        payload.owner_id,
    )
    return tuple(_row(r) for r in rows)


async def list_documents_with_access(
    conn: asyncpg.Connection, payload: ListDocumentsAccessInput
) -> tuple[tuple[MockDocumentRow, ...], int]:
    total = await conn.fetchval(
        """
        SELECT COUNT(*)::bigint
        FROM mock_documents
        WHERE ($1::bool OR owner_id = $2)
        """,
        payload.can_read_all,
        payload.current_user_id,
    )
    rows = await conn.fetch(
        """
        SELECT id, owner_id, title, status, created_at
        FROM mock_documents
        WHERE ($1::bool OR owner_id = $2)
        ORDER BY created_at DESC
        LIMIT $3 OFFSET $4
        """,
        payload.can_read_all,
        payload.current_user_id,
        payload.limit,
        payload.offset,
    )
    return tuple(_row(r) for r in rows), int(total or 0)


def _row(r: asyncpg.Record) -> MockDocumentRow:
    return MockDocumentRow(
        id=r["id"],
        owner_id=r["owner_id"],
        title=r["title"],
        status=r["status"],
        created_at=r["created_at"],
    )


async def get_document_by_id(
    conn: asyncpg.Connection, payload: GetDocumentByIdInput
) -> MockDocumentRow | None:
    row = await conn.fetchrow(
        """
        SELECT id, owner_id, title, status, created_at
        FROM mock_documents
        WHERE id = $1
        """,
        payload.document_id,
    )
    return None if row is None else _row(row)


async def insert_document(conn: asyncpg.Connection, payload: InsertDocumentInput) -> MockDocumentRow:
    row = await conn.fetchrow(
        """
        INSERT INTO mock_documents (owner_id, title, status)
        VALUES ($1, $2, 'draft')
        RETURNING id, owner_id, title, status, created_at
        """,
        payload.owner_id,
        payload.title,
    )
    return _row(row)


async def update_document_row(
    conn: asyncpg.Connection, payload: UpdateDocumentDbInput
) -> MockDocumentRow | None:
    row = await conn.fetchrow(
        """
        UPDATE mock_documents
        SET
            title = COALESCE($4, title),
            status = COALESCE($5, status)
        WHERE id = $1
          AND ($2::bool OR owner_id = $3)
        RETURNING id, owner_id, title, status, created_at
        """,
        payload.document_id,
        payload.can_update_all,
        payload.current_user_id,
        payload.title,
        payload.status,
    )
    return None if row is None else _row(row)


async def delete_document_row(
    conn: asyncpg.Connection, payload: DeleteDocumentDbInput
) -> int:
    status = await conn.execute(
        """
        DELETE FROM mock_documents
        WHERE id = $1
          AND ($2::bool OR owner_id = $3)
        """,
        payload.document_id,
        payload.can_delete_all,
        payload.current_user_id,
    )
    return int(status.split()[-1])
