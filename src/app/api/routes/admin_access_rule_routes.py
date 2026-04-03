from __future__ import annotations

import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.api.dependencies.auth import require_admin_role
from app.api.dependencies.db_pool import get_optional_db_pool
from app.core.errors import raise_api_error
from app.core.observability import admin_rules_conflict, admin_rules_read, admin_rules_write, record_route_latency
from app.core.responses import build_success_response
from app.db.pool import DatabasePool
from app.schemas.access_rule_schemas import (
    ListAccessRulesInput,
    UpsertAccessRuleInput,
    UpsertAccessRuleRequest,
)
from app.schemas.auth_schemas import AuthenticatedPrincipal
from app.services import admin_access_rule_service

router = APIRouter()


@router.get("")
async def list_rules(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_admin_role)],
    request: Request,
    pool: DatabasePool | None = Depends(get_optional_db_pool),
    role_name: str | None = None,
    business_element_code: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    settings = request.app.state.settings
    payload = ListAccessRulesInput(
        admin_user_id=principal.user_id,
        role_name=role_name,
        business_element_code=business_element_code,
        limit=limit,
        offset=offset,
    )
    t0 = time.perf_counter()
    if pool is None:
        out = admin_access_rule_service.list_access_rules_stub(payload)
    else:
        async with pool.acquire() as conn:
            out = await admin_access_rule_service.list_access_rules_db(conn, payload, settings)
    admin_rules_read()
    record_route_latency("admin_access_rules_list", time.perf_counter() - t0)
    return {
        "data": [r.model_dump(mode="json") for r in out.data],
        "matrix": [m.model_dump(mode="json") for m in out.matrix],
        "meta": out.meta,
    }


@router.put("/{role_id}/{business_element_code}")
async def upsert_rule(
    role_id: UUID,
    business_element_code: str,
    body: UpsertAccessRuleRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_admin_role)],
    request: Request,
    pool: DatabasePool | None = Depends(get_optional_db_pool),
) -> JSONResponse:
    settings = request.app.state.settings
    payload = UpsertAccessRuleInput(
        admin_user_id=principal.user_id,
        role_id=role_id,
        business_element_code=business_element_code,
        version=body.version,
        permissions=body.permissions,
    )
    t0 = time.perf_counter()
    try:
        if pool is None:
            out = admin_access_rule_service.upsert_access_rule_stub(payload)
        else:
            async with pool.acquire() as conn:
                out = await admin_access_rule_service.upsert_access_rule_db(conn, payload, settings)
    except admin_access_rule_service.AccessRuleNotFoundError:
        record_route_latency("admin_access_rules_upsert", time.perf_counter() - t0)
        raise_api_error(404, error="not_found", message="Role, business element, or rule not found")
    except admin_access_rule_service.AccessRuleVersionConflictError:
        admin_rules_conflict()
        record_route_latency("admin_access_rules_upsert", time.perf_counter() - t0)
        raise_api_error(
            409,
            error="conflict",
            message="Rule was modified or already exists for this version",
        )
    admin_rules_write()
    record_route_latency("admin_access_rules_upsert", time.perf_counter() - t0)
    status_code = status.HTTP_201_CREATED if out.created else status.HTTP_200_OK
    return JSONResponse(
        status_code=status_code,
        content=build_success_response({"rule": out.rule.model_dump(mode="json")}),
    )
