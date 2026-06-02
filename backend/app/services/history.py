"""Watch-history service — record progress, list continue-watching, delete."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.film import Film
from app.models.user import User
from app.models.watch_history import WatchHistory

COMPLETION_THRESHOLD = 0.9


async def upsert_progress(
    db: AsyncSession,
    user: User,
    *,
    film_id: int,
    position_sec: int,
    total_sec: int,
) -> WatchHistory:
    # Make sure film exists & is published; raises if not (kept inline to avoid circular import)
    film = await db.get(Film, film_id)
    if film is None or film.deleted_at is not None or film.status != "published":
        raise FilmNotWatchable

    now = datetime.now(tz=timezone.utc)
    row = await db.scalar(
        select(WatchHistory).where(
            and_(WatchHistory.user_id == user.id, WatchHistory.film_id == film_id)
        )
    )
    completed = total_sec > 0 and (position_sec / total_sec) >= COMPLETION_THRESHOLD

    if row is None:
        row = WatchHistory(
            user_id=user.id,
            film_id=film_id,
            position_sec=position_sec,
            total_sec=total_sec,
            completed=completed,
            last_played_at=now,
        )
        db.add(row)
    else:
        row.position_sec = position_sec
        row.total_sec = total_sec
        row.completed = completed
        row.last_played_at = now
    await db.flush()
    return row


async def list_continue_watching(
    db: AsyncSession, user: User, *, limit: int = 30
) -> list[tuple[WatchHistory, Film]]:
    stmt = (
        select(WatchHistory, Film)
        .join(Film, Film.id == WatchHistory.film_id)
        .where(
            WatchHistory.user_id == user.id,
            Film.deleted_at.is_(None),
            Film.status == "published",
        )
        .order_by(WatchHistory.last_played_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [(wh, film) for wh, film in rows]


async def delete_entry(db: AsyncSession, user: User, *, film_id: int) -> bool:
    res = await db.execute(
        delete(WatchHistory).where(
            WatchHistory.user_id == user.id, WatchHistory.film_id == film_id
        )
    )
    return res.rowcount > 0


class FilmNotWatchable(Exception):
    code = "film_not_found"
    message = "Film not available."
