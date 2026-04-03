from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import admin_access_rule_routes, auth_routes, mock_routes, profile_routes


def build_api_router() -> APIRouter:
    root = APIRouter()
    root.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
    root.include_router(profile_routes.router, prefix="/users", tags=["users"])
    root.include_router(mock_routes.router, prefix="/mock", tags=["mock"])
    root.include_router(
        admin_access_rule_routes.router,
        prefix="/admin/access-rules",
        tags=["admin-access-rules"],
    )
    return root
