"""Typical HTTP JSON bodies for API smoke tests."""

from __future__ import annotations

from typing import Any


def build_register_payload(
    *,
    email: str = "user@example.com",
    password: str = "password12",
    first_name: str = "Ivan",
    last_name: str = "Ivanov",
    middle_name: str | None = "Ivanovich",
) -> dict[str, Any]:
    return {
        "first_name": first_name,
        "last_name": last_name,
        "middle_name": middle_name,
        "email": email,
        "password": password,
        "password_confirmation": password,
    }


def build_login_payload(*, email: str = "user@example.com", password: str = "password12") -> dict[str, Any]:
    return {"email": email, "password": password}


def build_profile_patch_payload(
    *,
    first_name: str = "Patched",
    last_name: str = "User",
    middle_name: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"first_name": first_name, "last_name": last_name}
    if middle_name is not None:
        body["middle_name"] = middle_name
    return body


def build_upsert_access_rule_request(
    *,
    version: int = 1,
    read: bool = True,
    read_all: bool = False,
    create: bool = False,
    update: bool = False,
    update_all: bool = False,
    delete: bool = False,
    delete_all: bool = False,
) -> dict[str, Any]:
    return {
        "version": version,
        "permissions": {
            "read": read,
            "read_all": read_all,
            "create": create,
            "update": update,
            "update_all": update_all,
            "delete": delete,
            "delete_all": delete_all,
        },
    }
