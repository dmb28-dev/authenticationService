"""Access `AppSettings` from `app.state`."""

from __future__ import annotations

from fastapi import Request

from app.core.config import AppSettings


def get_app_settings(request: Request) -> AppSettings:
    return request.app.state.settings
