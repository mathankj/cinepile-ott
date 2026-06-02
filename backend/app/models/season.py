"""Season model — children of a series title."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = (UniqueConstraint("title_id", "season_number", name="uq_seasons_title_number"),)

    title_id: Mapped[int] = mapped_column(
        ForeignKey("titles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    season_number: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    synopsis: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    release_year: Mapped[int | None] = mapped_column(nullable=True)

    title: Mapped["Title"] = relationship("Title", back_populates="seasons")
    episodes: Mapped[list["Episode"]] = relationship(
        "Episode",
        back_populates="season",
        cascade="all, delete-orphan",
        order_by="Episode.ordinal",
        lazy="selectin",
    )
