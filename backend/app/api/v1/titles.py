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


import time

# In-process TTL cache for the public catalog list endpoint. Same pattern as
# the home-page cache in browse.py — Neon free-tier cold-start makes a fresh
# query take 5-30 s, so users navigating between Movies/TV Shows/genre
# filters were watching "Loading…" stay on screen forever. Cached values
# are invalidated by admin writes (publish/archive/delete) — see
# invalidate_titles_cache() at the bottom of this file.
_TITLES_CACHE: dict[tuple, tuple[dict, float]] = {}
# Bumped from 60s → 300s. Catalog list is read constantly while users browse;
# 5 minutes of staleness is acceptable for a demo and cuts Neon hits by 5x.
_TITLES_CACHE_TTL_SECONDS = 300

# Per-title detail cache (used by title detail page + season pages). Without
# this, every click into a movie/series detail page or season hit Neon fresh,
# costing 3-10 s on cold compute. Keyed by title_id (and season_number for
# seasons). Invalidated together with the list cache on admin writes.
_TITLE_DETAIL_CACHE: dict[int, tuple[dict, float]] = {}
_SEASON_DETAIL_CACHE: dict[tuple[int, int], tuple[dict, float]] = {}
# "More Like This" rail, keyed by (title_id, limit). Same TTL + invalidation.
_SIMILAR_CACHE: dict[tuple[int, int], tuple[list[dict], float]] = {}

# Hard cap per cache dict. Cache keys come from request parameters (filters,
# pages, title ids), so a crawler iterating filter combinations would grow
# these dicts forever. When full we evict the oldest insertion (dicts keep
# insertion order) — a cheap FIFO that's plenty for short-TTL caches.
_CACHE_MAX_ENTRIES = 512


def _cache_put(cache: dict, key, value) -> None:
    """Insert into a TTL cache dict, evicting the oldest entry at the cap."""
    if key not in cache and len(cache) >= _CACHE_MAX_ENTRIES:
        cache.pop(next(iter(cache)))
    cache[key] = value


def invalidate_titles_cache() -> None:
    """Drop ALL list + detail + similar responses. Called from admin endpoints
    that mutate the catalog (publish, archive, delete, create) so admins don't
    see stale data immediately after a write."""
    _TITLES_CACHE.clear()
    _TITLE_DETAIL_CACHE.clear()
    _SEASON_DETAIL_CACHE.clear()
    _SIMILAR_CACHE.clear()
    # A catalog write may have scheduled (or re-scheduled) a title; clearing
    # the promotion throttle lets the next read auto-promote immediately
    # instead of waiting out the 30 s window.
    catalog.reset_promotion_throttle()


