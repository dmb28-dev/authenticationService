"""Health, readiness, metrics, request id headers."""

from __future__ import annotations

import pytest

from app.core.observability import reset_for_tests


@pytest.fixture(autouse=True)
def _reset_metrics():
    reset_for_tests()
    yield
    reset_for_tests()


def test_health_ready_metrics_request_id(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    r2 = client.get("/ready")
    assert r2.status_code == 503
    body = r2.json()
    assert body["status"] == "not_ready"

    r3 = client.get("/metrics")
    assert r3.status_code == 200
    assert "counters" in r3.json()

    r4 = client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert r4.headers.get("X-Request-ID") == "abc-123"
