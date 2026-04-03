"""E2E auth with real DB — enable APP_DATABASE_URL, migrate, seed."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("APP_DATABASE_URL"),
    reason="Set APP_DATABASE_URL to run real auth e2e",
)


def test_placeholder_real_db_env():
    assert os.environ["APP_DATABASE_URL"]
