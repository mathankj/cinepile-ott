"""
Per-user, per-watchable progress. Replaces V1's WatchHistory.

Movies: one row per (user, title) — episode_id is NULL.
Series: one row per (user, episode) — title_id is the series, episode_id is the playable.

Unique on (user_id, title_id, episode_id). Both Postgres and SQLite treat NULL as
distinct in unique indexes, so this works for movies (single NULL row per (user,title))
and for series (multiple non-NULL rows per (user,title)).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WatchProgress(Base):
    __tablename__ = "watch_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "title_id", "episode_id", name="uq_watch_progress_unique"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    episode_id: Mapped[int | None] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True, index=True
    )
    position_sec: Mapped[int] = mapped_column(nullable=False, default=0)
    total_sec: Mapped[int] = mapped_column(nullable=False, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # User explicitly removed this from Continue Watching. The row stays for
    # resume-if-they-search-again behaviour (Netflix's pattern); the
    # continue-watching list filters it out.
    hidden_from_continue: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
