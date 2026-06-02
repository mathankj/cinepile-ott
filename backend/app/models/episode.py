"""
Episode model — the playable unit for series.

Skip-intro / skip-recap / credits markers are nullable; player only shows the
button when both endpoints are set (or, for credits_start_sec, when player
crosses that timestamp).

Episode status is independent of its parent title's status — that's how weekly
release schedules work (one episode `published`, the next still `draft`).
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Episode(Base):
    __tablename__ = "episodes"
    __table_args__ = (UniqueConstraint("season_id", "episode_number", name="uq_episodes_season_number"),)

    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    episode_number: Mapped[int] = mapped_column(nullable=False)
    # Same as episode_number by default; mutable to support re-cuts (production vs air order).
    ordinal: Mapped[int] = mapped_column(nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    synopsis: Mapped[str | None] = mapped_column(Text, nullable=True)
    runtime_seconds: Mapped[int | None] = mapped_column(nullable=True)
    air_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Skip markers (all seconds, all nullable)
    intro_start_sec: Mapped[int | None] = mapped_column(nullable=True)
    intro_end_sec: Mapped[int | None] = mapped_column(nullable=True)
    recap_start_sec: Mapped[int | None] = mapped_column(nullable=True)
    recap_end_sec: Mapped[int | None] = mapped_column(nullable=True)
    credits_start_sec: Mapped[int | None] = mapped_column(nullable=True)
    next_episode_cue_sec: Mapped[int | None] = mapped_column(nullable=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    season: Mapped["Season"] = relationship("Season", back_populates="episodes")
    assets: Mapped[list["EpisodeAsset"]] = relationship(
        "EpisodeAsset", back_populates="episode", cascade="all, delete-orphan", lazy="selectin"
    )


class EpisodeAsset(Base):
    __tablename__ = "episode_assets"

    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # 'hls_manifest'
    storage_url: Mapped[str] = mapped_column(Text, nullable=False)

    episode: Mapped[Episode] = relationship("Episode", back_populates="assets")
