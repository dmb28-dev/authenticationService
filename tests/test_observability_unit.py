"""TC-UNIT-01 (sanitize), TC-UNIT-02 (error envelope), TC-UNIT-03 (metrics)."""

from app.core.errors import build_error_response
from app.core.logging import sanitize_log_payload
from app.core.observability import auth_login_success, inc, reset_for_tests, snapshot


def test_sanitize_log_payload_redacts_secrets():
    raw = {
        "access_token": "x",
        "refresh_token": "y",
        "password_hash": "h",
        "session_id": "s",
        "nested": {"password": "p"},
    }
    out = sanitize_log_payload(raw)
    assert out["access_token"] == "[REDACTED]"
    assert out["refresh_token"] == "[REDACTED]"
    assert out["password_hash"] == "[REDACTED]"
    assert out["session_id"] == "[REDACTED]"
    assert out["nested"]["password"] == "[REDACTED]"


def test_build_error_response_includes_request_id():
    e = build_error_response(error="validation_error", message="bad", request_id="rid-1")
    assert e["request_id"] == "rid-1"
    assert e["error"] == "validation_error"


def test_metrics_increment():
    reset_for_tests()
    inc("test_metric", 2)
    auth_login_success()
    snap = snapshot()
    assert snap["counters"]["test_metric"] == 2
    assert snap["counters"]["auth_login_success"] == 1
    reset_for_tests()
