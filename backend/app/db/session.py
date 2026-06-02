"""
AsyncSession dependency.

Routes import `get_db` and FastAPI injects an open session per request,
closing it (and rolling back on error) when the request ends.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
