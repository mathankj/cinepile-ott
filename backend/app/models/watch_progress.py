"""
Per-user, per-watchable progress. Replaces V1's WatchHistory.

Movies: one row per (user, title) — episode_id is NULL.
Series: one row per (user, episode) — title_id is the series, episode_id is the playable.

Unique on (user_id, profile_id, title_id, episode_id). Both Postgres and SQLite
treat NULL as distinct in unique indexes, so this works for movies (single NULL
episode row per (user, profile, title)) and for series (multiple non-NULL rows).
Note the same NULL semantics apply to profile_id: rows with profile_id NULL
(legacy / no-profile scope) are NOT deduped by the constraint — the app-level
select-then-upsert in services/history.py is what guarantees one row there.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WatchProgress(Base):
    __tablename__ = "watch_progress"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "profile_id", "title_id", "episode_id", name="uq_watch_progress_unique"
        ),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # Which profile within the account watched this. NULL = legacy rows from
    # before profile scoping, or requests sent without an X-Profile-Id header.
    # ondelete SET NULL: deleting a profile folds its history back into the
    # account-level (no-profile) scope instead of erasing it.
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
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


# Continue-watching and full-history both read "this user's rows, most recent
# first" — this composite index serves that without a sort. Declared at model
# level so the SQLite test DB (built from metadata) gets it; the matching
# Alembic migration creates it on Postgres.
Index(
    "ix_watch_progress_user_id_last_played_at",
    WatchProgress.user_id,
    WatchProgress.last_played_at.desc(),
)
