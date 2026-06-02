"""Catalog schemas — film/category read + admin create/update."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str


class FilmAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    kind: str
    storage_url: str
    language: str | None = None
    bitrate_kbps: int | None = None
    width: int | None = None
    height: int | None = None
    duration_sec: int | None = None


class FilmSummary(BaseModel):
    """Card-sized payload for list views."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    title: str
    poster_url: str | None
    release_year: int | None
    runtime_minutes: int | None
    age_rating: str | None


class FilmDetail(BaseModel):
    """Full payload for /films/{id}."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    title: str
    original_title: str | None
    synopsis: str | None
    release_year: int | None
    runtime_minutes: int | None
    age_rating: str | None
    poster_url: str | None
    backdrop_url: str | None
    trailer_url: str | None
    primary_language: str | None
    countries: list[str] | None
    status: str
    published_at: datetime | None
    categories: list[CategoryRead] = Field(default_factory=list)
    assets: list[FilmAssetRead] = Field(default_factory=list)


class FilmListResponse(BaseModel):
    items: list[FilmSummary]
    page: int
    page_size: int
    total: int


class FilmCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=1, max_length=255)
    original_title: str | None = None
    synopsis: str | None = None
    release_year: int | None = Field(default=None, ge=1888, le=2100)
    runtime_minutes: int | None = Field(default=None, ge=1, le=1000)
    age_rating: str | None = Field(default=None, max_length=8)
    poster_url: str | None = None
    backdrop_url: str | None = None
    trailer_url: str | None = None
    primary_language: str | None = Field(default=None, max_length=8)
    countries: list[str] | None = None
    category_slugs: list[str] = Field(default_factory=list)
    hls_manifest_url: str | None = None  # convenience: creates a FilmAsset row
    status: Literal["draft", "published", "archived"] = "draft"


class FilmUpdate(BaseModel):
    title: str | None = None
    original_title: str | None = None
    synopsis: str | None = None
    release_year: int | None = None
    runtime_minutes: int | None = None
    age_rating: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    trailer_url: str | None = None
    primary_language: str | None = None
    countries: list[str] | None = None
    category_slugs: list[str] | None = None
    hls_manifest_url: str | None = None
    status: Literal["draft", "published", "archived"] | None = None
