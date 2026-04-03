"""TC-UNIT-01/02: request builders and envelope assertions."""

from __future__ import annotations

import pytest

from tests.helpers.assertions import assert_error_envelope, assert_success_envelope
from tests.helpers.request_builders import (
    build_login_payload,
    build_register_payload,
    build_upsert_access_rule_request,
)


def test_build_register_payload_defaults():
    payload = build_register_payload()
    assert payload["email"] == "user@example.com"
    assert payload["password"] == payload["password_confirmation"]


def test_build_login_payload_defaults():
    payload = build_login_payload()
    assert "email" in payload
    assert "password" in payload


def test_build_upsert_access_rule_request_shape():
    payload = build_upsert_access_rule_request(version=2, read=True)
    assert payload["version"] == 2
    assert payload["permissions"]["read"] is True


def test_assert_success_envelope_ok():
    assert_success_envelope({"data": {"id": "1"}})


def test_assert_success_envelope_rejects_tokens_at_root():
    with pytest.raises(AssertionError):
        assert_success_envelope({"data": {}, "access_token": "leak"})


def test_assert_error_envelope_ok():
    assert_error_envelope({"error": "unauthorized", "message": "nope", "request_id": "rid"})


def test_assert_error_envelope_rejects_missing_code():
    with pytest.raises(AssertionError):
        assert_error_envelope({"message": "m", "request_id": "r"})
