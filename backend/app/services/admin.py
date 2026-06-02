"""Admin service — film create/update/soft-delete + user listing."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.film import Category, Film, FilmAsset
from app.models.user import User


class SlugInUse(Exception):
    code = "slug_in_use"
    message = "Another film already uses that slug."


class FilmNotFound(Exception):
    code = "film_not_found"
    message = "Film not found."


async def _resolve_categories(db: AsyncSession, slugs: list[str]) -> list[Category]:
    if not slugs:
        return []
    stmt = select(Category).where(Category.slug.in_(slugs))
    return list((await db.scalars(stmt)).all())


async def create_film(db: AsyncSession, payload: dict) -> Film:
    existing = await db.scalar(select(Film).where(Film.slug == payload["slug"]))
    if existing is not None:
        raise SlugInUse

    category_slugs = payload.pop("category_slugs", []) or []
    hls_url = payload.pop("hls_manifest_url", None)

    film = Film(**payload)
    if film.status == "published" and film.published_at is None:
        film.published_at = datetime.now(tz=timezone.utc)
    film.categories = await _resolve_categories(db, category_slugs)
    db.add(film)
    await db.flush()

    if hls_url:
        db.add(FilmAsset(film_id=film.id, kind="hls_manifest", storage_url=hls_url))
        await db.flush()

    # Always refresh relationships so the response serializer doesn't trigger
    # a lazy load after the session is committed and closed.
    await db.refresh(film, attribute_names=["assets", "categories"])
    return film


async def update_film(db: AsyncSession, film_id: int, patch: dict) -> Film:
    film = await db.get(Film, film_id)
    if film is None or film.deleted_at is not None:
        raise FilmNotFound

    category_slugs = patch.pop("category_slugs", None)
    hls_url = patch.pop("hls_manifest_url", None)

    for k, v in patch.items():
        if v is not None:
            setattr(film, k, v)

    if film.status == "published" and film.published_at is None:
        film.published_at = datetime.now(tz=timezone.utc)

    if category_slugs is not None:
        film.categories = await _resolve_categories(db, category_slugs)

    if hls_url is not None:
        # Replace the existing hls_manifest asset (one per film for now)
        for a in list(film.assets):
            if a.kind == "hls_manifest":
                await db.delete(a)
        db.add(FilmAsset(film_id=film.id, kind="hls_manifest", storage_url=hls_url))

    await db.flush()
    await db.refresh(film, attribute_names=["assets", "categories"])
    return film


async def soft_delete_film(db: AsyncSession, film_id: int) -> None:
    film = await db.get(Film, film_id)
    if film is None or film.deleted_at is not None:
        raise FilmNotFound
    film.deleted_at = datetime.now(tz=timezone.utc)
    await db.flush()


async def list_users(db: AsyncSession, *, page: int = 1, page_size: int = 50) -> tuple[list[User], int]:
    page = max(1, page)
    page_size = max(1, min(200, page_size))
    items = list(
        (
            await db.scalars(
                select(User).order_by(User.id).offset((page - 1) * page_size).limit(page_size)
            )
        ).all()
    )
    total = (await db.scalar(select(func.count()).select_from(User))) or 0
    return items, int(total)
