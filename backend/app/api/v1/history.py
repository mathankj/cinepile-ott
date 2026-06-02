"""Watch-history routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.film import FilmSummary
from app.schemas.history import HistoryItem, HistoryList, ProgressUpdate
from app.services import history as history_svc

router = APIRouter()


@router.post("/{film_id}/progress", status_code=status.HTTP_204_NO_CONTENT)
async def upsert_progress(
    film_id: int, payload: ProgressUpdate, db: DbSession, user: CurrentUser
) -> None:
    try:
        await history_svc.upsert_progress(
            db,
            user,
            film_id=film_id,
            position_sec=payload.position_sec,
            total_sec=payload.total_sec,
        )
    except history_svc.FilmNotWatchable as e:
        raise HTTPException(404, detail={"error": {"code": e.code, "message": e.message}}) from e


@router.get("", response_model=HistoryList)
async def list_history(db: DbSession, user: CurrentUser) -> HistoryList:
    rows = await history_svc.list_continue_watching(db, user)
    items = [
        HistoryItem(
            film=FilmSummary.model_validate(film),
            position_sec=wh.position_sec,
            total_sec=wh.total_sec,
            completed=wh.completed,
            last_played_at=wh.last_played_at,
        )
        for wh, film in rows
    ]
    return HistoryList(items=items)


@router.delete("/{film_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_history(film_id: int, db: DbSession, user: CurrentUser) -> None:
    deleted = await history_svc.delete_entry(db, user, film_id=film_id)
    if not deleted:
        raise HTTPException(
            404,
            detail={"error": {"code": "not_found", "message": "No history entry for that film."}},
        )
