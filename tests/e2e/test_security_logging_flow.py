"""TC-E2E-01/02: security-related logs and denials (stub mode)."""

from __future__ import annotations

import logging

from tests.helpers.request_builders import build_login_payload


def test_e2e_login_success_and_failure_logs(caplog, client):
    caplog.set_level("INFO", logger="app.business")
    biz = logging.getLogger("app.business")
    biz.addHandler(caplog.handler)
    try:
        r_ok = client.post("/api/v1/auth/login", json=build_login_payload())
        assert r_ok.status_code == 200
        assert any("auth.login.success" in r.message for r in caplog.records)

        caplog.clear()
        bad = dict(build_login_payload())
        bad["email"] = "bad@example.com"
        r_fail = client.post("/api/v1/auth/login", json=bad)
        assert r_fail.status_code == 401
        assert any("auth.login.failed" in r.message for r in caplog.records)
    finally:
        biz.removeHandler(caplog.handler)


def test_metrics_after_login(client):
    from app.core.observability import reset_for_tests, snapshot

    reset_for_tests()
    client.post("/api/v1/auth/login", json=build_login_payload())
    snap = snapshot()
    assert snap["counters"].get("auth_login_success", 0) >= 1
