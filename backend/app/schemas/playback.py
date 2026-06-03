"""Playback URL response — works for both movies and episodes."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


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
