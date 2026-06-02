"""
Catalog service — list/get/search films and categories.
Pure logic, no FastAPI imports.
"""
from __future__ import annotations

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.film import Category, Film


class FilmNotFound(Exception):
    code = "film_not_found"
    message = "Film not found."


async def list_films(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    category_slug: str | None = None,
    sort: str = "-published_at",
) -> tuple[list[Film], int]:
    """Returns (items, total). Only `published` films are returned to the public."""
    base_q = select(Film).where(Film.status == "published", Film.deleted_at.is_(None))
    count_q = select(func.count()).select_from(Film).where(
        Film.status == "published", Film.deleted_at.is_(None)
    )

    if category_slug:
        base_q = base_q.join(Film.categories).where(Category.slug == category_slug)
        count_q = (
            select(func.count())
            .select_from(Film)
            .join(Film.categories)
            .where(
                and_(Film.status == "published", Film.deleted_at.is_(None), Category.slug == category_slug)
            )
        )

    # Tiny sort vocabulary — extend deliberately
    direction_desc = sort.startswith("-")
    field = sort.lstrip("-")
    sort_col = {
        "published_at": Film.published_at,
        "title": Film.title,
        "release_year": Film.release_year,
    }.get(field, Film.published_at)
    base_q = base_q.order_by(sort_col.desc() if direction_desc else sort_col.asc())

    page = max(1, page)
    page_size = max(1, min(100, page_size))
    base_q = base_q.offset((page - 1) * page_size).limit(page_size)

    items = (await db.scalars(base_q)).unique().all()
    total = (await db.scalar(count_q)) or 0
    return list(items), int(total)


async def get_by_id(db: AsyncSession, film_id: int) -> Film:
    film = await db.get(Film, film_id)
    if film is None or film.deleted_at is not None or film.status != "published":
        raise FilmNotFound
    return film


async def get_by_slug(db: AsyncSession, slug: str) -> Film:
    film = await db.scalar(
        select(Film).where(
            Film.slug == slug, Film.status == "published", Film.deleted_at.is_(None)
        )
    )
    if film is None:
        raise FilmNotFound
    return film


async def search(db: AsyncSession, *, query: str, limit: int = 30) -> list[Film]:
    """
    Phase 1: portable LIKE search (works on SQLite + Postgres).
    Phase 2 swap: when we move to Postgres-only prod, replace with tsvector match
    against Film.search_vector for better ranking. The wrapper signature stays the same.
    """
    if not query.strip():
        return []
    needle = f"%{query.strip().lower()}%"
    stmt = (
        select(Film)
        .where(
            Film.status == "published",
            Film.deleted_at.is_(None),
            or_(
                func.lower(Film.title).like(needle),
                func.lower(Film.original_title).like(needle),
                func.lower(Film.synopsis).like(needle),
            ),
        )
        .limit(limit)
    )
    return list((await db.scalars(stmt)).unique().all())


async def list_categories(db: AsyncSession) -> list[Category]:
    return list((await db.scalars(select(Category).order_by(Category.name))).all())
