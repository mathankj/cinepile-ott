"""
Catalog service — list / detail / search / filter for titles, seasons, episodes.

Only `published` (and not soft-deleted) titles are visible to non-admin callers.
On read, we auto-promote `scheduled → published` if publish_at has passed —
saves needing a background job for V1.5.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy import String, and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.episode import Episode
from app.models.genre import Genre
from app.models.season import Season
from app.models.title import Title, titles_genres

# List/search/row queries project into TitleSummary (scalar columns only).
# The Title model eager-loads 7 relationships via lazy="selectin" — right for
# the detail page (get_title / get_season keep it), wasteful here: without
# noload("*") every list query fans out into ~7 extra SELECTs nothing reads.
_SUMMARY_ONLY = noload("*")


class TitleNotFound(Exception):
    code = "title_not_found"
    message = "Title not found."


class SeasonNotFound(Exception):
    code = "season_not_found"
    message = "Season not found."


class EpisodeNotFound(Exception):
    code = "episode_not_found"
    message = "Episode not found."


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


# Throttle for auto_promote_scheduled: it used to run 2 UPDATE statements on
# EVERY uncached list/detail read, which on Neon means two extra round trips
# per request for a job that only matters around a publish_at boundary.
# Running it at most once per interval per process keeps scheduled publishes
# near-on-time (worst case: visible 30 s late) at ~zero per-request cost.
_PROMOTE_INTERVAL_SECONDS = 30.0
_last_promote_monotonic: float | None = None


def reset_promotion_throttle() -> None:
    """Allow the next read to run promotion immediately. Called after admin
    catalog writes (via invalidate_titles_cache) so a freshly-scheduled title
    with a past publish_at goes live on the very next read — and by tests,
    which assert promotion behaviour and must not inherit another test's
    throttle window."""
    global _last_promote_monotonic
    _last_promote_monotonic = None


async def auto_promote_scheduled(db: AsyncSession) -> int:
    """Flip status=scheduled → published for any titles whose publish_at has passed.
    Cheap and idempotent — called at the top of list/detail reads, but throttled
    to once per _PROMOTE_INTERVAL_SECONDS per process (see above)."""
    global _last_promote_monotonic
    mono = time.monotonic()
    if (
        _last_promote_monotonic is not None
        and mono - _last_promote_monotonic < _PROMOTE_INTERVAL_SECONDS
    ):
        return 0
    _last_promote_monotonic = mono

    now = _now()
    stmt = (
        update(Title)
        .where(
            Title.status == "scheduled",
            Title.publish_at.is_not(None),
            Title.publish_at <= now,
            Title.deleted_at.is_(None),
        )
        .values(status="published", published_at=now)
    )
    res = await db.execute(stmt)
    # Same for episodes
    stmt_ep = (
        update(Episode)
        .where(
            Episode.status == "scheduled",
            Episode.publish_at.is_not(None),
            Episode.publish_at <= now,
        )
        .values(status="published", published_at=now)
    )
    await db.execute(stmt_ep)
    return res.rowcount or 0


def _published_filter():
    return and_(Title.status == "published", Title.deleted_at.is_(None))


async def list_titles(
    db: AsyncSession,
    *,
    type_: str | None = None,           # 'movie' | 'series'
    genre_slug: str | None = None,
    language: str | None = None,        # original_language match
    country: str | None = None,         # any in countries[]
    year_from: int | None = None,
    year_to: int | None = None,
    sort: str = "-published_at",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Title], int]:
    await auto_promote_scheduled(db)

    stmt = select(Title).options(_SUMMARY_ONLY).where(_published_filter())
    count_stmt = select(func.count()).select_from(Title).where(_published_filter())

    if type_ in ("movie", "series"):
        stmt = stmt.where(Title.type == type_)
        count_stmt = count_stmt.where(Title.type == type_)
    if genre_slug:
        stmt = stmt.join(titles_genres).join(Genre).where(Genre.slug == genre_slug)
        count_stmt = count_stmt.join(titles_genres).join(Genre).where(Genre.slug == genre_slug)
    if language:
        stmt = stmt.where(Title.original_language == language)
        count_stmt = count_stmt.where(Title.original_language == language)
    if country:
        # JSON contains check — Postgres uses ?, SQLite uses LIKE on serialized text.
        # We keep it portable with a LIKE on the JSON serialization.
        stmt = stmt.where(func.cast(Title.countries, String).like(f'%"{country}"%'))
        count_stmt = count_stmt.where(func.cast(Title.countries, String).like(f'%"{country}"%'))
    if year_from is not None:
        stmt = stmt.where(Title.release_year >= year_from)
        count_stmt = count_stmt.where(Title.release_year >= year_from)
    if year_to is not None:
        stmt = stmt.where(Title.release_year <= year_to)
        count_stmt = count_stmt.where(Title.release_year <= year_to)

    # Sort vocabulary
    desc = sort.startswith("-")
    field = sort.lstrip("-")
    col = {
        "published_at": Title.published_at,
        "title": Title.title,
        "view_count": Title.view_count,
        "release_year": Title.release_year,
    }.get(field, Title.published_at)
    stmt = stmt.order_by(col.desc() if desc else col.asc(), Title.id.desc())

    page = max(1, page)
    page_size = max(1, min(100, page_size))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    items = (await db.scalars(stmt)).unique().all()
    total = (await db.scalar(count_stmt)) or 0
    return list(items), int(total)


async def get_title(db: AsyncSession, title_id: int) -> Title:
    await auto_promote_scheduled(db)
    t = await db.get(Title, title_id)
    if t is None or t.deleted_at is not None or t.status != "published":
        raise TitleNotFound
    return t


async def get_title_admin(db: AsyncSession, title_id: int) -> Title:
    """Admin/content-manager-scoped fetch. Returns drafts and scheduled titles
    too (everything except soft-deleted). Used by the title editor so admins
    can manage a title before it's published."""
    t = await db.get(Title, title_id)
    if t is None or t.deleted_at is not None:
        raise TitleNotFound
    return t


