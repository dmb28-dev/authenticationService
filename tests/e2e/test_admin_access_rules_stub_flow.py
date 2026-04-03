"""TC-E2E-03 (admin slice): access rules list + upsert (stubs)."""

from __future__ import annotations

from uuid import UUID

from tests.helpers.assertions import assert_success_envelope
from tests.helpers.request_builders import build_upsert_access_rule_request
from tests.helpers.stub_tokens import stub_authorization_headers


def test_admin_access_rules_list_and_upsert_smoke(client):
    admin_headers = stub_authorization_headers(admin=True)

    r = client.get("/api/v1/admin/access-rules", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert "data" in body
    assert "matrix" in body
    assert "meta" in body

    role_id = UUID("10000000-0000-4000-8000-000000000001")
    r2 = client.put(
        f"/api/v1/admin/access-rules/{role_id}/documents",
        headers=admin_headers,
        json=build_upsert_access_rule_request(version=1),
    )
    assert r2.status_code == 200
    assert_success_envelope(r2.json())
    assert "rule" in r2.json()["data"]
