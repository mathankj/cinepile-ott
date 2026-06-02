"""Catalog (titles + seasons + episodes + playback)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.title import (
    EpisodeRead,
    SeasonDetail,
    SeasonSummary,
    TitleDetail,
    TitleListResponse,
    TitleSummary,
    GenreRead,
)
from app.schemas.playback import PlaybackTicket
from app.services import catalog, playback

router = APIRouter()


def _err(exc, code: int) -> HTTPException:
    return HTTPException(
        status_code=code,
        detail={"error": {"code": exc.code, "message": exc.message}},
    )


def _title_to_detail(t) -> TitleDetail:
    """Project a Title ORM into the DetailSchema, including a SeasonSummary list."""
    season_summaries = [
        SeasonSummary(
            id=s.id,
            season_number=s.season_number,
            name=s.name,
            episode_count=len(s.episodes),
        )
        for s in (t.seasons if t.type == "series" else [])
    ]
    return TitleDetail.model_validate(t).model_copy(update={"seasons": season_summaries})


@router.get("", response_model=TitleListResponse)
async def list_titles(
    db: DbSession,
    type: str | None = Query(default=None, pattern="^(movie|series)$"),
    genre: str | None = None,
    language: str | None = None,
    country: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    sort: str = "-published_at",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> TitleListResponse:
    items, total = await catalog.list_titles(
        db,
        type_=type,
        genre_slug=genre,
        language=language,
        country=country,
        year_from=year_from,
        year_to=year_to,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return TitleListResponse(
        items=[TitleSummary.model_validate(t) for t in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/search", response_model=list[TitleSummary])
async def search_titles(db: DbSession, q: str = Query(min_length=1)) -> list[TitleSummary]:
    items = await catalog.search_titles(db, q=q)
    return [TitleSummary.model_validate(t) for t in items]


@router.get("/{title_id}", response_model=TitleDetail)
async def get_title(title_id: int, db: DbSession) -> TitleDetail:
    try:
        t = await catalog.get_title(db, title_id)
    except catalog.TitleNotFound as e:
        raise _err(e, 404) from e
    return _title_to_detail(t)


@router.get("/{title_id}/seasons/{season_number}", response_model=SeasonDetail)
async def get_season(title_id: int, season_number: int, db: DbSession) -> SeasonDetail:
    try:
        s = await catalog.get_season(db, title_id, season_number)
    except (catalog.TitleNotFound, catalog.SeasonNotFound) as e:
        raise _err(e, 404) from e
    return SeasonDetail.model_validate(s)


@router.get(
    "/{title_id}/seasons/{season_number}/episodes/{episode_number}",
    response_model=EpisodeRead,
)
async def get_episode(
    title_id: int, season_number: int, episode_number: int, db: DbSession
) -> EpisodeRead:
    try:
        ep = await catalog.get_episode(db, title_id, season_number, episode_number)
    except (catalog.TitleNotFound, catalog.SeasonNotFound, catalog.EpisodeNotFound) as e:
        raise _err(e, 404) from e
    return EpisodeRead.model_validate(ep)


@router.get("/{title_id}/play", response_model=PlaybackTicket)
async def play_movie(title_id: int, db: DbSession, user: CurrentUser) -> PlaybackTicket:
    try:
        title = await catalog.get_title(db, title_id)
    except catalog.TitleNotFound as e:
        raise _err(e, 404) from e
    if title.type != "movie":
        raise HTTPException(
            409,
            detail={"error": {"code": "type_mismatch", "message": "Use the episode playback endpoint for series."}},
        )
    try:
        ticket = await playback.issue_movie_ticket(db, user, title)
    except playback.NotEntitled as e:
        raise _err(e, status.HTTP_402_PAYMENT_REQUIRED) from e
    except playback.NoPlayableAsset as e:
        raise _err(e, 409) from e
    return PlaybackTicket(**ticket)
