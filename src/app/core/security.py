"""Security: email, Argon2id, JWT access (no role in token), opaque refresh + hash."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import AppSettings

_ph = PasswordHasher()

ACCESS_TOKEN_TYPE = "access"


def canonicalize_email(email: str) -> str:
    return email.strip().lower()


@dataclass(frozen=True)
class NormalizeEmailInput:
    email: str


@dataclass(frozen=True)
class NormalizedEmailOutput:
    email: str


def normalize_email(payload: NormalizeEmailInput) -> NormalizedEmailOutput:
    return NormalizedEmailOutput(email=canonicalize_email(payload.email))


@dataclass(frozen=True)
class HashPasswordInput:
    password: str


@dataclass(frozen=True)
class PasswordHashOutput:
    password_hash: str


def hash_password(payload: HashPasswordInput) -> PasswordHashOutput:
    return PasswordHashOutput(password_hash=_ph.hash(payload.password))


def verify_password(*, password_hash: str, password: str) -> bool:
    try:
        _ph.verify(password_hash, password)
        return True
    except VerifyMismatchError:
        return False


def stub_access_token() -> str:
    return "stub.access.jwt"


def stub_refresh_token() -> str:
    return "stub_refresh_opaque_token"


@dataclass(frozen=True)
class AccessTokenPayload:
    user_id: UUID
    session_id: UUID
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class AccessTokenOutput:
    token: str


def build_access_token(payload: AccessTokenPayload, settings: AppSettings) -> AccessTokenOutput:
    claims = {
        "sub": str(payload.user_id),
        "sid": str(payload.session_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": int(payload.issued_at.timestamp()),
        "exp": int(payload.expires_at.timestamp()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return AccessTokenOutput(token=token)


@dataclass(frozen=True)
class ParseAccessTokenInput:
    token: str
    settings: AppSettings


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: UUID
    session_id: UUID
    issued_at: datetime
    expires_at: datetime


def parse_access_token(payload: ParseAccessTokenInput) -> AccessTokenClaims:
    raw = jwt.decode(
        payload.token,
        payload.settings.jwt_secret,
        algorithms=[payload.settings.jwt_algorithm],
        audience=payload.settings.jwt_audience,
        issuer=payload.settings.jwt_issuer,
    )
    if raw.get("type") != ACCESS_TOKEN_TYPE:
        msg = "invalid access token type"
        raise jwt.InvalidTokenError(msg)
    user_id = UUID(raw["sub"])
    session_id = UUID(raw["sid"])
    iat = datetime.fromtimestamp(int(raw["iat"]), tz=timezone.utc)
    exp = datetime.fromtimestamp(int(raw["exp"]), tz=timezone.utc)
    return AccessTokenClaims(
        user_id=user_id,
        session_id=session_id,
        issued_at=iat,
        expires_at=exp,
    )


@dataclass(frozen=True)
class GenerateRefreshTokenInput:
    """Marker payload for refresh token generation (no fields)."""


@dataclass(frozen=True)
class RefreshTokenPlainOutput:
    token: str


def generate_refresh_token(_payload: GenerateRefreshTokenInput) -> RefreshTokenPlainOutput:
    # 256 bits random, url-safe opaque string
    return RefreshTokenPlainOutput(token=secrets.token_urlsafe(32))


@dataclass(frozen=True)
class HashRefreshTokenInput:
    token: str


@dataclass(frozen=True)
class RefreshTokenHashOutput:
    token_hash: str


def hash_refresh_token(payload: HashRefreshTokenInput) -> RefreshTokenHashOutput:
    digest = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    return RefreshTokenHashOutput(token_hash=digest)
