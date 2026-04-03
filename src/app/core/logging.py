"""Structured logging setup, redaction, and business/technical log helpers."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

_SENSITIVE_KEYS = frozenset(
    {
        "access_token",
        "refresh_token",
        "password",
        "password_confirmation",
        "password_hash",
        "session_id",
        "authorization",
        "cookie",
        "secret",
        "jwt",
    }
)


def sanitize_log_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove or mask sensitive keys (recursive for nested dicts)."""
    out: dict[str, Any] = {}
    for key, value in payload.items():
        lk = key.lower()
        if lk in _SENSITIVE_KEYS or lk.endswith("_token") or lk.endswith("_secret"):
            out[key] = "[REDACTED]"
            continue
        if isinstance(value, dict):
            out[key] = sanitize_log_payload(value)
        elif isinstance(value, list):
            out[key] = [
                sanitize_log_payload(v) if isinstance(v, dict) else _maybe_redact_scalar(key, v)
                for v in value
            ]
        else:
            out[key] = _maybe_redact_scalar(key, value)
    return out


def _maybe_redact_scalar(parent_key: str, value: Any) -> Any:
    _ = parent_key
    return value


class _JsonLogFormatter(logging.Formatter):
    """One JSON object per line: time, level, logger, message."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(*, level: str) -> None:
    root = logging.getLogger("app")
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonLogFormatter())
    root.addHandler(handler)
    root.propagate = False

    for name in ("app.business", "app.technical"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.setLevel(root.level)
        lg.addHandler(handler)
        lg.propagate = False


def get_business_logger() -> logging.Logger:
    return logging.getLogger("app.business")


def get_technical_logger() -> logging.Logger:
    return logging.getLogger("app.technical")


def log_business_event(event: str, **fields: Any) -> None:
    payload = sanitize_log_payload({"event": event, **fields})
    get_business_logger().info(json.dumps(payload, ensure_ascii=False, default=str))


def log_technical(message: str, **fields: Any) -> None:
    payload = sanitize_log_payload({"message": message, **fields})
    get_technical_logger().error(json.dumps(payload, ensure_ascii=False, default=str))
