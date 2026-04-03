"""TC-E2E-02: profile GET/PATCH/DELETE (stubs)."""

from __future__ import annotations

from tests.helpers.assertions import assert_success_envelope
from tests.helpers.request_builders import build_profile_patch_payload
from tests.helpers.stub_tokens import stub_authorization_headers


def test_profile_read_update_delete_smoke(client):
    headers = stub_authorization_headers()

    r = client.get("/api/v1/users/me", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert_success_envelope(body)

    r2 = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json=build_profile_patch_payload(),
    )
    assert r2.status_code == 200
    assert_success_envelope(r2.json())

    r3 = client.delete("/api/v1/users/me", headers=headers)
    assert r3.status_code == 204
