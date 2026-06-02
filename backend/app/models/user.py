"""User model — see docs/db-schema.md."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    # Stored lowercased; we lowercase in the service layer so DB collation
    # doesn't matter (Postgres CITEXT is nicer; SQLite doesn't have it).
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Bump to invalidate every refresh token + access token (we check this in deps).
    session_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def is_admin(self) -> bool:
        return self.role == "admin"
