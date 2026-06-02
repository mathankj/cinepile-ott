"""Watch-history schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.film import FilmSummary


class ProgressUpdate(BaseModel):
    position_sec: int = Field(ge=0)
    total_sec: int = Field(gt=0)


class HistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    film: FilmSummary
    position_sec: int
    total_sec: int
    completed: bool
    last_played_at: datetime


class HistoryList(BaseModel):
    items: list[HistoryItem]
