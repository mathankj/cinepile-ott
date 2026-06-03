"""
User-personalized endpoints: continue-watching, watchlist, reactions, progress posts.
All under /v1/me/* or /v1/titles/{id}/progress + /v1/episodes/{id}/progress.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.profile import (
    ProfileCreate,
    ProfileList,
    ProfileRead,
    ProfileUpdate,
)
from app.schemas.reaction import (
    ContinueWatchingItem,
    ContinueWatchingList,
    HistoryItem,
    HistoryList,
    ProgressUpdate,
    ReactionList,
    ReactionRead,
    ReactionWrite,
    WatchlistItemRead,
    WatchlistRead,
)
from app.schemas.title import TitleSummary
from app.services import browse as browse_svc
from app.services import history as history_svc
from app.services import profile as profile_svc
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
    """Soft-hide from Continue Watching. Row stays so progress is preserved if
    the user comes back via search/deep-link."""
    deleted = await history_svc.hide_title_from_continue(db, user, title_id=title_id)
    if deleted == 0:
        raise HTTPException(
            404,
            detail={"error": {"code": "not_found", "message": "No progress for that title."}},
        )


# ---- Full viewing history ----------------------------------------------------


@router.get("/me/history", response_model=HistoryList, tags=["history"])
async def get_history(
    db: DbSession,
    user: CurrentUser,
    page: int = 1,
    page_size: int = 20,
) -> HistoryList:
    """All titles the user has watched or paused — paginated, newest first.

    Includes:
      - in-progress titles (also visible in /me/continue-watching)
      - completed titles (no longer in continue-watching)
      - titles hidden from continue-watching

    Distinct from /me/continue-watching which is the curated feed.
    """
    from app.schemas.title import TitleSummary

    items, total = await history_svc.list_full_history(db, user, page=page, page_size=page_size)
    return HistoryList(
        items=[
            HistoryItem(
                title=TitleSummary.model_validate(t),
                position_sec=wp.position_sec,
                total_sec=wp.total_sec,
                completed=wp.completed,
                hidden_from_continue=wp.hidden_from_continue,
                last_played_at=wp.last_played_at,
            )
            for wp, t in items
        ],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.delete("/me/history/{title_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["history"])
async def delete_history(title_id: int, db: DbSession, user: CurrentUser) -> None:
    """Hard-delete every WatchProgress row for this title for the current user.

    Different from DELETE /me/continue-watching/{id} (which soft-hides):
    this one is "make this title disappear from my account entirely".
    """
    deleted = await history_svc.remove_from_history(db, user, title_id=title_id)
    if deleted == 0:
        raise HTTPException(
            404,
            detail={"error": {"code": "not_found", "message": "No history for that title."}},
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


# ---- Recommendations ----------------------------------------------------------


@router.get("/me/recommendations", response_model=list[TitleSummary], tags=["recommendations"])
async def my_recommendations(db: DbSession, user: CurrentUser) -> list[TitleSummary]:
    """Recommendation row independent of /v1/home.

    Same source as the 'Recommended for You' row on home — seeded by reactions,
    watchlist, and watch progress. Returns an empty list for users with no
    signal yet.
    """
    titles = await browse_svc.recommended_for_you(db, user)
    return [TitleSummary.model_validate(t) for t in titles]


# ---- Profiles ("Who's watching?") --------------------------------------------


@router.get("/me/profiles", response_model=ProfileList, tags=["profiles"])
async def list_profiles_endpoint(db: DbSession, user: CurrentUser) -> ProfileList:
    """List the user's profiles. Auto-creates the primary on first call so
    pre-profiles accounts always see at least one row."""
    profiles = await profile_svc.list_profiles(db, user.id)
    if not profiles:
        await profile_svc.ensure_primary_profile(db, user.id, default_name=user.full_name)
        await db.commit()
        profiles = await profile_svc.list_profiles(db, user.id)
    return ProfileList(
        items=[ProfileRead.model_validate(p) for p in profiles],
        max_profiles=profile_svc.MAX_PROFILES_PER_USER,
    )


@router.post("/me/profiles", response_model=ProfileRead, status_code=status.HTTP_201_CREATED, tags=["profiles"])
async def create_profile_endpoint(
    body: ProfileCreate, db: DbSession, user: CurrentUser
) -> ProfileRead:
    try:
        profile = await profile_svc.create_profile(
            db, user.id, name=body.name, avatar=body.avatar, kind=body.kind
        )
    except profile_svc.ProfileLimitReached as exc:
        raise _err(exc, status.HTTP_409_CONFLICT) from exc
    except profile_svc.DuplicateName as exc:
        raise _err(exc, status.HTTP_409_CONFLICT) from exc
    await db.commit()
    return ProfileRead.model_validate(profile)


@router.patch("/me/profiles/{profile_id}", response_model=ProfileRead, tags=["profiles"])
async def update_profile_endpoint(
    profile_id: int, body: ProfileUpdate, db: DbSession, user: CurrentUser
) -> ProfileRead:
    try:
        profile = await profile_svc.update_profile(
            db, user.id, profile_id, name=body.name, avatar=body.avatar, kind=body.kind
        )
    except profile_svc.ProfileNotFound as exc:
        raise _err(exc, status.HTTP_404_NOT_FOUND) from exc
    except profile_svc.DuplicateName as exc:
        raise _err(exc, status.HTTP_409_CONFLICT) from exc
    await db.commit()
    return ProfileRead.model_validate(profile)


@router.delete("/me/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["profiles"])
async def delete_profile_endpoint(
    profile_id: int, db: DbSession, user: CurrentUser
) -> None:
    try:
        await profile_svc.delete_profile(db, user.id, profile_id)
    except profile_svc.ProfileNotFound as exc:
        raise _err(exc, status.HTTP_404_NOT_FOUND) from exc
    except profile_svc.CannotDeletePrimary as exc:
        raise _err(exc, status.HTTP_409_CONFLICT) from exc
    await db.commit()
