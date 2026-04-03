"""TC-E2E-01: register → login → refresh → logout (stubs)."""

from __future__ import annotations

from tests.helpers.assertions import assert_success_envelope
from tests.helpers.request_builders import build_login_payload, build_register_payload
from tests.helpers.stub_tokens import STUB_REFRESH_TOKEN, stub_authorization_headers


def test_stub_user_lifecycle(client):
    r = client.post("/api/v1/auth/register", json=build_register_payload())
    assert r.status_code == 201
    body = r.json()
    assert_success_envelope(body)
    assert body["data"]["email"] == "user@example.com"

    r2 = client.post("/api/v1/auth/login", json=build_login_payload())
    assert r2.status_code == 200
    b2 = r2.json()
    assert_success_envelope(b2)
    assert b2["data"]["access_token"]
    assert b2["data"]["refresh_token"]

    r3 = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": STUB_REFRESH_TOKEN},
    )
    assert r3.status_code == 200
    b3 = r3.json()
    assert_success_envelope(b3)
    assert b3["data"]["access_token"]

    r4 = client.post(
        "/api/v1/auth/logout",
        headers=stub_authorization_headers(),
    )
    assert r4.status_code == 204
