"""
User-personalized endpoints: continue-watching, watchlist, reactions, progress posts.
All under /v1/me/* or /v1/titles/{id}/progress + /v1/episodes/{id}/progress.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.reaction import (
    ContinueWatchingItem,
    ContinueWatchingList,
    ProgressUpdate,
    ReactionList,
    ReactionRead,
    ReactionWrite,
    WatchlistItemRead,
    WatchlistRead,
)
from app.schemas.title import TitleSummary
from app.services import history as history_svc
from app.services import reactions as reaction_svc
from app.services import watchlist as watchlist_svc

router = APIRouter()


def _err(exc, code: int) -> HTTPException:
    return HTTPException(
        status_code=code,
        detail={"error": {"code": exc.code, "message": exc.message}},
    )


# ---- Continue watching --------------------------------------------------------


@router.get("/me/continue-watching", response_model=ContinueWatchingList)
async def get_continue_watching(db: DbSession, user: CurrentUser) -> ContinueWatchingList:
    items = await history_svc.continue_watching(db, user)
    out = [
        ContinueWatchingItem(
            title=TitleSummary.model_validate(i["title"]),
            episode_id=i["episode_id"],
            episode_number=i["episode_number"],
            season_number=i["season_number"],
            episode_name=i["episode_name"],
            position_sec=i["position_sec"],
            total_sec=i["total_sec"],
            last_played_at=i["last_played_at"],
        )
        for i in items
    ]
    return ContinueWatchingList(items=out)


@router.delete("/me/continue-watching/{title_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_continue_watching(title_id: int, db: DbSession, user: CurrentUser) -> None:
    deleted = await history_svc.delete_title_progress(db, user, title_id=title_id)
    if deleted == 0:
        raise HTTPException(
            404,
            detail={"error": {"code": "not_found", "message": "No progress for that title."}},
        )


# ---- Movie + episode progress posts ------------------------------------------


@router.post("/titles/{title_id}/progress", status_code=status.HTTP_204_NO_CONTENT, tags=["history"])
async def post_movie_progress(
    title_id: int, payload: ProgressUpdate, db: DbSession, user: CurrentUser
) -> None:
    try:
        await history_svc.upsert_movie_progress(
            db, user, title_id=title_id, position_sec=payload.position_sec, total_sec=payload.total_sec
        )
    except history_svc.NotPlayable as e:
        raise _err(e, 404) from e


@router.post(
    "/episodes/{episode_id}/progress",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["history"],
)
async def post_episode_progress(
    episode_id: int, payload: ProgressUpdate, db: DbSession, user: CurrentUser
) -> None:
    try:
        await history_svc.upsert_episode_progress(
            db, user, episode_id=episode_id, position_sec=payload.position_sec, total_sec=payload.total_sec
        )
    except history_svc.NotPlayable as e:
        raise _err(e, 404) from e


# ---- Reactions ---------------------------------------------------------------


@router.put("/titles/{title_id}/reaction", tags=["reactions"])
async def set_reaction(
    title_id: int, payload: ReactionWrite, db: DbSession, user: CurrentUser
) -> dict:
    try:
        r = await reaction_svc.set_reaction(db, user, title_id=title_id, kind=payload.kind)
    except reaction_svc.TitleNotFound as e:
        raise _err(e, 404) from e
    except reaction_svc.InvalidReactionKind as e:
        raise _err(e, 422) from e
    return {"title_id": title_id, "kind": r.kind}


@router.delete("/titles/{title_id}/reaction", status_code=status.HTTP_204_NO_CONTENT, tags=["reactions"])
async def clear_reaction(title_id: int, db: DbSession, user: CurrentUser) -> None:
    await reaction_svc.clear_reaction(db, user, title_id=title_id)


@router.get("/me/reactions", response_model=ReactionList, tags=["reactions"])
async def list_my_reactions(db: DbSession, user: CurrentUser) -> ReactionList:
    items = await reaction_svc.list_reactions(db, user)
    return ReactionList(
        items=[
            ReactionRead(title=TitleSummary.model_validate(t), kind=r.kind, updated_at=r.updated_at)
            for r, t in items
        ]
    )


# ---- Watchlist (My List) -----------------------------------------------------


@router.post("/me/list/{title_id}", tags=["watchlist"])
async def add_to_watchlist(title_id: int, db: DbSession, user: CurrentUser) -> dict:
    try:
        _, created = await watchlist_svc.add(db, user, title_id=title_id)
    except watchlist_svc.TitleNotFound as e:
        raise _err(e, 404) from e
    return {"title_id": title_id, "added": created}


@router.delete("/me/list/{title_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["watchlist"])
async def remove_from_watchlist(title_id: int, db: DbSession, user: CurrentUser) -> None:
    deleted = await watchlist_svc.remove(db, user, title_id=title_id)
    if deleted == 0:
        raise HTTPException(
            404,
            detail={"error": {"code": "not_in_list", "message": "Title not in My List."}},
        )


@router.get("/me/list", response_model=WatchlistRead, tags=["watchlist"])
async def list_watchlist(db: DbSession, user: CurrentUser) -> WatchlistRead:
    items = await watchlist_svc.list_(db, user)
    return WatchlistRead(
        items=[
            WatchlistItemRead(title=TitleSummary.model_validate(t), added_at=w.added_at)
            for w, t in items
        ]
    )
