"""
Title model — the unified catalog row for both movies and series.

Rules:
- type='movie' implies no seasons/episodes; the title itself is the playable unit.
- type='series' implies seasons[] → episodes[]; episodes are the playable units.
- series_type carries the limited/mini/anthology distinction Netflix uses.
- view_count is denormalized and bumped per playback ticket; trending row reads it.
- status is the single lifecycle column: draft → scheduled → published → archived → removed.
- publish_at lets admins schedule a future publish; a background job (Phase 2) or
  on-read auto-promotion flips scheduled → published when the time arrives.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Index, String, Table, Column, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


titles_genres = Table(
    "titles_genres",
    Base.metadata,
    Column("title_id", ForeignKey("titles.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)


class Title(Base):
    __tablename__ = "titles"

    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)  # 'movie' | 'series'
    series_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Only set for series. 'ongoing' | 'limited' | 'mini' | 'anthology'

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    synopsis: Mapped[str | None] = mapped_column(Text, nullable=True)
    release_year: Mapped[int | None] = mapped_column(nullable=True)
    runtime_minutes: Mapped[int | None] = mapped_column(nullable=True)
    age_rating: Mapped[str | None] = mapped_column(String(8), nullable=True)
    original_language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    countries: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    poster_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    backdrop_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    trailer_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    format_tag: Mapped[str | None] = mapped_column(String(32), nullable=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # When True, unsubscribed users can play this title. For series this means
    # ALL episodes are free unless their own is_free is explicitly False (use
    # case: a free series). For first-episode-free (Hoichoi/Aha pattern), leave
    # this False and set the individual episode's is_free=True.
    is_free: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Denormalized counter — bumped on playback. Used by Trending row.
    view_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    genres: Mapped[list["Genre"]] = relationship(
        "Genre", secondary=titles_genres, lazy="selectin"
    )
    seasons: Mapped[list["Season"]] = relationship(
        "Season",
        back_populates="title",
        cascade="all, delete-orphan",
        order_by="Season.season_number",
        lazy="selectin",
    )
    assets: Mapped[list["TitleAsset"]] = relationship(
        "TitleAsset", back_populates="title", cascade="all, delete-orphan", lazy="selectin"
    )
    audio_tracks: Mapped[list["AudioTrack"]] = relationship(
        "AudioTrack", back_populates="title", cascade="all, delete-orphan", lazy="selectin"
    )
    subtitle_tracks: Mapped[list["SubtitleTrack"]] = relationship(
        "SubtitleTrack", back_populates="title", cascade="all, delete-orphan", lazy="selectin"
    )
    availability_windows: Mapped[list["AvailabilityWindow"]] = relationship(
        "AvailabilityWindow", back_populates="title", cascade="all, delete-orphan", lazy="selectin"
    )
    credits: Mapped[list["TitleCredit"]] = relationship(
        "TitleCredit", back_populates="title", cascade="all, delete-orphan", lazy="selectin"
    )


# Indexes backing the hot read paths (docs/db-schema.md documents these).
# Declared at model level so the SQLite test DB (built from metadata) gets
# them too; the matching Alembic migration creates them on Postgres.
Index("ix_titles_status_published_at", Title.status, Title.published_at)  # default listings
Index("ix_titles_type_status", Title.type, Title.status)  # movie/series filter
Index("ix_titles_view_count_desc", Title.view_count.desc())  # trending / similar ordering


class TitleAsset(Base):
    """Title-level assets — movie HLS manifest, trailer. Episode-level lives in EpisodeAsset."""

    __tablename__ = "title_assets"

    title_id: Mapped[int] = mapped_column(
        ForeignKey("titles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # 'hls_manifest' | 'trailer'
    storage_url: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)

    title: Mapped[Title] = relationship("Title", back_populates="assets")
