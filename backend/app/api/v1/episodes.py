"""Direct episode endpoints — playback."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.playback import PlaybackTicket
from app.services import catalog, playback

router = APIRouter()


def _err(exc, code: int) -> HTTPException:
    return HTTPException(
        status_code=code,
        detail={"error": {"code": exc.code, "message": exc.message}},
    )


@router.get("/{episode_id}/play", response_model=PlaybackTicket)
async def play_episode(episode_id: int, db: DbSession, user: CurrentUser) -> PlaybackTicket:
    try:
        ep = await catalog.get_episode_by_id(db, episode_id)
    except catalog.EpisodeNotFound as e:
        raise _err(e, 404) from e
    try:
        ticket = await playback.issue_episode_ticket(db, user, ep)
    except playback.NotEntitled as e:
        raise _err(e, status.HTTP_402_PAYMENT_REQUIRED) from e
    except playback.NoPlayableAsset as e:
        raise _err(e, 409) from e
    return PlaybackTicket(**ticket)
