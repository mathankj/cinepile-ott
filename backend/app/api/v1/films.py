"""Catalog + playback routes (public catalog + auth-protected playback)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.film import FilmDetail, FilmListResponse, FilmSummary
from app.schemas.playback import PlaybackTicket
from app.services import catalog, playback

router = APIRouter()


@router.get("", response_model=FilmListResponse)
async def list_films(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    sort: str = "-published_at",
) -> FilmListResponse:
    items, total = await catalog.list_films(
        db, page=page, page_size=page_size, category_slug=category, sort=sort
    )
    return FilmListResponse(
        items=[FilmSummary.model_validate(f) for f in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/search", response_model=list[FilmSummary])
async def search_films(db: DbSession, q: str = Query(min_length=1)) -> list[FilmSummary]:
    items = await catalog.search(db, query=q)
    return [FilmSummary.model_validate(f) for f in items]


@router.get("/{film_id}", response_model=FilmDetail)
async def get_film(film_id: int, db: DbSession) -> FilmDetail:
    try:
        film = await catalog.get_by_id(db, film_id)
    except catalog.FilmNotFound as e:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": e.code, "message": e.message}},
        ) from e
    return FilmDetail.model_validate(film)


@router.get("/{film_id}/play", response_model=PlaybackTicket)
async def play_film(film_id: int, db: DbSession, user: CurrentUser) -> PlaybackTicket:
    try:
        film = await catalog.get_by_id(db, film_id)
    except catalog.FilmNotFound as e:
        raise HTTPException(404, detail={"error": {"code": e.code, "message": e.message}}) from e

    try:
        ticket = await playback.issue_ticket(db, user, film)
    except playback.NotEntitled as e:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            detail={"error": {"code": e.code, "message": e.message}},
        ) from e
    except playback.NoPlayableAsset as e:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={"error": {"code": e.code, "message": e.message}},
        ) from e
    return PlaybackTicket(**ticket)
