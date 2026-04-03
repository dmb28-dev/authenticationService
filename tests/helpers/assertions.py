"""Shared checks for API envelope JSON (success and error)."""

from __future__ import annotations

from typing import Any


def assert_success_envelope(payload: dict[str, Any]) -> None:
    assert "data" in payload, "success response must contain a top-level 'data' key"
    assert "access_token" not in payload, "tokens must not appear at the root; use data.*"
    assert "refresh_token" not in payload, "tokens must not appear at the root; use data.*"


def assert_error_envelope(payload: dict[str, Any]) -> None:
    """Error body: `error` (code), `message`, `request_id`, optional `details`."""
    assert "error" in payload, "error response must contain 'error' (code)"
    assert isinstance(payload["error"], str)
    assert "message" in payload
    assert isinstance(payload["message"], str)
    assert "request_id" in payload
    assert isinstance(payload["request_id"], str)
    if "details" in payload and payload["details"] is not None:
        assert isinstance(payload["details"], list)
