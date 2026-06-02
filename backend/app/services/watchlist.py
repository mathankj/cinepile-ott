"""My List — per-user watchlist of titles."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.title import Title
from app.models.user import User
from app.models.watchlist import WatchlistItem


class TitleNotFound(Exception):
    code = "title_not_found"
    message = "Title not found."


async def add(db: AsyncSession, user: User, *, title_id: int) -> tuple[WatchlistItem, bool]:
    """Returns (item, created). created=True on first add, False if already present."""
    title = await db.get(Title, title_id)
    if title is None or title.deleted_at is not None or title.status != "published":
        raise TitleNotFound

    row = await db.scalar(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user.id, WatchlistItem.title_id == title_id
        )
    )
    if row is not None:
        return row, False
    row = WatchlistItem(
        user_id=user.id, title_id=title_id, added_at=datetime.now(tz=timezone.utc)
    )
    db.add(row)
    await db.flush()
    return row, True


async def remove(db: AsyncSession, user: User, *, title_id: int) -> int:
    res = await db.execute(
        delete(WatchlistItem).where(
            WatchlistItem.user_id == user.id, WatchlistItem.title_id == title_id
        )
    )
    return res.rowcount or 0


async def list_(db: AsyncSession, user: User, *, limit: int = 50) -> list[tuple[WatchlistItem, Title]]:
    stmt = (
        select(WatchlistItem, Title)
        .join(Title, Title.id == WatchlistItem.title_id)
        .where(
            WatchlistItem.user_id == user.id,
            Title.deleted_at.is_(None),
            Title.status == "published",
        )
        .order_by(WatchlistItem.added_at.desc())
        .limit(limit)
    )
    return [(w, t) for w, t in (await db.execute(stmt)).all()]
