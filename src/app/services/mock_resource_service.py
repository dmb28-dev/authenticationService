"""Mock documents/reports: stubs without DB; SQL + RBAC with PostgreSQL."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import asyncpg

from app.core.config import AppSettings
from app.core.logging import log_business_event
from app.domain import constants as c
from app.repositories import mock_document_repository, mock_report_repository
from app.repositories.types import MockDocumentRow, MockReportRow
from app.repositories.mock_document_repository import (
    DeleteDocumentDbInput,
    GetDocumentByIdInput,
    InsertDocumentInput,
    ListDocumentsAccessInput,
    UpdateDocumentDbInput,
)
from app.repositories.mock_report_repository import ListReportsAccessInput
from app.schemas.mock_schemas import (
    CreateDocumentInput,
    DeleteDocumentInput,
    GetDocumentInput,
    ListDocumentsInput,
    ListReportsInput,
    MockDocumentListOutput,
    MockDocumentOutput,
    MockReportListOutput,
    MockReportOutput,
    UpdateDocumentInput,
)
from app.services import access_service


class MockNotFoundError(Exception):
    """Resource does not exist."""


class MockForbiddenError(Exception):
    """Operation not allowed for this principal."""


def _log_mock_denied(*, user_id: UUID, action: str, business_element: str, reason: str) -> None:
    log_business_event(
        "mock.access.denied",
        user_id=str(user_id),
        action=action,
        business_element=business_element,
        reason=reason,
    )


def _fmt_ts(value: datetime | str) -> str:
    if isinstance(value, str):
        return value
    s = value.isoformat()
    if s.endswith("+00:00"):
        return s[:-6] + "Z"
    return s


def _doc_out(row: MockDocumentRow) -> MockDocumentOutput:
    return MockDocumentOutput(
        id=str(row.id),
        title=row.title,
        owner_id=row.owner_id,
        status=row.status,
        created_at=_fmt_ts(row.created_at),
    )


def _rep_out(row: MockReportRow) -> MockReportOutput:
    return MockReportOutput(
        id=str(row.id),
        title=row.title,
        owner_id=row.owner_id,
        summary=row.summary,
        created_at=_fmt_ts(row.created_at),
    )


def list_documents(payload: ListDocumentsInput) -> MockDocumentListOutput:
    _ = payload
    return MockDocumentListOutput(
        items=[
            MockDocumentOutput(
                id="doc-1",
                title="Quarterly plan",
                owner_id=UUID("00000000-0000-4000-8000-000000000001"),
                status="draft",
                created_at="2026-04-03T10:00:00Z",
            )
        ]
    )


async def list_documents_db(
    conn: asyncpg.Connection,
    payload: ListDocumentsInput,
    settings: AppSettings,
) -> tuple[MockDocumentListOutput, int]:
    _ = settings
    decision = await access_service.resolve_action_access_db(
        conn,
        role_id=payload.role_id,
        business_element_code=c.BE_DOCUMENTS,
        action=c.ACTION_READ,
    )
    if not decision.allow:
        return MockDocumentListOutput(items=[]), 0
    items, total = await mock_document_repository.list_documents_with_access(
        conn,
        ListDocumentsAccessInput(
            current_user_id=payload.user_id,
            can_read_all=decision.scope_all,
            limit=payload.limit,
            offset=payload.offset,
        ),
    )
    return MockDocumentListOutput(items=[_doc_out(i) for i in items]), total


def get_document(payload: GetDocumentInput) -> MockDocumentOutput:
    if payload.document_id == "missing":
        msg = "not found"
        raise ValueError(msg)
    return MockDocumentOutput(
        id=payload.document_id,
        title="Stub document",
        owner_id=payload.user_id,
        status="draft",
        created_at="2026-04-03T10:00:00Z",
    )


async def get_document_db(
    conn: asyncpg.Connection,
    payload: GetDocumentInput,
    settings: AppSettings,
) -> MockDocumentOutput:
    _ = settings
    decision = await access_service.resolve_action_access_db(
        conn,
        role_id=payload.role_id,
        business_element_code=c.BE_DOCUMENTS,
        action=c.ACTION_READ,
    )
    if not decision.allow:
        _log_mock_denied(
            user_id=payload.user_id,
            action=c.ACTION_READ,
            business_element=c.BE_DOCUMENTS,
            reason="rbac_denied",
        )
        raise MockForbiddenError
    try:
        doc_id = UUID(payload.document_id)
    except ValueError as e:
        raise MockNotFoundError from e
    row = await mock_document_repository.get_document_by_id(conn, GetDocumentByIdInput(document_id=doc_id))
    if row is None:
        raise MockNotFoundError
    if not decision.scope_all and row.owner_id != payload.user_id:
        _log_mock_denied(
            user_id=payload.user_id,
            action=c.ACTION_READ,
            business_element=c.BE_DOCUMENTS,
            reason="not_owner",
        )
        raise MockForbiddenError
    return _doc_out(row)


def create_document(payload: CreateDocumentInput) -> MockDocumentOutput:
    return MockDocumentOutput(
        id="doc-new",
        title=payload.title,
        owner_id=payload.user_id,
        status="draft",
        created_at="2026-04-03T10:00:00Z",
    )


async def create_document_db(
    conn: asyncpg.Connection,
    payload: CreateDocumentInput,
    settings: AppSettings,
) -> MockDocumentOutput:
    _ = settings
    decision = await access_service.resolve_action_access_db(
        conn,
        role_id=payload.role_id,
        business_element_code=c.BE_DOCUMENTS,
        action=c.ACTION_CREATE,
    )
    if not decision.allow:
        _log_mock_denied(
            user_id=payload.user_id,
            action=c.ACTION_CREATE,
            business_element=c.BE_DOCUMENTS,
            reason="rbac_denied",
        )
        raise MockForbiddenError
    row = await mock_document_repository.insert_document(
        conn,
        InsertDocumentInput(owner_id=payload.user_id, title=payload.title),
    )
    return _doc_out(row)


def update_document(payload: UpdateDocumentInput) -> MockDocumentOutput:
    return MockDocumentOutput(
        id=payload.document_id,
        title=payload.title or "Updated",
        owner_id=payload.user_id,
        status=payload.status or "draft",
        created_at="2026-04-03T10:00:00Z",
    )


async def update_document_db(
    conn: asyncpg.Connection,
    payload: UpdateDocumentInput,
    settings: AppSettings,
) -> MockDocumentOutput:
    _ = settings
    decision = await access_service.resolve_action_access_db(
        conn,
        role_id=payload.role_id,
        business_element_code=c.BE_DOCUMENTS,
        action=c.ACTION_UPDATE,
    )
    if not decision.allow:
        _log_mock_denied(
            user_id=payload.user_id,
            action=c.ACTION_UPDATE,
            business_element=c.BE_DOCUMENTS,
            reason="rbac_denied",
        )
        raise MockForbiddenError
    try:
        doc_id = UUID(payload.document_id)
    except ValueError as e:
        raise MockNotFoundError from e
    exists = await mock_document_repository.get_document_by_id(conn, GetDocumentByIdInput(document_id=doc_id))
    if exists is None:
        raise MockNotFoundError
    row = await mock_document_repository.update_document_row(
        conn,
        UpdateDocumentDbInput(
            document_id=doc_id,
            current_user_id=payload.user_id,
            can_update_all=decision.scope_all,
            title=payload.title,
            status=payload.status,
        ),
    )
    if row is None:
        _log_mock_denied(
            user_id=payload.user_id,
            action=c.ACTION_UPDATE,
            business_element=c.BE_DOCUMENTS,
            reason="not_owner_or_scope",
        )
        raise MockForbiddenError
    return _doc_out(row)


def delete_document(payload: DeleteDocumentInput) -> None:
    _ = payload


async def delete_document_db(
    conn: asyncpg.Connection,
    payload: DeleteDocumentInput,
    settings: AppSettings,
) -> None:
    _ = settings
    decision = await access_service.resolve_action_access_db(
        conn,
        role_id=payload.role_id,
        business_element_code=c.BE_DOCUMENTS,
        action=c.ACTION_DELETE,
    )
    if not decision.allow:
        _log_mock_denied(
            user_id=payload.user_id,
            action=c.ACTION_DELETE,
            business_element=c.BE_DOCUMENTS,
            reason="rbac_denied",
        )
        raise MockForbiddenError
    try:
        doc_id = UUID(payload.document_id)
    except ValueError as e:
        raise MockNotFoundError from e
    exists = await mock_document_repository.get_document_by_id(conn, GetDocumentByIdInput(document_id=doc_id))
    if exists is None:
        raise MockNotFoundError
    deleted = await mock_document_repository.delete_document_row(
        conn,
        DeleteDocumentDbInput(
            document_id=doc_id,
            current_user_id=payload.user_id,
            can_delete_all=decision.scope_all,
        ),
    )
    if deleted == 0:
        _log_mock_denied(
            user_id=payload.user_id,
            action=c.ACTION_DELETE,
            business_element=c.BE_DOCUMENTS,
            reason="not_owner_or_scope",
        )
        raise MockForbiddenError


def list_reports(payload: ListReportsInput) -> MockReportListOutput:
    _ = payload
    return MockReportListOutput(
        items=[
            MockReportOutput(
                id="rep-1",
                title="Monthly",
                owner_id=payload.user_id,
                summary="stub",
                created_at="2026-04-03T10:00:00Z",
            )
        ]
    )


async def list_reports_db(
    conn: asyncpg.Connection,
    payload: ListReportsInput,
    settings: AppSettings,
) -> tuple[MockReportListOutput, int]:
    _ = settings
    decision = await access_service.resolve_action_access_db(
        conn,
        role_id=payload.role_id,
        business_element_code=c.BE_REPORTS,
        action=c.ACTION_READ,
    )
    if not decision.allow:
        return MockReportListOutput(items=[]), 0
    items, total = await mock_report_repository.list_reports_with_access(
        conn,
        ListReportsAccessInput(
            current_user_id=payload.user_id,
            can_read_all=decision.scope_all,
            limit=payload.limit,
            offset=payload.offset,
        ),
    )
    return MockReportListOutput(items=[_rep_out(i) for i in items]), total
