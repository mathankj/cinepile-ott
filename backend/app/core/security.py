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

# bcrypt has a hard 72-byte input limit. We pre-hash with SHA-256 so users
# with very long passwords still get hashed correctly and we don't silently
# truncate. This is the same approach Django + many production apps use.
_BCRYPT_ROUNDS = 12  # ≈250ms on commodity hardware


def _prepare(password: str) -> bytes:
    """Current scheme: sha256 HEX digest → 64 ascii bytes (under bcrypt's 72).

    Why hexdigest and not the raw digest: bcrypt (the C implementation)
    truncates its input at the first NUL byte, and a raw sha256 digest
    contains 0x00 about 12% of the time — those passwords were silently
    losing entropy. Hex output is guaranteed NUL-free.
    """
    import hashlib

    return hashlib.sha256(password.encode("utf-8")).hexdigest().encode("ascii")


def _prepare_legacy(password: str) -> bytes:
    """Legacy scheme (pre null-byte fix): raw sha256 digest bytes.
    Kept ONLY so existing stored hashes keep verifying; new hashes never
    use this. Rows are transparently rehashed on next successful login."""
    import hashlib

    return hashlib.sha256(password.encode("utf-8")).digest()


def hash_password(plain: str) -> str:
    h = bcrypt.hashpw(_prepare(plain), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS))
    return h.decode("utf-8")


def verify_password_detailed(plain: str, hashed: str) -> tuple[bool, bool]:
    """Returns (is_valid, needs_rehash).

    Tries the current (hexdigest) scheme first, then falls back to the legacy
    raw-digest scheme. A match on the legacy scheme is still a valid login but
    signals the caller to rehash with the current scheme.
    """
    try:
        hashed_bytes = hashed.encode("utf-8")
        if bcrypt.checkpw(_prepare(plain), hashed_bytes):
            return True, False
        if bcrypt.checkpw(_prepare_legacy(plain), hashed_bytes):
            return True, True
        return False, False
    except (ValueError, TypeError):
        return False, False


def verify_password(plain: str, hashed: str) -> bool:
    valid, _ = verify_password_detailed(plain, hashed)
    return valid


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


# ---- Checkout tokens --------------------------------------------------------
#
# The dev /test-checkout page needs *some* credential in its URL so it can call
# POST /v1/payments/verify after Razorpay Checkout succeeds. Putting the user's
# real access token in a URL leaks it (browser history, server logs, Referer).
# Instead we mint a single-purpose token: short TTL, scoped to one order, and
# useless for any other endpoint.

CHECKOUT_TOKEN_TTL_MINUTES = 10


def create_checkout_token(*, user_id: int, subscription_id: int, order_id: str) -> str:
    """Short-lived token embedded in the dev checkout_url. Only good for
    verifying THIS order's payment — nothing else accepts purpose='checkout'."""
    settings = get_settings()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "purpose": "checkout",
        "subscription_id": subscription_id,
        "order_id": order_id,
        "iat": _now_utc(),
        "exp": _now_utc() + timedelta(minutes=CHECKOUT_TOKEN_TTL_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_checkout_token(token: str) -> dict[str, Any]:
    """Decode + enforce purpose='checkout'. Raises JWTError otherwise, so a
    user access token pasted into a checkout URL is rejected outright."""
    payload = decode_token(token)
    if payload.get("purpose") != "checkout":
        raise JWTError("Not a checkout token.")
    return payload


# Re-export for callers that want to catch decoding errors without importing jose directly
TokenError = JWTError
