"""TC-UNIT-01/02: email normalization and refresh hash."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.config import load_settings
from app.core.security import (
    AccessTokenPayload,
    GenerateRefreshTokenInput,
    HashRefreshTokenInput,
    NormalizeEmailInput,
    build_access_token,
    generate_refresh_token,
    hash_refresh_token,
    normalize_email,
    parse_access_token,
    ParseAccessTokenInput,
)


def test_normalize_email_trims_and_lowercases():
    out = normalize_email(NormalizeEmailInput(email="  User@Example.COM \t"))
    assert out.email == "user@example.com"


def test_hash_refresh_token_is_deterministic():
    h1 = hash_refresh_token(HashRefreshTokenInput(token="same")).token_hash
    h2 = hash_refresh_token(HashRefreshTokenInput(token="same")).token_hash
    assert h1 == h2
    assert h1 != hash_refresh_token(HashRefreshTokenInput(token="other")).token_hash


def test_generate_refresh_token_has_entropy():
    a = generate_refresh_token(GenerateRefreshTokenInput()).token
    b = generate_refresh_token(GenerateRefreshTokenInput()).token
    assert a != b
    assert len(a) >= 32


def test_build_and_parse_access_token_roundtrip():
    settings = load_settings()
    uid = uuid4()
    sid = uuid4()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=15)
    out = build_access_token(
        AccessTokenPayload(user_id=uid, session_id=sid, issued_at=now, expires_at=exp),
        settings,
    )
    claims = parse_access_token(ParseAccessTokenInput(token=out.token, settings=settings))
    assert claims.user_id == uid
    assert claims.session_id == sid
