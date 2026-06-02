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
