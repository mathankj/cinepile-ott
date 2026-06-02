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


PLAYBACK_TTL_MINUTES = 240  # 4h — long enough to finish a film comfortably


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


async def _ensure_entitled(db: AsyncSession, user: User) -> None:
    if not await has_active_subscription(db, user):
        raise NotEntitled


async def issue_movie_ticket(db: AsyncSession, user: User, title: Title) -> dict:
    await _ensure_entitled(db, user)
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

    return {
        "manifest_url": playback_url,
        "token": token,
        "expires_at": expires_at,
        "ref_id": title.id,
        "ref_type": "title",
    }


async def issue_episode_ticket(db: AsyncSession, user: User, episode: Episode) -> dict:
    await _ensure_entitled(db, user)
    manifest = next((a for a in episode.assets if a.kind == "hls_manifest"), None)
    if manifest is None:
        raise NoPlayableAsset
    playback_url = storage_svc.resolve_url(manifest.storage_url)
    expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=PLAYBACK_TTL_MINUTES)
    token = _build_token(user.id, "episode", episode.id, playback_url, expires_at)

    season = await db.get(Season, episode.season_id)
    if season is not None:
        await db.execute(
            update(Title).where(Title.id == season.title_id).values(view_count=Title.view_count + 1)
        )

    return {
        "manifest_url": playback_url,
        "token": token,
        "expires_at": expires_at,
        "ref_id": episode.id,
        "ref_type": "episode",
    }
