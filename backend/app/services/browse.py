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

from datetime import datetime, timedelta, timezone

from sqlalchemy import String, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.genre import Genre
from app.models.title import Title, titles_genres
from app.models.user import User
from app.models.watchlist import WatchlistItem
from app.models.watch_progress import WatchProgress
from app.services import history as history_svc


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
    """Returns a list of dicts: [{kind, title, items: [Title]}, ...]"""
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
