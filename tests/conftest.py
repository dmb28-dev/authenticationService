"""Shared pytest fixtures and test client factories."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_application


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_application()) as test_client:
        yield test_client


def build_test_client() -> TestClient:
    return TestClient(create_application())


def build_stub_authorization_headers(*, admin: bool = False) -> dict[str, str]:
    from tests.helpers.stub_tokens import stub_authorization_headers

    return stub_authorization_headers(admin=admin)


def build_test_client_with_overrides(
    dependency_overrides: dict[Callable[..., object], Callable[..., object]],
) -> TestClient:
    return TestClient(create_application(dependency_overrides=dependency_overrides))
