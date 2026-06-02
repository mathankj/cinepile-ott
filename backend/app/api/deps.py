"""
Reusable FastAPI dependencies.

- get_db        : per-request AsyncSession
- get_current_user / get_current_user_optional : decodes Bearer JWT, loads user
- require_admin : role gate
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenError, decode_token
from app.db.session import get_db as _get_db
from app.models.user import User


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


async def get_current_user(
    db: DbSession,
    authorization: str | None = Header(default=None),
) -> User:
    user = await _user_from_bearer(authorization, db)
    if user is None:
        raise _unauthorized()
    return user


async def get_current_user_optional(
    db: DbSession,
    authorization: str | None = Header(default=None),
) -> User | None:
    return await _user_from_bearer(authorization, db)


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
AdminUser = Annotated[User, Depends(require_admin)]
ContentRoleUser = Annotated[User, Depends(require_content_role)]
