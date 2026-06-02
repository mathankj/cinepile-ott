"""GET /v1/home — returns rows of titles. Personalized when authenticated."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserOptional, DbSession
from app.schemas.home import HomeResponse, HomeRow
from app.schemas.title import TitleSummary
from app.services import browse

router = APIRouter()


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
    from app.schemas.title import GenreRead
    from app.services import catalog

    genres = await catalog.list_genres(db)
    return [GenreRead.model_validate(g) for g in genres]
