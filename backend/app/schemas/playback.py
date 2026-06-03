"""Playback URL response — works for both movies and episodes."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DrmConfig(BaseModel):
    """DRM key-system configuration the player needs to make a license request.

    Only the systems supported by the configured DRM provider are populated.
    Empty fields mean "this key system isn't available — fall back to a clear
    stream or the next system the browser supports."

    The player picks ONE system based on navigator.requestMediaKeySystemAccess
    (Widevine on Chrome/Edge/Android, PlayReady on Edge/Windows, FairPlay on
    Safari/iOS). It then POSTs the license challenge to the relevant URL with
    `playback_token` as a header.
    """

    widevine_license_url: str | None = None
    playready_license_url: str | None = None
    fairplay_license_url: str | None = None
    fairplay_cert_url: str | None = None
    # The token the player must present to the license server. Backend mints
    # this server-side (signed with DRM_TOKEN_SECRET) so the license server
    # can verify the request before issuing decryption keys.
    playback_token: str | None = None


class PlaybackTicket(BaseModel):
    manifest_url: str
    token: str
    expires_at: datetime
    ref_type: Literal["title", "episode"]
    ref_id: int
    # If user has prior watch-progress on this content, the frontend should
    # seek to this position rather than starting at 0. None for first-time plays.
    resume_at_sec: int | None = None
    # Useful for the player progress bar; comes from the episode's runtime
    # or the title's runtime_minutes * 60 (None if not yet known).
    total_sec: int | None = None
    # DRM — null when no DRM provider is configured (the V1 default for dev).
    # Once a provider is wired up (Widevine / PlayReady / FairPlay) this
    # block is populated and the player switches to encrypted playback.
    drm: DrmConfig | None = None
