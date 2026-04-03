"""TC-UNIT-01, TC-UNIT-02 (task 1.1)."""

import pytest
from pydantic import ValidationError

from app.core.errors import build_error_response
from app.core.responses import build_success_response
from app.schemas.auth_schemas import RegisterUserInput


def test_register_user_input_validation():
    RegisterUserInput(
        first_name="A",
        last_name="B",
        email="a@b.com",
        password="password12",
        password_confirmation="password12",
    )
    with pytest.raises(ValidationError):
        RegisterUserInput(
            first_name="A",
            last_name="B",
            email="not-an-email",
            password="password12",
            password_confirmation="password12",
        )


def test_envelope_success_and_error():
    s = build_success_response({"id": "1"})
    assert s == {"data": {"id": "1"}}

    e = build_error_response(error="validation_error", message="bad", details=[{"field": "x"}])
    assert e["error"] == "validation_error"
    assert e["message"] == "bad"
    assert "request_id" in e
