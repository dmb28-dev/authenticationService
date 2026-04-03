from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies.auth import get_current_principal
from app.api.dependencies.db_pool import get_optional_db_pool
from app.api.dependencies.mock_access import RequireMockAccess
from app.core.errors import raise_api_error
from app.core.observability import mock_http, record_route_latency
from app.core.responses import build_list_response, build_success_response
from app.db.pool import DatabasePool
from app.domain import constants as c
from app.schemas.auth_schemas import AuthenticatedPrincipal
from app.schemas.mock_schemas import (
    CreateDocumentInput,
    CreateDocumentRequest,
    DeleteDocumentInput,
    GetDocumentInput,
    ListDocumentsInput,
    ListReportsInput,
    UpdateDocumentInput,
    UpdateDocumentRequest,
)
from app.services import mock_resource_service

router = APIRouter()


@router.get("/documents")
async def list_documents(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    _access: Annotated[AuthenticatedPrincipal, Depends(RequireMockAccess(c.BE_DOCUMENTS, c.ACTION_READ))],
    request: Request,
    pool: DatabasePool | None = Depends(get_optional_db_pool),
) -> dict:
    _ = _access
    t0 = time.perf_counter()
    settings = request.app.state.settings
    payload = ListDocumentsInput(user_id=principal.user_id, role_id=principal.role_id)
    if pool is None:
        out = mock_resource_service.list_documents(payload)
        total = len(out.items)
    else:
        async with pool.acquire() as conn:
            out, total = await mock_resource_service.list_documents_db(conn, payload, settings)
    record_route_latency("mock_documents_list", time.perf_counter() - t0)
    return build_list_response(
        [i.model_dump(mode="json") for i in out.items],
        limit=payload.limit,
        offset=payload.offset,
        total=total,
    )


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    _access: Annotated[AuthenticatedPrincipal, Depends(RequireMockAccess(c.BE_DOCUMENTS, c.ACTION_READ))],
    request: Request,
    pool: DatabasePool | None = Depends(get_optional_db_pool),
) -> dict:
    _ = _access
    settings = request.app.state.settings
    payload = GetDocumentInput(
        user_id=principal.user_id,
        role_id=principal.role_id,
        document_id=document_id,
    )
    t0 = time.perf_counter()
    try:
        if pool is None:
            doc = mock_resource_service.get_document(payload)
        else:
            async with pool.acquire() as conn:
                doc = await mock_resource_service.get_document_db(conn, payload, settings)
    except mock_resource_service.MockNotFoundError:
        mock_http(404, c.BE_DOCUMENTS)
        raise_api_error(404, error="not_found", message="Document not found")
    except mock_resource_service.MockForbiddenError:
        mock_http(403, c.BE_DOCUMENTS)
        raise_api_error(403, error="forbidden", message="Access denied")
    except ValueError:
        mock_http(404, c.BE_DOCUMENTS)
        raise_api_error(404, error="not_found", message="Document not found")
    finally:
        record_route_latency("mock_documents_get", time.perf_counter() - t0)
    return build_success_response(doc.model_dump(mode="json"))


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def create_document(
    body: CreateDocumentRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    _access: Annotated[AuthenticatedPrincipal, Depends(RequireMockAccess(c.BE_DOCUMENTS, c.ACTION_CREATE))],
    request: Request,
    pool: DatabasePool | None = Depends(get_optional_db_pool),
) -> dict:
    _ = _access
    settings = request.app.state.settings
    payload = CreateDocumentInput(user_id=principal.user_id, role_id=principal.role_id, title=body.title)
    t0 = time.perf_counter()
    try:
        if pool is None:
            doc = mock_resource_service.create_document(payload)
        else:
            async with pool.acquire() as conn:
                doc = await mock_resource_service.create_document_db(conn, payload, settings)
    except mock_resource_service.MockForbiddenError:
        mock_http(403, c.BE_DOCUMENTS)
        raise_api_error(403, error="forbidden", message="Access denied")
    finally:
        record_route_latency("mock_documents_create", time.perf_counter() - t0)
    return build_success_response(doc.model_dump(mode="json"))


@router.patch("/documents/{document_id}")
async def update_document(
    document_id: str,
    body: UpdateDocumentRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    _access: Annotated[AuthenticatedPrincipal, Depends(RequireMockAccess(c.BE_DOCUMENTS, c.ACTION_UPDATE))],
    request: Request,
    pool: DatabasePool | None = Depends(get_optional_db_pool),
) -> dict:
    _ = _access
    settings = request.app.state.settings
    payload = UpdateDocumentInput(
        user_id=principal.user_id,
        role_id=principal.role_id,
        document_id=document_id,
        title=body.title,
        status=body.status,
    )
    t0 = time.perf_counter()
    try:
        if pool is None:
            doc = mock_resource_service.update_document(payload)
        else:
            async with pool.acquire() as conn:
                doc = await mock_resource_service.update_document_db(conn, payload, settings)
    except mock_resource_service.MockNotFoundError:
        mock_http(404, c.BE_DOCUMENTS)
        raise_api_error(404, error="not_found", message="Document not found")
    except mock_resource_service.MockForbiddenError:
        mock_http(403, c.BE_DOCUMENTS)
        raise_api_error(403, error="forbidden", message="Access denied")
    finally:
        record_route_latency("mock_documents_patch", time.perf_counter() - t0)
    return build_success_response(doc.model_dump(mode="json"))


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    _access: Annotated[AuthenticatedPrincipal, Depends(RequireMockAccess(c.BE_DOCUMENTS, c.ACTION_DELETE))],
    request: Request,
    pool: DatabasePool | None = Depends(get_optional_db_pool),
) -> None:
    _ = _access
    settings = request.app.state.settings
    payload = DeleteDocumentInput(
        user_id=principal.user_id,
        role_id=principal.role_id,
        document_id=document_id,
    )
    t0 = time.perf_counter()
    try:
        if pool is None:
            mock_resource_service.delete_document(payload)
        else:
            async with pool.acquire() as conn:
                await mock_resource_service.delete_document_db(conn, payload, settings)
    except mock_resource_service.MockNotFoundError:
        mock_http(404, c.BE_DOCUMENTS)
        raise_api_error(404, error="not_found", message="Document not found")
    except mock_resource_service.MockForbiddenError:
        mock_http(403, c.BE_DOCUMENTS)
        raise_api_error(403, error="forbidden", message="Access denied")
    finally:
        record_route_latency("mock_documents_delete", time.perf_counter() - t0)


@router.get("/reports")
async def list_reports(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    _access: Annotated[AuthenticatedPrincipal, Depends(RequireMockAccess(c.BE_REPORTS, c.ACTION_READ))],
    request: Request,
    pool: DatabasePool | None = Depends(get_optional_db_pool),
) -> dict:
    _ = _access
    settings = request.app.state.settings
    t0 = time.perf_counter()
    payload = ListReportsInput(user_id=principal.user_id, role_id=principal.role_id)
    if pool is None:
        out = mock_resource_service.list_reports(payload)
        total = len(out.items)
    else:
        async with pool.acquire() as conn:
            out, total = await mock_resource_service.list_reports_db(conn, payload, settings)
    record_route_latency("mock_reports_list", time.perf_counter() - t0)
    return build_list_response(
        [i.model_dump(mode="json") for i in out.items],
        limit=payload.limit,
        offset=payload.offset,
        total=total,
    )