@router.get("", response_model=TitleListResponse)
async def list_titles(
    db: DbSession,
    type: str | None = Query(default=None, pattern="^(movie|series)$"),
    genre: str | None = None,
    language: str | None = None,
    # ISO 3166-1 alpha-2 only — this value reaches a LIKE pattern in the
    # service, so we constrain its shape at the HTTP boundary.
    country: str | None = Query(default=None, min_length=2, max_length=2),
    year_from: int | None = None,
    year_to: int | None = None,
    sort: str = Query(
        "-published_at",
        pattern=r"^-?(published_at|title|view_count|release_year)$",
        description="Sort key. Prefix with '-' for descending.",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> TitleListResponse:
    cache_key = (type, genre, language, country, year_from, year_to, sort, page, page_size)
    now = time.monotonic()
    cached = _TITLES_CACHE.get(cache_key)
    if cached and cached[1] > now:
        return TitleListResponse.model_validate(cached[0])

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
    response = TitleListResponse(
        items=[TitleSummary.model_validate(t) for t in items],
        page=page,
        page_size=page_size,
        total=total,
    )
    _cache_put(_TITLES_CACHE, cache_key, (response.model_dump(), now + _TITLES_CACHE_TTL_SECONDS))
    return response


@router.get("/coming-soon", response_model=list[TitleSummary])
async def coming_soon(
    db: DbSession,
    limit: int = Query(20, ge=1, le=100),
) -> list[TitleSummary]:
    """Titles scheduled for future publish. Public — these are marketing.
    Ordered by publish_at ASC (soonest first)."""
    items = await catalog.list_coming_soon(db, limit=limit)
    return [TitleSummary.model_validate(t) for t in items]


@router.get("/search", response_model=list[TitleSummary])
async def search_titles(db: DbSession, q: str = Query(min_length=1)) -> list[TitleSummary]:
    items = await catalog.search_titles(db, q=q)
    return [TitleSummary.model_validate(t) for t in items]


@router.get("/{title_id}", response_model=TitleDetail)
async def get_title(title_id: int, db: DbSession) -> TitleDetail:
    now = time.monotonic()
    cached = _TITLE_DETAIL_CACHE.get(title_id)
    if cached and cached[1] > now:
        return TitleDetail.model_validate(cached[0])
    try:
        t = await catalog.get_title(db, title_id)
    except catalog.TitleNotFound as e:
        raise _err(e, 404) from e
    detail = _title_to_detail(t)
    _cache_put(_TITLE_DETAIL_CACHE, title_id, (detail.model_dump(), now + _TITLES_CACHE_TTL_SECONDS))
    return detail


@router.get("/{title_id}/seasons/{season_number}", response_model=SeasonDetail)
async def get_season(title_id: int, season_number: int, db: DbSession) -> SeasonDetail:
    key = (title_id, season_number)
    now = time.monotonic()
    cached = _SEASON_DETAIL_CACHE.get(key)
    if cached and cached[1] > now:
        return SeasonDetail.model_validate(cached[0])
    try:
        s = await catalog.get_season(db, title_id, season_number)
    except (catalog.TitleNotFound, catalog.SeasonNotFound) as e:
        raise _err(e, 404) from e
    detail = SeasonDetail.model_validate(s)
    _cache_put(_SEASON_DETAIL_CACHE, key, (detail.model_dump(), now + _TITLES_CACHE_TTL_SECONDS))
    return detail


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


@router.get("/{title_id}/similar", response_model=list[TitleSummary])
async def similar_titles(
    title_id: int,
    db: DbSession,
    limit: int = Query(20, ge=1, le=40),
) -> list[TitleSummary]:
    """"More Like This" — public like the trailer endpoint (it's marketing:
    shown on detail pages before login). Published, non-deleted titles sharing
    at least one genre with this one, busiest first."""
    key = (title_id, limit)
    now = time.monotonic()
    cached = _SIMILAR_CACHE.get(key)
    if cached and cached[1] > now:
        return [TitleSummary.model_validate(item) for item in cached[0]]
    try:
        items = await catalog.similar_titles(db, title_id, limit=limit)
    except catalog.TitleNotFound as e:
        raise _err(e, 404) from e
    summaries = [TitleSummary.model_validate(t) for t in items]
    _cache_put(
        _SIMILAR_CACHE,
        key,
        ([s.model_dump() for s in summaries], now + _TITLES_CACHE_TTL_SECONDS),
    )
    return summaries


@router.get("/{title_id}/trailer")
async def get_trailer(title_id: int, db: DbSession) -> dict:
    """Public trailer URL — no auth, no subscription required.

    Returns 404 if no trailer asset exists. Returns a resolved URL (presigned
    if stored privately, full URL if already public).
    """
    try:
        title = await catalog.get_title(db, title_id)
    except catalog.TitleNotFound as e:
        raise _err(e, 404) from e

    from app.services import storage as storage_svc

    # Prefer a TitleAsset of kind='trailer'; fall back to title.trailer_url field
    asset = next((a for a in title.assets if a.kind == "trailer"), None)
    if asset is not None:
        return {
            "title_id": title.id,
            "trailer_url": storage_svc.resolve_url(asset.storage_url),
            "source": "asset",
        }
    if title.trailer_url:
        return {
            "title_id": title.id,
            "trailer_url": storage_svc.resolve_url(title.trailer_url),
            "source": "field",
        }
    raise HTTPException(
        404,
        detail={"error": {"code": "no_trailer", "message": "This title has no trailer configured."}},
    )


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
    # Ticket issuance bumps view_count; drop this title's cached detail so the
    # bump is visible. One key per play — the rest of the cache survives.
    _TITLE_DETAIL_CACHE.pop(title_id, None)
    return PlaybackTicket(**ticket)
