"""Deterministic stub Bearer values for smoke tests (stage 1.1 stubs)."""

# Matches `auth_service` / `dependencies.auth` stub behaviour: non-admin path.
STUB_ACCESS_TOKEN = "stub.access.jwt"
STUB_REFRESH_TOKEN = "stub_refresh_opaque_token"

# `get_current_principal` treats any token containing "admin" as admin.
STUB_ADMIN_BEARER = "stub.admin.jwt"


def stub_authorization_headers(*, admin: bool = False) -> dict[str, str]:
    token = STUB_ADMIN_BEARER if admin else STUB_ACCESS_TOKEN
    return {"Authorization": f"Bearer {token}"}
