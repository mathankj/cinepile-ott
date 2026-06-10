"""My List — user's bookmarked titles."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    # Unique per (user, profile, title). NULL profile_id (legacy / no-header
    # scope) rows aren't deduped by the DB — NULLs compare distinct in unique
    # indexes on both Postgres and SQLite — so the service's check-then-insert
    # is the real guard there.
    __table_args__ = (
        UniqueConstraint("user_id", "profile_id", "title_id", name="uq_watchlist_user_title"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # NULL = legacy/no-profile scope; SET NULL on profile delete keeps the list
    # at account level instead of dropping it.
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
