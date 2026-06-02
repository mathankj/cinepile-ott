"""
Playback URL service.

V1: returns a short-lived JWT-signed URL that points at the film's stored
HLS manifest. The token carries (user_id, film_id, exp) so a future CDN
verification layer (or our own proxy) can refuse expired/forged tokens.

V2: the URL becomes a CloudFront signed URL or BunnyCDN token URL.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import cast

from jose import jwt

from app.core.config import get_settings
from app.models.film import Film, FilmAsset
from app.models.user import User
from app.services.billing import has_active_subscription


PLAYBACK_TTL_MINUTES = 240  # 4h — long enough to finish a film comfortably


class NotEntitled(Exception):
    code = "subscription_required"
    message = "An active subscription is required to play this film."


class NoPlayableAsset(Exception):
    code = "no_playable_asset"
    message = "This film has no playable asset configured."


async def issue_ticket(db, user: User, film: Film) -> dict:
    if not await has_active_subscription(db, user):
        raise NotEntitled

    manifest_asset = next((a for a in film.assets if a.kind == "hls_manifest"), None)
    if manifest_asset is None:
        raise NoPlayableAsset

    settings = get_settings()
    expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=PLAYBACK_TTL_MINUTES)
    payload = {
        "sub": str(user.id),
        "film": film.id,
        "exp": expires_at,
        "type": "playback",
        "url": manifest_asset.storage_url,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {
        "manifest_url": manifest_asset.storage_url,
        "token": token,
        "expires_at": expires_at,
        "film_id": cast(int, film.id),
    }
