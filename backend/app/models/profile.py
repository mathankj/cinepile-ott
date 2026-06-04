"""Profile model — Netflix-style "Who's watching?" sub-account.

One user account owns 1-4 profiles. Each profile has its own continue-watching,
watchlist, and reaction history. The primary profile is auto-created at signup
and cannot be deleted (it's the fallback when a profile is removed).

Profiles are NOT separate auth identities — the user's login still goes through
the User table. The selected profile_id is just an extra header / query param
that the API uses to scope queries.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_profile_user_name"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Display name — what the user sees on the picker. Max 32 like Netflix.
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    # Avatar — either a short ID into the frontend's avatar registry (e.g.
    # "panda", "astronaut", "ninja") which renders as an illustrated SVG via
    # DiceBear, OR an emoji glyph for legacy rows. The frontend's avatar
    # library detects the format and renders accordingly. 32 chars covers
    # both formats with headroom for future avatar variants.
    avatar: Mapped[str] = mapped_column(String(32), nullable=False, default="default")
    # "adult" or "kid" — kids profiles will (in future) filter to U-rated content
    # only. For V1 the flag is stored but not enforced anywhere; we'll wire it
    # to the content filter once age-rating gating is fully implemented.
    kind: Mapped[str] = mapped_column(String(8), nullable=False, default="adult")
    # The primary profile is the user's original one; cannot be deleted. Auto-
    # created on user signup so the picker always has at least one row.
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Loaded via relationship() for convenience in services; not exposed in HTTP.
    user = relationship("User", lazy="joined")
