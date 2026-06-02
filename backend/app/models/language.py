"""Audio + subtitle track metadata per title."""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AudioTrack(Base):
    __tablename__ = "audio_tracks"

    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    language: Mapped[str] = mapped_column(String(8), nullable=False)  # ISO 639-1
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # 'original' | 'dub'
    codec: Mapped[str | None] = mapped_column(String(32), nullable=True)

    title: Mapped["Title"] = relationship("Title", back_populates="audio_tracks")


class SubtitleTrack(Base):
    __tablename__ = "subtitle_tracks"

    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    # 'subtitle' | 'cc' | 'sdh' | 'dubtitle'
    forced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    title: Mapped["Title"] = relationship("Title", back_populates="subtitle_tracks")
