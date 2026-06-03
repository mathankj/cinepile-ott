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
    """A subtitle / closed-caption / SDH track.

    Belongs to EITHER a Title (movie) or an Episode — exactly one of title_id /
    episode_id is set. Old seed rows pre-CC-upload have title_id + null
    storage_url (no playable file, just metadata for the language picker).
    New uploads via the admin endpoint always carry storage_url pointing at the
    .vtt file in B2 (or a public storage URL).
    """

    __tablename__ = "subtitle_tracks"

    title_id: Mapped[int | None] = mapped_column(
        ForeignKey("titles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    episode_id: Mapped[int | None] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True, index=True
    )
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    # 'subtitle' | 'cc' | 'sdh' | 'dubtitle'
    forced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Either a full public URL or a bucket key — resolved to a presigned URL at
    # playback time by storage_svc.resolve_url(). Nullable for legacy seed data.
    storage_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # Optional human label e.g. "English [CC]" or "Tamil"; defaults to the
    # language ISO code uppercased when not provided.
    label: Mapped[str | None] = mapped_column(String(64), nullable=True)

    title: Mapped["Title | None"] = relationship("Title", back_populates="subtitle_tracks")
