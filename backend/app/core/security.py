"""
Password hashing and JWT helpers.

Why bcrypt: industry standard, slow by design, no clever home-rolled crypto.
Why python-jose: maintained JOSE implementation, supports HS256 and asymmetric
algos when we move to RS256 later for multi-service deployments.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

# bcrypt with sensible defaults; rounds=12 ≈ 250ms on commodity hardware
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def create_access_token(*, subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": _now_utc(),
        "exp": _now_utc() + timedelta(minutes=settings.jwt_access_ttl_minutes),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(*, subject: str, family_id: str) -> tuple[str, datetime]:
    """Returns (token, expires_at). expires_at is also stored in DB for revocation."""
    settings = get_settings()
    expires_at = _now_utc() + timedelta(days=settings.jwt_refresh_ttl_days)
    payload = {
        "sub": subject,
        "iat": _now_utc(),
        "exp": expires_at,
        "type": "refresh",
        "family": family_id,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_token(token: str) -> dict[str, Any]:
    """Raises JWTError on invalid/expired tokens — callers should catch and 401."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


# Re-export for callers that want to catch decoding errors without importing jose directly
TokenError = JWTError
