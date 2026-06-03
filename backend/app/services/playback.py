"""
Playback URL service — V1.5 supports both movies (title-level asset) and series
(episode-level asset).

V1: returns a short-lived JWT-signed URL that points at the stored HLS manifest.
V2: replace with real CDN signed URLs (CloudFront / Bunny).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.episode import Episode
from app.models.season import Season
from app.models.title import Title
from app.models.user import User
from app.services import storage as storage_svc
from app.services.billing import has_active_subscription


# Manifest TTL is intentionally short — a leaked URL is only useful for the
# remaining TTL. Players refresh the manifest periodically anyway. 15 min
# matches Mux / CloudFront signed-URL recommendations for video manifests.
# Segment URLs (Phase 2 when we have a real CDN) can be longer (~2h) because
# they are per-byte-range.
PLAYBACK_TTL_MINUTES = 15


class NotEntitled(Exception):
    code = "subscription_required"
    message = "An active subscription is required to play this title."


class NoPlayableAsset(Exception):
    code = "no_playable_asset"
    message = "This title or episode has no playable asset configured."


def _build_token(user_id: int, ref_type: str, ref_id: int, url: str, expires_at: datetime) -> str:
    settings = get_settings()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        ref_type: ref_id,
        "exp": expires_at,
        "type": "playback",
        "url": url,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def _ensure_entitled(
    db: AsyncSession, user: User, *, title: Title | None = None, episode: Episode | None = None
) -> None:
    """Subscription gate, with free-content bypass.

    Order of checks:
      1. If episode.is_free → allow (first-episode-free pattern).
      2. If title.is_free → allow (free movie or wholly-free series).
      3. Else → require an active subscription.
    """
    if episode is not None and episode.is_free:
        return
    if title is not None and title.is_free:
        return
    if not await has_active_subscription(db, user):
        raise NotEntitled


async def _lookup_resume(
    db: AsyncSession, user_id: int, title_id: int, episode_id: int | None
) -> tuple[int | None, int | None]:
    """Returns (position_sec, total_sec) for a user's prior progress, if any.
    None when this is the user's first time playing this content."""
    from sqlalchemy import and_, select as _select

    from app.models.watch_progress import WatchProgress

    where = [WatchProgress.user_id == user_id, WatchProgress.title_id == title_id]
    if episode_id is None:
        where.append(WatchProgress.episode_id.is_(None))
    else:
        where.append(WatchProgress.episode_id == episode_id)
    row = await db.scalar(_select(WatchProgress).where(and_(*where)))
    if row is None:
        return None, None
    return row.position_sec, row.total_sec


async def issue_movie_ticket(db: AsyncSession, user: User, title: Title) -> dict:
    await _ensure_entitled(db, user, title=title)
    manifest = next((a for a in title.assets if a.kind == "hls_manifest"), None)
    if manifest is None:
        raise NoPlayableAsset
    # resolve_url returns the URL as-is if it's already a full http(s):// URL,
    # else generates a presigned URL from the bucket key (private-bucket case).
    playback_url = storage_svc.resolve_url(manifest.storage_url)
    expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=PLAYBACK_TTL_MINUTES)
    token = _build_token(user.id, "title", title.id, playback_url, expires_at)

    # Bump view counter for Trending row.
    await db.execute(update(Title).where(Title.id == title.id).values(view_count=Title.view_count + 1))

    # Resume hint — saves the frontend a round trip to /me/continue-watching
    resume_at, stored_total = await _lookup_resume(db, user.id, title.id, None)
    total_sec = stored_total or (title.runtime_minutes * 60 if title.runtime_minutes else None)

    return {
        "manifest_url": playback_url,
        "token": token,
        "expires_at": expires_at,
        "ref_id": title.id,
        "ref_type": "title",
        "resume_at_sec": resume_at,
        "total_sec": total_sec,
    }


async def issue_episode_ticket(db: AsyncSession, user: User, episode: Episode) -> dict:
    # Episode free overrides; otherwise check parent series's is_free; otherwise need sub.
    season = await db.get(Season, episode.season_id)
    parent_title = await db.get(Title, season.title_id) if season else None
    await _ensure_entitled(db, user, title=parent_title, episode=episode)
    manifest = next((a for a in episode.assets if a.kind == "hls_manifest"), None)
    if manifest is None:
        raise NoPlayableAsset
    playback_url = storage_svc.resolve_url(manifest.storage_url)
    expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=PLAYBACK_TTL_MINUTES)
    token = _build_token(user.id, "episode", episode.id, playback_url, expires_at)

    if season is not None:
        await db.execute(
            update(Title).where(Title.id == season.title_id).values(view_count=Title.view_count + 1)
        )

    # Resume + total — keyed on (user, title, episode)
    parent_title_id = season.title_id if season else 0
    resume_at, stored_total = await _lookup_resume(db, user.id, parent_title_id, episode.id)
    total_sec = stored_total or episode.runtime_seconds

    return {
        "manifest_url": playback_url,
        "token": token,
        "expires_at": expires_at,
        "ref_id": episode.id,
        "ref_type": "episode",
        "resume_at_sec": resume_at,
        "total_sec": total_sec,
    }
