"""In-process metrics, latency aggregates, readiness probe."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from threading import Lock
from typing import Any

import asyncpg

_lock = Lock()
_counters: dict[str, int] = defaultdict(int)
_latency_sum_s: dict[str, float] = defaultdict(float)
_latency_count: dict[str, int] = defaultdict(int)


def reset_for_tests() -> None:
    """Clear all metrics (tests only)."""
    with _lock:
        _counters.clear()
        _latency_sum_s.clear()
        _latency_count.clear()


def inc(metric: str, value: int = 1) -> None:
    with _lock:
        _counters[metric] += value


def record_route_latency(route_key: str, duration_s: float) -> None:
    with _lock:
        _latency_sum_s[route_key] += duration_s
        _latency_count[route_key] += 1


def snapshot() -> dict[str, Any]:
    with _lock:
        lat: dict[str, dict[str, float]] = {}
        for key in set(_latency_sum_s) | set(_latency_count):
            n = _latency_count.get(key, 0)
            total = _latency_sum_s.get(key, 0.0)
            lat[key] = {"count": float(n), "duration_s_sum": total}
        return {"counters": dict(_counters), "latency": lat}


async def check_database_ready(
    pool: asyncpg.Pool | None,
    *,
    timeout_ms: int,
) -> tuple[bool, str | None]:
    if pool is None:
        return False, "pool_unavailable"
    timeout = max(0.001, timeout_ms / 1000.0)
    try:
        async with asyncio.timeout(timeout):
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
    except TimeoutError:
        return False, "timeout"
    except Exception as e:
        return False, type(e).__name__
    return True, None


# Auth / mock / admin convenience wrappers
def auth_login_success() -> None:
    inc("auth_login_success")


def auth_login_failure() -> None:
    inc("auth_login_failure")


def auth_refresh_success() -> None:
    inc("auth_refresh_success")


def auth_refresh_failure() -> None:
    inc("auth_refresh_failure")


def auth_refresh_reuse() -> None:
    inc("auth_refresh_reuse")


def auth_logout() -> None:
    inc("auth_logout")


def mock_http(code: int, business_element: str) -> None:
    inc(f"mock_http_{code}_{business_element}")


def admin_rules_read() -> None:
    inc("admin_access_rules_read")


def admin_rules_write() -> None:
    inc("admin_access_rules_write")


def admin_rules_conflict() -> None:
    inc("admin_access_rules_conflict")
