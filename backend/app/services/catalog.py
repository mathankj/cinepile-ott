"""
Catalog service — list / detail / search / filter for titles, seasons, episodes.

Only `published` (and not soft-deleted) titles are visible to non-admin callers.
On read, we auto-promote `scheduled → published` if publish_at has passed —
saves needing a background job for V1.5.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import String, and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.episode import Episode
from app.models.genre import Genre
from app.models.season import Season
from app.models.title import Title, titles_genres


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


async def auto_promote_scheduled(db: AsyncSession) -> int:
    """Flip status=scheduled → published for any titles whose publish_at has passed.
    Cheap and idempotent — call it at the top of list/detail reads."""
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

    stmt = select(Title).where(_published_filter())
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
    """Direct fetch — used by /v1/episodes/{id}/play."""
    ep = await db.get(Episode, episode_id)
    if ep is None or ep.status != "published":
        raise EpisodeNotFound
    return ep


async def search_titles(db: AsyncSession, *, q: str, limit: int = 30) -> list[Title]:
    """V1.5: LIKE-based; swap to Postgres tsvector when catalog scales."""
    if not q.strip():
        return []
    needle = f"%{q.strip().lower()}%"
    stmt = (
        select(Title)
        .where(
            _published_filter(),
            or_(
                func.lower(Title.title).like(needle),
                func.lower(Title.original_title).like(needle),
                func.lower(Title.synopsis).like(needle),
            ),
        )
        .limit(limit)
    )
    return list((await db.scalars(stmt)).unique().all())


async def list_genres(db: AsyncSession) -> list[Genre]:
    return list((await db.scalars(select(Genre).order_by(Genre.kind, Genre.name))).all())
