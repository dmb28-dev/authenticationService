"""Session/refresh SQL checks — run with APP_DATABASE_URL + migrations + seed."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("APP_DATABASE_URL"),
    reason="Set APP_DATABASE_URL to run integration tests",
)


def test_placeholder_integration_env():
    assert os.environ["APP_DATABASE_URL"]