async def get_title_by_slug(db: AsyncSession, slug: str) -> Title:
    await auto_promote_scheduled(db)
    t = await db.scalar(
        select(Title).where(
            Title.slug == slug, Title.status == "published", Title.deleted_at.is_(None)
        )
    )
    if t is None:
        raise TitleNotFound
    return t


async def get_season(db: AsyncSession, title_id: int, season_number: int) -> Season:
    title = await get_title(db, title_id)
    if title.type != "series":
        raise SeasonNotFound
    s = await db.scalar(
        select(Season).where(Season.title_id == title.id, Season.season_number == season_number)
    )
    if s is None:
        raise SeasonNotFound
    return s


async def get_episode(
    db: AsyncSession, title_id: int, season_number: int, episode_number: int
) -> Episode:
    season = await get_season(db, title_id, season_number)
    ep = await db.scalar(
        select(Episode).where(
            Episode.season_id == season.id, Episode.episode_number == episode_number
        )
    )
    if ep is None or ep.status != "published":
        raise EpisodeNotFound
    return ep


async def get_episode_by_id(db: AsyncSession, episode_id: int) -> Episode:
    """Direct fetch — used by /v1/episodes/{id}/play.

    Verifies the episode is published AND its parent series is published-and-not-deleted.
    An episode of an archived/removed/soft-deleted series must not be playable, even
    if the episode itself still shows status='published'.
    """
    ep = await db.get(Episode, episode_id)
    if ep is None or ep.status != "published":
        raise EpisodeNotFound

    season = await db.get(Season, ep.season_id)
    if season is None:
        raise EpisodeNotFound
    title = await db.get(Title, season.title_id)
    if title is None or title.deleted_at is not None or title.status != "published":
        raise EpisodeNotFound
    return ep


_SEARCH_MAX_LEN = 100


def _escape_like(s: str) -> str:
    """Escape LIKE wildcards so user input doesn't act as a wildcard.
    Without this, q='%' matches every title — a real bug.
    The ESCAPE clause must match in the SQL below."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def search_titles(db: AsyncSession, *, q: str, limit: int = 30) -> list[Title]:
    """V1.5: LIKE-based; swap to Postgres tsvector when catalog scales."""
    q = (q or "").strip()
    if not q:
        return []
    # Cap query length to prevent DoS via huge regex-like input
    if len(q) > _SEARCH_MAX_LEN:
        q = q[:_SEARCH_MAX_LEN]
    needle = f"%{_escape_like(q.lower())}%"
    stmt = (
        select(Title)
        .options(_SUMMARY_ONLY)
        .where(
            _published_filter(),
            or_(
                func.lower(Title.title).like(needle, escape="\\"),
                func.lower(Title.original_title).like(needle, escape="\\"),
                func.lower(Title.synopsis).like(needle, escape="\\"),
            ),
        )
        .limit(limit)
    )
    return list((await db.scalars(stmt)).unique().all())


async def similar_titles(db: AsyncSession, title_id: int, *, limit: int = 20) -> list[Title]:
    """Titles sharing at least one genre with the given title — the "More Like
    This" rail on a detail page. Public surface: the seed must be a published,
    non-deleted title (404 otherwise, same rule as the detail endpoint), and
    results are restricted the same way. Ordered by view_count desc so the
    rail leads with what people actually watch."""
    seed = await db.get(Title, title_id)
    if seed is None or seed.deleted_at is not None or seed.status != "published":
        raise TitleNotFound

    seed_genre_ids = (
        await db.scalars(
            select(titles_genres.c.genre_id).where(titles_genres.c.title_id == title_id)
        )
    ).all()
    if not seed_genre_ids:
        return []

    # distinct() dedupes in SQL (a title matching 2 shared genres would
    # otherwise occupy 2 of the LIMIT slots before Python-side .unique()).
    stmt = (
        select(Title)
        .options(_SUMMARY_ONLY)
        .join(titles_genres, titles_genres.c.title_id == Title.id)
        .where(
            _published_filter(),
            titles_genres.c.genre_id.in_(seed_genre_ids),
            Title.id != title_id,
        )
        .order_by(Title.view_count.desc(), Title.id.desc())
        .distinct()
        .limit(limit)
    )
    return list((await db.scalars(stmt)).unique().all())


async def list_genres(db: AsyncSession) -> list[Genre]:
    return list((await db.scalars(select(Genre).order_by(Genre.kind, Genre.name))).all())


async def list_coming_soon(db: AsyncSession, *, limit: int = 20) -> list[Title]:
    """Titles in 'scheduled' status with a future publish_at — soonest first."""
    now = _now()
    stmt = (
        select(Title)
        .options(_SUMMARY_ONLY)
        .where(
            Title.status == "scheduled",
            Title.deleted_at.is_(None),
            Title.publish_at.is_not(None),
            Title.publish_at > now,
        )
        .order_by(Title.publish_at.asc())
        .limit(limit)
    )
    return list((await db.scalars(stmt)).unique().all())
