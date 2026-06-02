"""
Password hashing and JWT helpers.

Why bcrypt: industry standard, slow by design, no clever home-rolled crypto.
Why python-jose: maintained JOSE implementation, supports HS256 and asymmetric
algos when we move to RS256 later for multi-service deployments.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

# bcrypt has a hard 72-byte input limit. We pre-hash with SHA-256 (32 bytes)
# so users with very long passwords still get hashed correctly and we don't
# silently truncate. This is the same approach Django + many production apps use.
_BCRYPT_ROUNDS = 12  # ≈250ms on commodity hardware


def _prepare(password: str) -> bytes:
    import hashlib
    # SHA-256 → 32 bytes raw, well under bcrypt's 72-byte limit
    return hashlib.sha256(password.encode("utf-8")).digest()


def hash_password(plain: str) -> str:
    h = bcrypt.hashpw(_prepare(plain), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS))
    return h.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


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
    """Returns (token, expires_at). expires_at is also stored in DB for revocation.
    A random `jti` makes every issued token byte-distinct even within the same second."""
    import uuid as _uuid
    settings = get_settings()
    expires_at = _now_utc() + timedelta(days=settings.jwt_refresh_ttl_days)
    payload = {
        "sub": subject,
        "iat": _now_utc(),
        "exp": expires_at,
        "type": "refresh",
        "family": family_id,
        "jti": _uuid.uuid4().hex,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_token(token: str) -> dict[str, Any]:
    """Raises JWTError on invalid/expired tokens — callers should catch and 401."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


# Re-export for callers that want to catch decoding errors without importing jose directly
TokenError = JWTError
