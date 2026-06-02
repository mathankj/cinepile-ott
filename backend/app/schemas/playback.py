"""Playback URL response."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PlaybackTicket(BaseModel):
    manifest_url: str
    token: str
    expires_at: datetime
    film_id: int
