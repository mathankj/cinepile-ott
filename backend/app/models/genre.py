"""Genre — renamed from Category. Now carries a kind so we can have moods and sub-genres later."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Genre(Base):
    __tablename__ = "genres"

    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="primary")
    # 'primary' | 'sub' | 'mood'
