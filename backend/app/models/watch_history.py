"""Watch-progress per (user, film)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WatchHistory(Base):
    __tablename__ = "watch_history"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    film_id: Mapped[int] = mapped_column(
        ForeignKey("films.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
