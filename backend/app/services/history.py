"""
Watch progress service — replaces V1's history.

Movies: one row per (user, title), episode_id = NULL.
Series: one row per (user, episode), title_id = the series.

Continue-watching collapses series rows back up to their parent title,
showing the most-recently-played episode as the resume target.
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.episode import Episode
from app.models.season import Season
from app.models.title import Title
from app.models.user import User
from app.models.watch_progress import WatchProgress

COMPLETION_THRESHOLD = 0.9


class NotPlayable(Exception):
    code = "not_playable"
    message = "Title or episode is not available."


async def _ensure_movie_playable(db: AsyncSession, title_id: int) -> Title:
    t = await db.get(Title, title_id)
    if t is None or t.deleted_at is not None or t.status != "published" or t.type != "movie":
        raise NotPlayable
    return t


async def _ensure_episode_playable(
    db: AsyncSession, episode_id: int
) -> tuple[Episode, Season, Title]:
    ep = await db.get(Episode, episode_id)
    if ep is None or ep.status != "published":
        raise NotPlayable
    season = await db.get(Season, ep.season_id)
    if season is None:
        raise NotPlayable
    title = await db.get(Title, season.title_id)
    if title is None or title.deleted_at is not None or title.status != "published":
        raise NotPlayable
    return ep, season, title


async def upsert_movie_progress(
    db: AsyncSession, user: User, *, title_id: int, position_sec: int, total_sec: int
) -> WatchProgress:
    await _ensure_movie_playable(db, title_id)
    now = datetime.now(tz=timezone.utc)
    completed = total_sec > 0 and (position_sec / total_sec) >= COMPLETION_THRESHOLD
    row = await db.scalar(
        select(WatchProgress).where(
            and_(
                WatchProgress.user_id == user.id,
                WatchProgress.title_id == title_id,
                WatchProgress.episode_id.is_(None),
            )
        )
    )
    if row is None:
        row = WatchProgress(
            user_id=user.id,
            title_id=title_id,
            episode_id=None,
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


async def upsert_episode_progress(
    db: AsyncSession, user: User, *, episode_id: int, position_sec: int, total_sec: int
) -> WatchProgress:
    ep, _, title = await _ensure_episode_playable(db, episode_id)
    now = datetime.now(tz=timezone.utc)
    completed = total_sec > 0 and (position_sec / total_sec) >= COMPLETION_THRESHOLD
    row = await db.scalar(
        select(WatchProgress).where(
            and_(
                WatchProgress.user_id == user.id,
                WatchProgress.title_id == title.id,
                WatchProgress.episode_id == ep.id,
            )
        )
    )
    if row is None:
        row = WatchProgress(
            user_id=user.id,
            title_id=title.id,
            episode_id=ep.id,
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


async def continue_watching(
    db: AsyncSession, user: User, *, limit: int = 20
) -> list[dict]:
    """
    Returns [{title, episode?, position_sec, total_sec, last_played_at}].
    For series: most-recent non-completed (or last completed if all done) episode
    per series, keyed by title_id.
    """
    stmt = (
        select(WatchProgress, Title, Episode, Season)
        .join(Title, Title.id == WatchProgress.title_id)
        .outerjoin(Episode, Episode.id == WatchProgress.episode_id)
        .outerjoin(Season, Season.id == Episode.season_id)
        .where(
            WatchProgress.user_id == user.id,
            Title.deleted_at.is_(None),
            Title.status == "published",
        )
        .order_by(WatchProgress.last_played_at.desc())
    )
    rows = (await db.execute(stmt)).all()

    # Group by title_id, keep first per title (already ordered by last_played desc)
    grouped: OrderedDict[int, dict] = OrderedDict()
    for wp, title, ep, season in rows:
        if title.id in grouped:
            continue
        grouped[title.id] = {
            "title": title,
            "episode_id": ep.id if ep else None,
            "episode_number": ep.episode_number if ep else None,
            "season_number": season.season_number if season else None,
            "episode_name": ep.name if ep else None,
            "position_sec": wp.position_sec,
            "total_sec": wp.total_sec,
            "last_played_at": wp.last_played_at,
        }
        if len(grouped) >= limit:
            break
    return list(grouped.values())


async def delete_title_progress(db: AsyncSession, user: User, *, title_id: int) -> int:
    """Clear all progress (movie + every series episode) for a title."""
    res = await db.execute(
        delete(WatchProgress).where(
            WatchProgress.user_id == user.id, WatchProgress.title_id == title_id
        )
    )
    return res.rowcount or 0


async def finished_title_ids(db: AsyncSession, user: User, *, limit: int = 3) -> list[int]:
    """The user's N most recently finished titles. Used by Because-You-Watched."""
    stmt = (
        select(WatchProgress.title_id, WatchProgress.last_played_at)
        .where(WatchProgress.user_id == user.id, WatchProgress.completed.is_(True))
        .order_by(WatchProgress.last_played_at.desc())
        .limit(limit)
    )
    # De-dup while preserving order (could be both movie + episode rows for same series)
    seen: list[int] = []
    for tid, _ in (await db.execute(stmt)).all():
        if tid not in seen:
            seen.append(tid)
        if len(seen) >= limit:
            break
    return seen
