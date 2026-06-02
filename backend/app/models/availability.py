"""
Per-region availability windows.

In V1.5 we keep this simple — one row per (title, region) defines when the title
is watchable in that region. A title without availability_windows is considered
available everywhere (the V1 behavior, so existing demo data still works).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AvailabilityWindow(Base):
    __tablename__ = "availability_windows"

    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    title: Mapped["Title"] = relationship("Title", back_populates="availability_windows")


class MaturityRating(Base):
    __tablename__ = "maturity_ratings"

    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    system: Mapped[str] = mapped_column(String(16), nullable=False)
    # 'MPAA' | 'BBFC' | 'CBFC' | 'TV' ...
    rating_code: Mapped[str] = mapped_column(String(16), nullable=False)
    # 'PG-13' | 'TV-MA' | '15' ...
    maturity_level: Mapped[int] = mapped_column(nullable=False)
    # 0-18 normalized
