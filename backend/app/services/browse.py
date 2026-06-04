"""
Browse / home rows.

V1.5 uses simple heuristics — no ML rankers. Each row is built from a
purpose-shaped query. The API contract returns the same row shape as a Netflix
home page so the frontend can render them uniformly.

Rows considered:
- continue_watching
- my_list
- new_releases     (published in last 30 days)
- trending_now     (top view_count over last 7 days — proxied by raw view_count for V1.5)
- top_in_country   (top view_count, country-filtered)
- because_you_watched:{seed_id}  (titles sharing a genre with a recently-finished title)
- genre:{slug}     (one row per user's top genre)

Order of returned rows is fixed for V1.5. Per-user row selection is V2.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import String, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.genre import Genre
from app.models.reaction import Reaction
from app.models.title import Title, titles_genres
from app.models.user import User
from app.models.watchlist import WatchlistItem
from app.models.watch_progress import WatchProgress
from app.services import history as history_svc


# Per-process TTL cache for /v1/home. Each entry is keyed by
# (user_id_or_none, country) and holds (rows, expires_at). On a cold Neon
# connection the home page does 5-10 sequential round trips that add up to
# 15-30 s — caching for 60 s means the first visit pays once and every
# subsequent visit by anyone (or by the same user+country) is sub-100 ms.
# This is the same trick Netflix uses (their home is cached server-side too).
_HOME_CACHE: dict[tuple[int | None, str | None], tuple[list[dict], float]] = {}
_HOME_CACHE_TTL_SECONDS = 60
_HOME_CACHE_LOCK = asyncio.Lock()  # avoid stampede when many requests miss simultaneously


def invalidate_home_cache(user_id: int | None = None) -> None:
    """Drops cache entries — call after writes that change what a user sees on
    home (e.g. add-to-list, reaction, finish watching). When user_id is None,
    drops EVERYTHING (use after admin publish/unpublish)."""
    if user_id is None:
        _HOME_CACHE.clear()
        return
    for key in [k for k in _HOME_CACHE if k[0] == user_id]:
        _HOME_CACHE.pop(key, None)


ROW_DEFAULT_CAP = 20


def _published_filter():
    return and_(Title.status == "published", Title.deleted_at.is_(None))


async def _new_releases(db: AsyncSession, *, days: int = 30, limit: int = ROW_DEFAULT_CAP) -> list[Title]:
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)
    stmt = (
        select(Title)
        .where(_published_filter(), Title.published_at.is_not(None), Title.published_at >= since)
        .order_by(Title.published_at.desc())
        .limit(limit)
    )
    return list((await db.scalars(stmt)).unique().all())


async def _trending(db: AsyncSession, *, limit: int = ROW_DEFAULT_CAP) -> list[Title]:
    """V1.5: use raw view_count as a proxy for trending.
    V2 will move to a windowed sum from a daily metrics table."""
    stmt = (
        select(Title)
        .where(_published_filter())
        .order_by(Title.view_count.desc(), Title.id.desc())
        .limit(limit)
    )
    return list((await db.scalars(stmt)).unique().all())


async def _top_in_country(db: AsyncSession, country: str, *, limit: int = 10) -> list[Title]:
    if not country:
        return []
    stmt = (
        select(Title)
        .where(
            _published_filter(),
            func.cast(Title.countries, String).like(f'%"{country}"%'),
        )
        .order_by(Title.view_count.desc())
        .limit(limit)
    )
    return list((await db.scalars(stmt)).unique().all())


async def _because_you_watched(
    db: AsyncSession, seed_title_id: int, *, exclude_title_ids: set[int], limit: int = ROW_DEFAULT_CAP
) -> list[Title]:
    """Titles sharing at least one genre with the seed, excluding seed + already-watched."""
    seed_genre_ids = (
        await db.scalars(
            select(titles_genres.c.genre_id).where(titles_genres.c.title_id == seed_title_id)
        )
    ).all()
    if not seed_genre_ids:
        return []

    stmt = (
        select(Title)
        .join(titles_genres, titles_genres.c.title_id == Title.id)
        .where(
            _published_filter(),
            titles_genres.c.genre_id.in_(seed_genre_ids),
            Title.id != seed_title_id,
            *([Title.id.notin_(exclude_title_ids)] if exclude_title_ids else []),
        )
        .order_by(Title.view_count.desc(), Title.id.desc())
        .limit(limit)
    )
    # distinct on id to avoid dupes when multiple genres match
    return list((await db.scalars(stmt)).unique().all())


async def _user_top_genres(db: AsyncSession, user: User, *, limit: int = 3) -> list[Genre]:
    """Genres the user has watched most (by play count, not weighted by duration)."""
    stmt = (
        select(Genre, func.count(WatchProgress.id).label("plays"))
        .join(titles_genres, titles_genres.c.genre_id == Genre.id)
        .join(Title, Title.id == titles_genres.c.title_id)
        .join(WatchProgress, WatchProgress.title_id == Title.id)
        .where(WatchProgress.user_id == user.id)
        .group_by(Genre.id)
        .order_by(func.count(WatchProgress.id).desc())
        .limit(limit)
    )
    return [g for g, _ in (await db.execute(stmt)).all()]


async def _titles_by_genre(
    db: AsyncSession, genre_id: int, *, limit: int = ROW_DEFAULT_CAP
) -> list[Title]:
    stmt = (
        select(Title)
        .join(titles_genres, titles_genres.c.title_id == Title.id)
        .where(_published_filter(), titles_genres.c.genre_id == genre_id)
        .order_by(Title.view_count.desc(), Title.id.desc())
        .limit(limit)
    )
    return list((await db.scalars(stmt)).unique().all())


async def recommended_for_you(
    db: AsyncSession, user: User, *, limit: int = ROW_DEFAULT_CAP
) -> list[Title]:
    """Lightweight recommendations.

    Seeds (in priority order):
      1. Titles the user thumbed UP via reactions
      2. Titles the user added to their watchlist
      3. Titles the user has any watch progress on (finished or in-flight)

    For each seed we pull the genre IDs and find titles sharing genre, excluding
    the seeds themselves. Order: view_count desc, then id desc as a tiebreaker.

    Returns [] for users with NO seeds — caller decides whether to fall back
    to globally popular content. This deliberately under-reports rather than
    hallucinate a recommendation when we have nothing to base it on.
    """
    # Seed IDs from positive reactions, watchlist, and watch progress. Valid
    # reaction kinds are thumbs_down / thumbs_up / double_thumbs_up — there is
    # no "like" kind (that was a bug; we now correctly include both positive
    # signals).
    liked_ids = list(
        (
            await db.scalars(
                select(Reaction.title_id).where(
                    Reaction.user_id == user.id,
                    Reaction.kind.in_(("thumbs_up", "double_thumbs_up")),
                )
            )
        ).all()
    )
    list_ids = list(
        (
            await db.scalars(
                select(WatchlistItem.title_id).where(WatchlistItem.user_id == user.id)
            )
        ).all()
    )
    progress_ids = list(
        (
            await db.scalars(
                select(WatchProgress.title_id)
                .where(WatchProgress.user_id == user.id)
                .order_by(WatchProgress.updated_at.desc())
                .limit(10)
            )
        ).all()
    )
    seed_ids = {*liked_ids, *list_ids, *progress_ids}
    if not seed_ids:
        return []

    # Genres of all seed titles
    genre_ids = list(
        (
            await db.scalars(
                select(titles_genres.c.genre_id)
                .where(titles_genres.c.title_id.in_(seed_ids))
                .distinct()
            )
        ).all()
    )
    if not genre_ids:
        return []

    # Titles sharing a genre, excluding seeds themselves. The distinct() avoids
    # the same title appearing twice when it matches two seed genres.
    stmt = (
        select(Title)
        .join(titles_genres, titles_genres.c.title_id == Title.id)
        .where(
            _published_filter(),
            titles_genres.c.genre_id.in_(genre_ids),
            Title.id.notin_(seed_ids),
        )
        .order_by(Title.view_count.desc(), Title.id.desc())
        .limit(limit)
    )
    return list((await db.scalars(stmt)).unique().all())


async def _my_list_titles(db: AsyncSession, user: User, *, limit: int = 50) -> list[Title]:
    stmt = (
        select(Title)
        .join(WatchlistItem, WatchlistItem.title_id == Title.id)
        .where(_published_filter(), WatchlistItem.user_id == user.id)
        .order_by(WatchlistItem.added_at.desc())
        .limit(limit)
    )
    return list((await db.scalars(stmt)).unique().all())


async def build_home(
    db: AsyncSession,
    user: User | None,
    *,
    country: str | None = None,
) -> list[dict]:
    """Returns a list of dicts: [{kind, title, items: [Title]}, ...]

    Cached per (user_id, country) for 60 s. The lock prevents thundering-herd
    rebuilds when many requests miss the cache simultaneously."""
    cache_key = (user.id if user else None, country)
    now = time.monotonic()
    cached = _HOME_CACHE.get(cache_key)
    if cached and cached[1] > now:
        return cached[0]

    async with _HOME_CACHE_LOCK:
        # Double-check: someone may have populated it while we waited on the lock.
        cached = _HOME_CACHE.get(cache_key)
        if cached and cached[1] > time.monotonic():
            return cached[0]
        rows = await _build_home_uncached(db, user, country=country)
        _HOME_CACHE[cache_key] = (rows, time.monotonic() + _HOME_CACHE_TTL_SECONDS)
        return rows


async def _build_home_uncached(
    db: AsyncSession,
    user: User | None,
    *,
    country: str | None = None,
) -> list[dict]:
    rows: list[dict] = []

    if user is not None:
        cw = await history_svc.continue_watching(db, user)
        if cw:
            rows.append(
                {
                    "kind": "continue_watching",
                    "title": "Continue Watching",
                    "items": [c["title"] for c in cw],
                }
            )

        my_list_items = await _my_list_titles(db, user)
        if my_list_items:
            rows.append({"kind": "my_list", "title": "My List", "items": my_list_items})

        # Recommendations row — fires whenever the user has ANY signal (reaction,
        # watchlist, progress). Stronger than "Because you watched" because it
        # doesn't require a FINISHED watch.
        recs = await recommended_for_you(db, user)
        if recs:
            rows.append({"kind": "recommended", "title": "Recommended for You", "items": recs})

    rows.append({"kind": "new_releases", "title": "New Releases", "items": await _new_releases(db)})
    rows.append({"kind": "trending_now", "title": "Trending Now", "items": await _trending(db)})

    if country:
        rows.append(
            {
                "kind": "top_in_country",
                "title": f"Top 10 in {country}",
                "items": await _top_in_country(db, country),
            }
        )

    if user is not None:
        finished = await history_svc.finished_title_ids(db, user)
        watched_ids: set[int] = set(finished)
        for seed_id in finished[:2]:  # cap at 2 BYW rows
            # find the seed title's name for the row label
            seed_title = await db.get(Title, seed_id)
            label = (
                f"Because You Watched {seed_title.title}" if seed_title is not None else "Because You Watched"
            )
            byw_items = await _because_you_watched(db, seed_id, exclude_title_ids=watched_ids)
            if byw_items:
                rows.append(
                    {"kind": f"because_you_watched:{seed_id}", "title": label, "items": byw_items}
                )

        # User's top genres
        for g in await _user_top_genres(db, user):
            items = await _titles_by_genre(db, g.id)
            if items:
                rows.append({"kind": f"genre:{g.slug}", "title": g.name, "items": items})

    return rows
