"""Title / Season / Episode response & request schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ----- Common building blocks -----


class GenreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str
    kind: str


class AudioTrackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    language: str
    kind: Literal["original", "dub"]
    codec: str | None = None


class SubtitleTrackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int | None = None  # null for in-manifest tracks (no DB row of their own)
    language: str
    kind: Literal["subtitle", "cc", "sdh", "dubtitle"]
    forced: bool
    label: str | None = None


class PersonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    profile_url: str | None = None


class CreditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    person: PersonRead
    role: Literal["cast", "director", "writer", "creator", "producer"]
    character_name: str | None = None
    order: int = 0


class TitleAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    kind: str
    storage_url: str
    language: str | None = None


class EpisodeAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    kind: str
    storage_url: str


# ----- Title card / detail -----


class TitleSummary(BaseModel):
    """Card-sized payload used in rows + list views."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    type: Literal["movie", "series"]
    title: str
    poster_url: str | None = None
    backdrop_url: str | None = None
    release_year: int | None = None
    age_rating: str | None = None
    runtime_minutes: int | None = None
    # Frontend renders a "FREE" badge when True
    is_free: bool = False


class SeasonSummary(BaseModel):
    """Lightweight season entry in a series detail."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    season_number: int
    name: str | None = None
    episode_count: int = 0


class TitleDetail(BaseModel):
    """Full payload for GET /v1/titles/{id}."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    type: Literal["movie", "series"]
    series_type: Literal["ongoing", "limited", "mini", "anthology"] | None = None

    title: str
    original_title: str | None
    synopsis: str | None
    release_year: int | None
    runtime_minutes: int | None
    age_rating: str | None
    original_language: str | None
    countries: list[str] | None
    poster_url: str | None
    backdrop_url: str | None
    trailer_url: str | None
    format_tag: str | None
    is_free: bool = False

    status: str
    published_at: datetime | None
    view_count: int

    genres: list[GenreRead] = Field(default_factory=list)
    audio_tracks: list[AudioTrackRead] = Field(default_factory=list)
    subtitle_tracks: list[SubtitleTrackRead] = Field(default_factory=list)
    credits: list[CreditRead] = Field(default_factory=list)
    assets: list[TitleAssetRead] = Field(default_factory=list)

    # For series only — light summary of seasons
    seasons: list[SeasonSummary] = Field(default_factory=list)


class TitleListResponse(BaseModel):
    items: list[TitleSummary]
    page: int
    page_size: int
    total: int


# ----- Episode -----


class EpisodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    episode_number: int
    ordinal: int
    name: str
    synopsis: str | None
    runtime_seconds: int | None
    air_date: date | None
    intro_start_sec: int | None
    intro_end_sec: int | None
    recap_start_sec: int | None
    recap_end_sec: int | None
    credits_start_sec: int | None
    next_episode_cue_sec: int | None
    status: str
    published_at: datetime | None
    is_free: bool = False
    assets: list[EpisodeAssetRead] = Field(default_factory=list)


class SeasonDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    season_number: int
    name: str | None
    synopsis: str | None
    poster_url: str | None
    release_year: int | None
    episodes: list[EpisodeRead] = Field(default_factory=list)


# ----- Admin write schemas -----


class TitleCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9-]+$")
    type: Literal["movie", "series"]
    series_type: Literal["ongoing", "limited", "mini", "anthology"] | None = None
    title: str = Field(min_length=1, max_length=255)
    original_title: str | None = None
    synopsis: str | None = None
    release_year: int | None = Field(default=None, ge=1888, le=2100)
    runtime_minutes: int | None = Field(default=None, ge=1, le=1000)
    age_rating: str | None = Field(default=None, max_length=8)
    original_language: str | None = Field(default=None, max_length=8)
    countries: list[str] | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    trailer_url: str | None = None
    format_tag: str | None = None
    genre_slugs: list[str] = Field(default_factory=list)
    # Optional movie convenience: create the hls asset alongside
    hls_manifest_url: str | None = None
    status: Literal["draft", "scheduled", "published", "archived"] = "draft"
    publish_at: datetime | None = None
    is_free: bool = False


class TitleUpdate(BaseModel):
    """Update schema — extra='forbid' blocks mass-assignment of fields we didn't list."""
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    original_title: str | None = None
    synopsis: str | None = None
    series_type: Literal["ongoing", "limited", "mini", "anthology"] | None = None
    release_year: int | None = None
    runtime_minutes: int | None = None
    age_rating: str | None = None
    original_language: str | None = None
    countries: list[str] | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    trailer_url: str | None = None
    format_tag: str | None = None
    genre_slugs: list[str] | None = None
    hls_manifest_url: str | None = None
    is_free: bool | None = None


class TitleSchedule(BaseModel):
    publish_at: datetime


class SeasonCreate(BaseModel):
    season_number: int = Field(ge=1)
    name: str | None = None
    synopsis: str | None = None
    poster_url: str | None = None
    release_year: int | None = None


class SeasonUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    synopsis: str | None = None
    poster_url: str | None = None
    release_year: int | None = None


class EpisodeCreate(BaseModel):
    episode_number: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=255)
    synopsis: str | None = None
    runtime_seconds: int | None = Field(default=None, ge=1)
    air_date: date | None = None
    intro_start_sec: int | None = Field(default=None, ge=0)
    intro_end_sec: int | None = Field(default=None, ge=0)
    recap_start_sec: int | None = Field(default=None, ge=0)
    recap_end_sec: int | None = Field(default=None, ge=0)
    credits_start_sec: int | None = Field(default=None, ge=0)
    next_episode_cue_sec: int | None = Field(default=None, ge=0)
    hls_manifest_url: str | None = None
    status: Literal["draft", "scheduled", "published", "archived"] = "draft"
    publish_at: datetime | None = None
    is_free: bool = False


class EpisodeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    synopsis: str | None = None
    runtime_seconds: int | None = None
    air_date: date | None = None
    intro_start_sec: int | None = None
    intro_end_sec: int | None = None
    recap_start_sec: int | None = None
    recap_end_sec: int | None = None
    credits_start_sec: int | None = None
    next_episode_cue_sec: int | None = None
    hls_manifest_url: str | None = None
    ordinal: int | None = None
    is_free: bool | None = None


class AudioTracksReplace(BaseModel):
    tracks: list[AudioTrackRead]


class SubtitleTracksReplace(BaseModel):
    tracks: list[SubtitleTrackRead]


class GenreCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1, max_length=128)
    kind: Literal["primary", "sub", "mood"] = "primary"
