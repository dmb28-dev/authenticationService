"""TC-E2E-03 (mock slice): documents and reports (stubs)."""

from __future__ import annotations

from tests.helpers.assertions import assert_success_envelope
from tests.helpers.stub_tokens import stub_authorization_headers


def test_mock_documents_and_reports_smoke(client):
    headers = stub_authorization_headers()

    r = client.get("/api/v1/mock/documents", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "data" in body
    assert "meta" in body

    r2 = client.get("/api/v1/mock/documents/doc-1", headers=headers)
    assert r2.status_code == 200
    assert_success_envelope(r2.json())

    r3 = client.get("/api/v1/mock/reports", headers=headers)
    assert r3.status_code == 200
    b3 = r3.json()
    assert "data" in b3
    assert "meta" in b3
