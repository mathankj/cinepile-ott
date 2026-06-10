"""
Reusable FastAPI dependencies.

- get_db        : per-request AsyncSession
- get_current_user / get_current_user_optional : decodes Bearer JWT, loads user
- require_admin : role gate
- get_active_profile : resolves the X-Profile-Id header to a verified Profile
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenError, decode_token
from app.db.session import get_db as _get_db
from app.models.profile import Profile
from app.models.user import User
from app.services.profile import set_request_profile


async def get_db() -> AsyncIterator[AsyncSession]:
    async for s in _get_db():
        yield s


DbSession = Annotated[AsyncSession, Depends(get_db)]


def _unauthorized(code: str = "unauthorized", message: str = "Not authenticated.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": code, "message": message}},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden(message: str = "Admin role required.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": {"code": "forbidden", "message": message}},
    )


async def _user_from_bearer(authorization: str | None, db: AsyncSession) -> User | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    try:
        payload = decode_token(token)
    except TokenError:
        return None
    if payload.get("type") != "access":
        return None

    user_id_raw = payload.get("sub")
    if not user_id_raw:
        return None
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        return None

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        return None

    # session_version check — bump on User to invalidate all outstanding tokens
    if int(payload.get("sv", 0)) != user.session_version:
        return None

    return user


async def _resolve_active_profile(
    db: AsyncSession, user: User | None, x_profile_id: str | None
) -> Profile | None:
    """Maps the X-Profile-Id header to a Profile — or None.

    The header is client-supplied, so it is NEVER trusted on its own: a profile
    is only returned when it exists AND belongs to the authenticated user.
    Anything else (no header, garbage value, someone else's profile id) quietly
    degrades to None — i.e. the legacy "no profile" scope — rather than erroring,
    so stale localStorage on the frontend can't lock a user out.
    """
    if user is None or not x_profile_id:
        return None
    try:
        profile_id = int(x_profile_id)
    except (TypeError, ValueError):
        return None
    profile = await db.get(Profile, profile_id)
    if profile is None or profile.user_id != user.id:
        return None
    return profile


async def get_current_user(
    db: DbSession,
    authorization: str | None = Header(default=None),
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
) -> User:
    user = await _user_from_bearer(authorization, db)
    if user is None:
        raise _unauthorized()
    # Stash the verified active profile in a request-scoped ContextVar. Routes
    # we own take ActiveProfile explicitly; the /play routes (other branch)
    # can't — the playback service reads this stash instead. See
    # app/services/profile.py for the rationale.
    set_request_profile(await _resolve_active_profile(db, user, x_profile_id))
    return user


async def get_current_user_optional(
    db: DbSession,
    authorization: str | None = Header(default=None),
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
) -> User | None:
    user = await _user_from_bearer(authorization, db)
    set_request_profile(await _resolve_active_profile(db, user, x_profile_id))
    return user


async def get_active_profile(
    db: DbSession,
    authorization: str | None = Header(default=None),
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
) -> Profile | None:
    """Explicit dependency form of the active profile, for routes we own.

    Self-contained (re-reads the bearer + header) so it works regardless of
    whether the route also depends on get_current_user — the duplicate
    db.get() calls hit the session identity map, not the database.
    """
    user = await _user_from_bearer(authorization, db)
    return await _resolve_active_profile(db, user, x_profile_id)


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_admin():
        raise _forbidden()
    return user


async def require_content_role(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Allows admin or content_manager. The catalog-write boundary."""
    if user.role not in {"admin", "content_manager"}:
        raise _forbidden(message="content_manager or admin role required.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserOptional = Annotated[User | None, Depends(get_current_user_optional)]
ActiveProfile = Annotated[Profile | None, Depends(get_active_profile)]
AdminUser = Annotated[User, Depends(require_admin)]
ContentRoleUser = Annotated[User, Depends(require_content_role)]
