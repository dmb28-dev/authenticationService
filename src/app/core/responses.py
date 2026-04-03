from __future__ import annotations

from typing import Any


def build_success_response(data: Any) -> dict[str, Any]:
    return {"data": data}


def build_list_response(
    data: list[Any],
    *,
    limit: int,
    offset: int,
    total: int,
) -> dict[str, Any]:
    return {
        "data": data,
        "meta": {"limit": limit, "offset": offset, "total": total},
    }
