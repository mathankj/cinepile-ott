"""
Watch progress service — replaces V1's history.

Movies: one row per (user, profile, title), episode_id = NULL.
Series: one row per (user, profile, episode), title_id = the series.

Continue-watching collapses series rows back up to their parent title,
showing the most-recently-played episode as the resume target.

Every function takes the active `profile` (None = legacy/no-header scope) and
filters via profile_scope() so each profile keeps a fully separate history.
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.episode import Episode
from app.models.profile import Profile
from app.models.season import Season
from app.models.title import Title
from app.models.user import User
from app.models.watch_progress import WatchProgress
from app.services.profile import profile_scope

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


def _bust_home(user_id: int) -> None:
    """Lazy import to avoid a circular dep: browse imports from history, so
    history can't import browse at module load."""
    from app.services.browse import invalidate_home_cache

    invalidate_home_cache(user_id)


async def upsert_movie_progress(
    db: AsyncSession,
    user: User,
    *,
    title_id: int,
    position_sec: int,
    total_sec: int,
    profile: Profile | None = None,
) -> WatchProgress:
    await _ensure_movie_playable(db, title_id)
    now = datetime.now(tz=timezone.utc)
    completed = total_sec > 0 and (position_sec / total_sec) >= COMPLETION_THRESHOLD
    row = await db.scalar(
        select(WatchProgress).where(
            and_(
                WatchProgress.user_id == user.id,
                profile_scope(WatchProgress.profile_id, profile),
                WatchProgress.title_id == title_id,
                WatchProgress.episode_id.is_(None),
            )
        )
    )
    if row is None:
        row = WatchProgress(
            user_id=user.id,
            profile_id=profile.id if profile else None,
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
        # Un-hide on resume — if the user comes back to watch, surface it again
        row.hidden_from_continue = False
    await db.flush()
    _bust_home(user.id)  # Continue-Watching row depends on this
    return row


async def upsert_episode_progress(
    db: AsyncSession,
    user: User,
    *,
    episode_id: int,
    position_sec: int,
    total_sec: int,
    profile: Profile | None = None,
) -> WatchProgress:
    ep, _, title = await _ensure_episode_playable(db, episode_id)
    now = datetime.now(tz=timezone.utc)
    completed = total_sec > 0 and (position_sec / total_sec) >= COMPLETION_THRESHOLD
    row = await db.scalar(
        select(WatchProgress).where(
            and_(
                WatchProgress.user_id == user.id,
                profile_scope(WatchProgress.profile_id, profile),
                WatchProgress.title_id == title.id,
                WatchProgress.episode_id == ep.id,
            )
        )
    )
    if row is None:
        row = WatchProgress(
            user_id=user.id,
            profile_id=profile.id if profile else None,
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
        # Un-hide on resume — if the user comes back to watch, surface it again
        row.hidden_from_continue = False
    await db.flush()
    _bust_home(user.id)  # Continue-Watching row depends on this
    return row


async def continue_watching(
    db: AsyncSession, user: User, *, limit: int = 20, profile: Profile | None = None
) -> list[dict]:
    """
    Returns [{title, episode?, position_sec, total_sec, last_played_at}].

    Filters applied:
      - title must be published and not soft-deleted
      - row not hidden via "Remove from Continue Watching"
      - row not completed (completed titles move to a separate "Watch Again" row)

    For series: most-recent in-progress episode per series, keyed by title_id.
    """
    stmt = (
        select(WatchProgress, Title, Episode, Season)
        .join(Title, Title.id == WatchProgress.title_id)
        .outerjoin(Episode, Episode.id == WatchProgress.episode_id)
        .outerjoin(Season, Season.id == Episode.season_id)
        .where(
            WatchProgress.user_id == user.id,
            profile_scope(WatchProgress.profile_id, profile),
            WatchProgress.hidden_from_continue.is_(False),
            WatchProgress.completed.is_(False),
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


async def hide_title_from_continue(
    db: AsyncSession, user: User, *, title_id: int, profile: Profile | None = None
) -> int:
    """
    "Remove from Continue Watching" — soft-hide, don't hard-delete.
    The row stays so if the user searches the title later and resumes, their
    position is intact. This is Netflix's documented behaviour.
    Scoped: hiding on one profile must not hide it for the others.
    """
    from sqlalchemy import update as sa_update

    res = await db.execute(
        sa_update(WatchProgress)
        .where(
            WatchProgress.user_id == user.id,
            profile_scope(WatchProgress.profile_id, profile),
            WatchProgress.title_id == title_id,
        )
        .values(hidden_from_continue=True)
    )
    return res.rowcount or 0


# Backward-compat alias used by older code; behavior is now soft-hide.
delete_title_progress = hide_title_from_continue


async def list_full_history(
    db: AsyncSession,
    user: User,
    *,
    page: int = 1,
    page_size: int = 20,
    profile: Profile | None = None,
) -> tuple[list[tuple[WatchProgress, Title]], int]:
    """
    Full viewing history — all titles the user has ever pressed play on.
    Differs from continue_watching() which filters to in-progress + visible.
    Returns finished, paused, AND hidden-from-continue rows so the user can
    review and manage their full activity (Netflix's "Viewing Activity" feature).
    """
    from sqlalchemy import func

    page = max(1, page)
    page_size = max(1, min(100, page_size))

    base_where = [
        WatchProgress.user_id == user.id,
        profile_scope(WatchProgress.profile_id, profile),
        Title.deleted_at.is_(None),
    ]

    # For series, multiple episode-rows roll up to one history entry per title.
    # We pick the most-recent row per title (Postgres DISTINCT ON could help; for
    # portability we do it in Python after fetching with ORDER BY last_played_at).
    stmt = (
        select(WatchProgress, Title)
        .join(Title, Title.id == WatchProgress.title_id)
        .where(*base_where)
        .order_by(WatchProgress.last_played_at.desc())
    )
    rows = (await db.execute(stmt)).all()

    seen_titles: set[int] = set()
    deduped: list[tuple[WatchProgress, Title]] = []
    for wp, t in rows:
        if t.id in seen_titles:
            continue
        seen_titles.add(t.id)
        deduped.append((wp, t))

    total = len(deduped)
    start = (page - 1) * page_size
    return deduped[start : start + page_size], total


async def remove_from_history(
    db: AsyncSession, user: User, *, title_id: int, profile: Profile | None = None
) -> int:
    """Hard-delete every WatchProgress row for (user, profile, title) — the user
    genuinely doesn't want any record of this title on this profile. Different
    from hide_title_from_continue() which is soft-hide for the continue-watching
    row. Scoped: wiping history on one profile leaves the others intact."""
    res = await db.execute(
        delete(WatchProgress).where(
            WatchProgress.user_id == user.id,
            profile_scope(WatchProgress.profile_id, profile),
            WatchProgress.title_id == title_id,
        )
    )
    return res.rowcount or 0


async def finished_title_ids(
    db: AsyncSession, user: User, *, limit: int = 3, profile: Profile | None = None
) -> list[int]:
    """The profile's N most recently finished titles. Used by Because-You-Watched."""
    stmt = (
        select(WatchProgress.title_id, WatchProgress.last_played_at)
        .where(
            WatchProgress.user_id == user.id,
            profile_scope(WatchProgress.profile_id, profile),
            WatchProgress.completed.is_(True),
        )
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
