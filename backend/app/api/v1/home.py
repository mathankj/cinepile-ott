"""GET /v1/home — returns rows of titles. Personalized when authenticated."""
from __future__ import annotations

import time

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserOptional, DbSession
from app.schemas.home import HomeResponse, HomeRow
from app.schemas.title import TitleSummary
from app.services import browse

router = APIRouter()

# Genres rarely change — cache for 5 minutes. Without this, every /browse
# render pays a cold Neon round-trip for the genres dropdown.
_GENRES_CACHE: tuple[list, float] | None = None
_GENRES_CACHE_TTL_SECONDS = 300


def invalidate_genres_cache() -> None:
    global _GENRES_CACHE
    _GENRES_CACHE = None


@router.get("", response_model=HomeResponse)
async def get_home(
    db: DbSession,
    user: CurrentUserOptional,
    country: str | None = Query(default=None, min_length=2, max_length=2),
) -> HomeResponse:
    rows = await browse.build_home(db, user, country=country)
    return HomeResponse(
        rows=[
            HomeRow(
                kind=r["kind"],
                title=r["title"],
                items=[TitleSummary.model_validate(t) for t in r["items"]],
            )
            for r in rows
        ]
    )


@router.get("/genres")
async def get_genres(db: DbSession):
    global _GENRES_CACHE
    from app.schemas.title import GenreRead
    from app.services import catalog

    now = time.monotonic()
    if _GENRES_CACHE and _GENRES_CACHE[1] > now:
        return _GENRES_CACHE[0]

    genres = await catalog.list_genres(db)
    result = [GenreRead.model_validate(g).model_dump() for g in genres]
    _GENRES_CACHE = (result, now + _GENRES_CACHE_TTL_SECONDS)
    return result
