"""Lightweight person + credit model. V2 will swap for an external service (TMDB-like)."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Person(Base):
    __tablename__ = "persons"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    profile_url: Mapped[str | None] = mapped_column(Text, nullable=True)


class TitleCredit(Base):
    __tablename__ = "title_credits"

    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    # 'cast' | 'director' | 'writer' | 'creator' | 'producer'
    character_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order: Mapped[int] = mapped_column(nullable=False, default=0)

    title: Mapped["Title"] = relationship("Title", back_populates="credits")
    person: Mapped[Person] = relationship("Person")
