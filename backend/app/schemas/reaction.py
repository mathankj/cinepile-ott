"""Reaction + Watchlist + Continue-watching schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.title import TitleSummary


class ReactionWrite(BaseModel):
    kind: Literal["thumbs_down", "thumbs_up", "double_thumbs_up"]


class ReactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: TitleSummary
    kind: str
    updated_at: datetime


class ReactionList(BaseModel):
    items: list[ReactionRead]


class WatchlistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: TitleSummary
    added_at: datetime


class WatchlistRead(BaseModel):
    items: list[WatchlistItemRead]


class ContinueWatchingItem(BaseModel):
    """One item — for series, refers to the currently-playing episode."""
    title: TitleSummary
    episode_id: int | None = None
    episode_number: int | None = None
    season_number: int | None = None
    episode_name: str | None = None
    position_sec: int
    total_sec: int
    last_played_at: datetime


class ContinueWatchingList(BaseModel):
    items: list[ContinueWatchingItem]


class HistoryItem(BaseModel):
    """Row in /v1/me/history — every title the user has touched, regardless of state."""
    title: TitleSummary
    position_sec: int
    total_sec: int
    completed: bool
    hidden_from_continue: bool
    last_played_at: datetime


class HistoryList(BaseModel):
    items: list[HistoryItem]
    page: int
    page_size: int
    total: int


class ProgressUpdate(BaseModel):
    """Generic — used for both movie and episode progress."""
    position_sec: int
    total_sec: int
