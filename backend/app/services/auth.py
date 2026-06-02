"""
Auth service — pure business logic. No FastAPI imports, no HTTPException.
Raises domain errors; the route layer maps them to HTTP responses.

Flow:
    signup     → create user → issue_token_pair (new family)
    login      → verify password → issue_token_pair (new family)
    refresh    → validate refresh → rotate within same family → issue new pair
    logout     → revoke entire family

Rotation detection: if a presented refresh token has already been revoked AND
its replaced_by row points elsewhere, that means somebody else used the new one
and now this one shouldn't exist — so we revoke the entire family. This is the
standard refresh-token-rotation-with-reuse-detection pattern.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User


# ---------- Domain errors (route layer maps these to HTTP codes) ----------


class AuthError(Exception):
    code: str = "auth_error"
    message: str = "Authentication failed."


class EmailAlreadyRegistered(AuthError):
    code = "email_already_registered"
    message = "An account with that email already exists."


class InvalidCredentials(AuthError):
    code = "invalid_credentials"
    message = "Email or password is incorrect."


class InvalidToken(AuthError):
    code = "invalid_token"
    message = "The provided token is invalid or expired."


class InactiveUser(AuthError):
    code = "inactive_user"
    message = "This account is inactive."


# ---------- Helpers ----------


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _as_utc(dt: datetime) -> datetime:
    """SQLite returns naive datetimes even for tz-aware columns.
    Treat naive values as UTC (which is how we always write them)."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


# ---------- Token issuance ----------


async def _issue_token_pair(
    db: AsyncSession, user: User, *, family_id: str | None = None
) -> tuple[str, str, datetime]:
    """Create an access+refresh pair and persist the refresh."""
    family = family_id or str(uuid.uuid4())
    access = create_access_token(
        subject=str(user.id),
        extra_claims={"sv": user.session_version, "role": user.role},
    )
    refresh, refresh_exp = create_refresh_token(subject=str(user.id), family_id=family)

    row = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(refresh),
        family_id=family,
        issued_at=datetime.now(tz=timezone.utc),
        expires_at=refresh_exp,
    )
    db.add(row)
    await db.flush()
    return access, refresh, refresh_exp


# ---------- Public service operations ----------


async def signup(db: AsyncSession, *, email: str, password: str, full_name: str | None) -> tuple[User, str, str, datetime]:
    email = _normalize_email(email)
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise EmailAlreadyRegistered

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role="user",
    )
    db.add(user)
    await db.flush()  # populates user.id

    access, refresh, refresh_exp = await _issue_token_pair(db, user)
    return user, access, refresh, refresh_exp


async def login(db: AsyncSession, *, email: str, password: str) -> tuple[User, str, str, datetime]:
    email = _normalize_email(email)
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentials
    if not user.is_active:
        raise InactiveUser

    access, refresh, refresh_exp = await _issue_token_pair(db, user)
    return user, access, refresh, refresh_exp


async def refresh(db: AsyncSession, *, refresh_token: str) -> tuple[User, str, str, datetime]:
    # 1) JWT shape/expiry sanity
    try:
        payload = decode_token(refresh_token)
    except TokenError as e:
        raise InvalidToken from e
    if payload.get("type") != "refresh":
        raise InvalidToken

    # 2) Look up by hash
    h = _hash_token(refresh_token)
    row = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == h))
    if row is None:
        raise InvalidToken

    # 3) Reuse detection: a revoked refresh being presented means someone
    # already rotated past it. Burn the whole family.
    # We commit immediately so this security-critical change persists even
    # though we're about to raise (the request transaction would otherwise
    # be rolled back by the per-request dependency).
    if row.revoked_at is not None:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == row.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(tz=timezone.utc))
        )
        await db.commit()
        raise InvalidToken

    # 4) Expiry safety net (jose checks exp too, but belt-and-braces)
    if _as_utc(row.expires_at) < datetime.now(tz=timezone.utc):
        raise InvalidToken

    user = await db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise InvalidToken

    # 5) Rotate: revoke this one, issue a new pair in the same family
    new_access, new_refresh, new_exp = await _issue_token_pair(db, user, family_id=row.family_id)
    new_row = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(new_refresh))
    )
    row.revoked_at = datetime.now(tz=timezone.utc)
    row.replaced_by_id = new_row.id if new_row else None

    return user, new_access, new_refresh, new_exp


async def logout_family(db: AsyncSession, *, refresh_token: str) -> None:
    """Revoke the family the refresh token belongs to. No-op on bad token."""
    try:
        payload = decode_token(refresh_token)
    except TokenError:
        return
    if payload.get("type") != "refresh":
        return
    family = payload.get("family")
    if not family:
        return
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(tz=timezone.utc))
    )
