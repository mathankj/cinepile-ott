"""Three-state reaction per (user, title) — matches Netflix's Apr-2022 model."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Reaction(Base):
    __tablename__ = "reactions"
    __table_args__ = (UniqueConstraint("user_id", "title_id", name="uq_reactions_user_title"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    # 'thumbs_down' | 'thumbs_up' | 'double_thumbs_up'
