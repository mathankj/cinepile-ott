"""
Admin service — titles + seasons + episodes + genres + languages.

Every write goes through audit_svc.record() with a before/after snapshot.
Lifecycle:  draft → scheduled → published → archived → removed
            (publish_at is required when entering 'scheduled')
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.episode import Episode, EpisodeAsset
from app.models.genre import Genre
from app.models.language import AudioTrack, SubtitleTrack
from app.models.season import Season
from app.models.title import Title, TitleAsset
from app.models.user import User
from app.services import audit as audit_svc


# ---- Domain errors -----------------------------------------------------------


class SlugInUse(Exception):
    code = "slug_in_use"
    message = "Another title already uses that slug."


class TitleNotFound(Exception):
    code = "title_not_found"
    message = "Title not found."


class SeasonNotFound(Exception):
    code = "season_not_found"
    message = "Season not found."


class EpisodeNotFound(Exception):
    code = "episode_not_found"
    message = "Episode not found."


class GenreSlugInUse(Exception):
    code = "genre_slug_in_use"
    message = "Genre slug already exists."


class InvalidLifecycle(Exception):
    code = "invalid_lifecycle"
    message = "Invalid lifecycle transition."


class TypeMismatch(Exception):
    code = "type_mismatch"
    message = "Operation not allowed for this title type."


# ---- Helpers -----------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _title_snapshot(t: Title) -> dict[str, Any]:
    """Minimal audit snapshot — keep small + portable."""
    return {
        "id": t.id,
        "slug": t.slug,
        "type": t.type,
        "title": t.title,
        "status": t.status,
        "publish_at": t.publish_at.isoformat() if t.publish_at else None,
        "published_at": t.published_at.isoformat() if t.published_at else None,
        "age_rating": t.age_rating,
        "runtime_minutes": t.runtime_minutes,
    }


def _episode_snapshot(e: Episode) -> dict[str, Any]:
    return {
        "id": e.id,
        "season_id": e.season_id,
        "episode_number": e.episode_number,
        "name": e.name,
        "status": e.status,
        "publish_at": e.publish_at.isoformat() if e.publish_at else None,
    }


async def _resolve_genres(db: AsyncSession, slugs: list[str]) -> list[Genre]:
    if not slugs:
        return []
    return list((await db.scalars(select(Genre).where(Genre.slug.in_(slugs)))).all())


# ---- Title CRUD --------------------------------------------------------------


async def create_title(
    db: AsyncSession, actor: User, payload: dict, *, request_id: str | None = None
) -> Title:
    existing = await db.scalar(select(Title).where(Title.slug == payload["slug"]))
    if existing is not None:
        raise SlugInUse

    genre_slugs = payload.pop("genre_slugs", []) or []
    hls_url = payload.pop("hls_manifest_url", None)

    title = Title(**payload)
    if title.status == "published" and title.published_at is None:
        title.published_at = _now()
    title.genres = await _resolve_genres(db, genre_slugs)
    db.add(title)
    await db.flush()

    if hls_url:
        db.add(TitleAsset(title_id=title.id, kind="hls_manifest", storage_url=hls_url))
        await db.flush()
    await db.refresh(title, attribute_names=["assets", "genres", "seasons", "audio_tracks", "subtitle_tracks", "credits"])

    await audit_svc.record(
        db,
        actor=actor,
        action="title.create",
        entity_type="title",
        entity_id=title.id,
        after=_title_snapshot(title),
        request_id=request_id,
    )
    return title


async def update_title(
    db: AsyncSession,
    actor: User,
    title_id: int,
    patch: dict,
    *,
    request_id: str | None = None,
) -> Title:
    title = await db.get(Title, title_id)
    if title is None or title.deleted_at is not None:
        raise TitleNotFound
    before = _title_snapshot(title)

    genre_slugs = patch.pop("genre_slugs", None)
    hls_url = patch.pop("hls_manifest_url", None)

    for k, v in patch.items():
        if v is not None:
            setattr(title, k, v)

    if genre_slugs is not None:
        title.genres = await _resolve_genres(db, genre_slugs)
    if hls_url is not None:
        # Replace any existing hls_manifest asset
        await db.execute(
            delete(TitleAsset).where(
                TitleAsset.title_id == title.id, TitleAsset.kind == "hls_manifest"
            )
        )
        db.add(TitleAsset(title_id=title.id, kind="hls_manifest", storage_url=hls_url))

    await db.flush()
    await db.refresh(title, attribute_names=["assets", "genres", "audio_tracks", "subtitle_tracks", "credits", "seasons"])

    await audit_svc.record(
        db, actor=actor, action="title.update", entity_type="title",
        entity_id=title.id, before=before, after=_title_snapshot(title),
        request_id=request_id,
    )
    return title


async def _transition_title(
    db: AsyncSession,
    actor: User,
    title_id: int,
    new_status: str,
    *,
    publish_at: datetime | None = None,
    request_id: str | None = None,
) -> Title:
    title = await db.get(Title, title_id)
    if title is None or title.deleted_at is not None:
        raise TitleNotFound
    before = _title_snapshot(title)

    if new_status == "scheduled":
        if publish_at is None:
            raise InvalidLifecycle
        title.status = "scheduled"
        title.publish_at = publish_at
    elif new_status == "published":
        title.status = "published"
        title.published_at = _now()
        title.publish_at = None
    elif new_status == "archived":
        title.status = "archived"
    elif new_status == "removed":
        title.status = "removed"
    else:
        raise InvalidLifecycle

    await db.flush()

    await audit_svc.record(
        db, actor=actor, action=f"title.{new_status}", entity_type="title",
        entity_id=title.id, before=before, after=_title_snapshot(title),
        request_id=request_id,
    )
    return title


async def publish_title(db, actor, title_id, *, request_id=None):
    return await _transition_title(db, actor, title_id, "published", request_id=request_id)


async def schedule_title(db, actor, title_id, *, publish_at, request_id=None):
    return await _transition_title(
        db, actor, title_id, "scheduled", publish_at=publish_at, request_id=request_id
    )


async def archive_title(db, actor, title_id, *, request_id=None):
    return await _transition_title(db, actor, title_id, "archived", request_id=request_id)


async def soft_delete_title(
    db: AsyncSession, actor: User, title_id: int, *, request_id: str | None = None
) -> None:
    title = await db.get(Title, title_id)
    if title is None or title.deleted_at is not None:
        raise TitleNotFound
    before = _title_snapshot(title)
    title.deleted_at = _now()
    title.status = "removed"
    await db.flush()
    await audit_svc.record(
        db, actor=actor, action="title.delete", entity_type="title",
        entity_id=title.id, before=before, request_id=request_id,
    )


# ---- Seasons -----------------------------------------------------------------


async def create_season(
    db: AsyncSession, actor: User, title_id: int, payload: dict,
    *, request_id: str | None = None,
) -> Season:
    title = await db.get(Title, title_id)
    if title is None or title.deleted_at is not None:
        raise TitleNotFound
    if title.type != "series":
        raise TypeMismatch
    season = Season(title_id=title.id, **payload)
    db.add(season)
    await db.flush()
    await db.refresh(season, attribute_names=["episodes"])
    await audit_svc.record(
        db, actor=actor, action="season.create", entity_type="season",
        entity_id=season.id,
        after={"id": season.id, "title_id": season.title_id, "season_number": season.season_number},
        request_id=request_id,
    )
    return season


async def update_season(db, actor, season_id, patch, *, request_id=None):
    season = await db.get(Season, season_id)
    if season is None:
        raise SeasonNotFound
    before = {"id": season.id, "name": season.name, "season_number": season.season_number}
    for k, v in patch.items():
        if v is not None:
            setattr(season, k, v)
    await db.flush()
    await audit_svc.record(
        db, actor=actor, action="season.update", entity_type="season",
        entity_id=season.id, before=before,
        after={"id": season.id, "name": season.name, "season_number": season.season_number},
        request_id=request_id,
    )
    return season


async def delete_season(db, actor, season_id, *, request_id=None):
    season = await db.get(Season, season_id)
    if season is None:
        raise SeasonNotFound
    before = {"id": season.id, "season_number": season.season_number, "title_id": season.title_id}
    await db.delete(season)
    await db.flush()
    await audit_svc.record(
        db, actor=actor, action="season.delete", entity_type="season",
        entity_id=before["id"], before=before, request_id=request_id,
    )


# ---- Episodes ----------------------------------------------------------------


async def create_episode(
    db: AsyncSession, actor: User, season_id: int, payload: dict,
    *, request_id: str | None = None,
) -> Episode:
    season = await db.get(Season, season_id)
    if season is None:
        raise SeasonNotFound

    hls_url = payload.pop("hls_manifest_url", None)
    publish_at = payload.get("publish_at")
    status = payload.get("status", "draft")
    if status == "scheduled" and publish_at is None:
        raise InvalidLifecycle

    ordinal = payload.get("ordinal", payload["episode_number"])
    ep = Episode(season_id=season.id, ordinal=ordinal, **payload)
    if ep.status == "published" and ep.published_at is None:
        ep.published_at = _now()
    db.add(ep)
    await db.flush()
    if hls_url:
        db.add(EpisodeAsset(episode_id=ep.id, kind="hls_manifest", storage_url=hls_url))
        await db.flush()
    await db.refresh(ep, attribute_names=["assets"])

    await audit_svc.record(
        db, actor=actor, action="episode.create", entity_type="episode",
        entity_id=ep.id, after=_episode_snapshot(ep), request_id=request_id,
    )
    return ep


async def update_episode(
    db: AsyncSession, actor: User, episode_id: int, patch: dict,
    *, request_id: str | None = None,
) -> Episode:
    ep = await db.get(Episode, episode_id)
    if ep is None:
        raise EpisodeNotFound
    before = _episode_snapshot(ep)

    hls_url = patch.pop("hls_manifest_url", None)
    for k, v in patch.items():
        if v is not None:
            setattr(ep, k, v)
    if hls_url is not None:
        await db.execute(
            delete(EpisodeAsset).where(
                EpisodeAsset.episode_id == ep.id, EpisodeAsset.kind == "hls_manifest"
            )
        )
        db.add(EpisodeAsset(episode_id=ep.id, kind="hls_manifest", storage_url=hls_url))

    await db.flush()
    await db.refresh(ep, attribute_names=["assets"])

    await audit_svc.record(
        db, actor=actor, action="episode.update", entity_type="episode",
        entity_id=ep.id, before=before, after=_episode_snapshot(ep),
        request_id=request_id,
    )
    return ep


async def publish_episode(db, actor, episode_id, *, request_id=None):
    ep = await db.get(Episode, episode_id)
    if ep is None:
        raise EpisodeNotFound
    before = _episode_snapshot(ep)
    ep.status = "published"
    ep.published_at = _now()
    ep.publish_at = None
    await db.flush()
    await audit_svc.record(
        db, actor=actor, action="episode.publish", entity_type="episode",
        entity_id=ep.id, before=before, after=_episode_snapshot(ep),
        request_id=request_id,
    )
    return ep


async def delete_episode(db, actor, episode_id, *, request_id=None):
    ep = await db.get(Episode, episode_id)
    if ep is None:
        raise EpisodeNotFound
    before = _episode_snapshot(ep)
    await db.delete(ep)
    await db.flush()
    await audit_svc.record(
        db, actor=actor, action="episode.delete", entity_type="episode",
        entity_id=before["id"], before=before, request_id=request_id,
    )


# ---- Genres ------------------------------------------------------------------


async def create_genre(db, actor, payload: dict, *, request_id=None) -> Genre:
    existing = await db.scalar(select(Genre).where(Genre.slug == payload["slug"]))
    if existing is not None:
        raise GenreSlugInUse
    g = Genre(**payload)
    db.add(g)
    await db.flush()
    await audit_svc.record(
        db, actor=actor, action="genre.create", entity_type="genre",
        entity_id=g.id, after={"id": g.id, "slug": g.slug, "name": g.name},
        request_id=request_id,
    )
    return g


async def list_genres_admin(db) -> list[Genre]:
    return list((await db.scalars(select(Genre).order_by(Genre.kind, Genre.name))).all())


# ---- Audio + subtitle tracks (replace-all semantics) -------------------------


async def replace_audio_tracks(db, actor, title_id, tracks: list[dict], *, request_id=None):
    title = await db.get(Title, title_id)
    if title is None or title.deleted_at is not None:
        raise TitleNotFound
    await db.execute(delete(AudioTrack).where(AudioTrack.title_id == title_id))
    for t in tracks:
        db.add(AudioTrack(title_id=title_id, **t))
    await db.flush()
    await audit_svc.record(
        db, actor=actor, action="title.audio_tracks_replace", entity_type="title",
        entity_id=title_id, after={"tracks": tracks}, request_id=request_id,
    )


async def replace_subtitle_tracks(db, actor, title_id, tracks: list[dict], *, request_id=None):
    title = await db.get(Title, title_id)
    if title is None or title.deleted_at is not None:
        raise TitleNotFound
    await db.execute(delete(SubtitleTrack).where(SubtitleTrack.title_id == title_id))
    for t in tracks:
        db.add(SubtitleTrack(title_id=title_id, **t))
    await db.flush()
    await audit_svc.record(
        db, actor=actor, action="title.subtitle_tracks_replace", entity_type="title",
        entity_id=title_id, after={"tracks": tracks}, request_id=request_id,
    )


# ---- Users (admin role only — gating done in route) --------------------------


async def list_users(db, *, page: int = 1, page_size: int = 50) -> tuple[list[User], int]:
    page = max(1, page)
    page_size = max(1, min(200, page_size))
    items = list(
        (
            await db.scalars(
                select(User).order_by(User.id).offset((page - 1) * page_size).limit(page_size)
            )
        ).all()
    )
    total = (await db.scalar(select(func.count()).select_from(User))) or 0
    return items, int(total)


async def change_user_role(
    db: AsyncSession, actor: User, user_id: int, *, new_role: str, request_id: str | None = None
) -> User:
    target = await db.get(User, user_id)
    if target is None:
        raise TitleNotFound  # using a generic 404; route maps to 404

    before = {"id": target.id, "email": target.email, "role": target.role}
    if new_role not in {"user", "viewer", "content_manager", "admin"}:
        raise InvalidLifecycle  # repurposed — route maps to 400

    target.role = new_role
    # Bump session_version so existing JWTs become invalid (forces re-login with fresh role claim)
    target.session_version += 1
    await db.flush()
    await audit_svc.record(
        db, actor=actor, action="user.role_change", entity_type="user",
        entity_id=target.id, before=before,
        after={"id": target.id, "email": target.email, "role": target.role},
        request_id=request_id,
    )
    return target
