"""
Admin routes — titles + seasons + episodes + genres + tracks + users + audit.

Role gating:
- All catalog writes require `content_manager` or `admin` (ContentRoleUser dep).
- User management requires `admin` only (AdminUser dep).
"""
from __future__ import annotations

from fastapi import APIRouter, File, Header, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel

from app.api.deps import AdminUser, ContentRoleUser, DbSession
from app.models.episode import Episode, EpisodeAsset
from app.models.title import Title, TitleAsset
from app.services import storage as storage_svc
from sqlalchemy import delete as sa_delete
from app.schemas.audit import AuditEntry, AuditListResponse, UserRoleChange
from app.schemas.title import (
    AudioTrackRead,
    AudioTracksReplace,
    EpisodeCreate,
    EpisodeRead,
    EpisodeUpdate,
    GenreCreate,
    GenreRead,
    SeasonCreate,
    SeasonDetail,
    SeasonUpdate,
    SubtitleTrackRead,
    SubtitleTracksReplace,
    TitleCreate,
    TitleDetail,
    TitleSchedule,
    TitleUpdate,
)
from app.schemas.user import UserRead
from app.services import admin as svc
from app.services import audit as audit_svc


def _bust_catalog_caches() -> None:
    """Clear every public read cache after any catalog mutation: title list +
    detail + season detail, genres, and the home rows (which embed title
    summaries). Imports are lazy so this file doesn't depend on the public
    router order. Without this, users watch stale data persist for up to
    5 minutes after a publish / upload / edit."""
    from app.api.v1.titles import invalidate_titles_cache
    from app.api.v1.home import invalidate_genres_cache
    from app.services.browse import invalidate_home_cache

    invalidate_titles_cache()
    invalidate_genres_cache()
    invalidate_home_cache()

router = APIRouter()


def _err(exc, code: int) -> HTTPException:
    return HTTPException(
        status_code=code,
        detail={"error": {"code": exc.code, "message": exc.message}},
    )


def _req_id(request: Request) -> str | None:
    return request.headers.get("x-request-id")


# ---- Titles ------------------------------------------------------------------


@router.post(
    "/titles",
    response_model=TitleDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_title(
    payload: TitleCreate, request: Request, db: DbSession, actor: ContentRoleUser
) -> TitleDetail:
    try:
        t = await svc.create_title(db, actor, payload.model_dump(), request_id=_req_id(request))
    except svc.SlugInUse as e:
        raise _err(e, 409) from e
    _bust_catalog_caches()
    from app.api.v1.titles import _title_to_detail

    return _title_to_detail(t)


@router.get("/titles/{title_id}", response_model=TitleDetail)
async def get_title_for_admin(
    title_id: int, db: DbSession, actor: ContentRoleUser
) -> TitleDetail:
    """Admin-scoped title detail. Returns drafts + scheduled titles too — the
    public /v1/titles/:id endpoint 404s on those, which broke the editor for
    just-created drafts. With this route the upload + subtitle cards can render
    for a brand-new draft without requiring publish-first."""
    from app.api.v1.titles import _title_to_detail
    from app.services import catalog as catalog_svc

    try:
        t = await catalog_svc.get_title_admin(db, title_id)
    except catalog_svc.TitleNotFound as e:
        raise _err(e, 404) from e
    return _title_to_detail(t)


@router.patch("/titles/{title_id}", response_model=TitleDetail)
async def update_title(
    title_id: int,
    payload: TitleUpdate,
    request: Request,
    db: DbSession,
    actor: ContentRoleUser,
) -> TitleDetail:
    try:
        t = await svc.update_title(
            db, actor, title_id, payload.model_dump(exclude_unset=True), request_id=_req_id(request)
        )
    except svc.TitleNotFound as e:
        raise _err(e, 404) from e
    _bust_catalog_caches()
    from app.api.v1.titles import _title_to_detail

    return _title_to_detail(t)


@router.post("/titles/{title_id}/publish", response_model=TitleDetail)
async def publish_title(
    title_id: int, request: Request, db: DbSession, actor: ContentRoleUser
) -> TitleDetail:
    try:
        t = await svc.publish_title(db, actor, title_id, request_id=_req_id(request))
    except svc.TitleNotFound as e:
        raise _err(e, 404) from e
    _bust_catalog_caches()
    from app.api.v1.titles import _title_to_detail

    return _title_to_detail(t)


@router.post("/titles/{title_id}/schedule", response_model=TitleDetail)
async def schedule_title(
    title_id: int,
    payload: TitleSchedule,
    request: Request,
    db: DbSession,
    actor: ContentRoleUser,
) -> TitleDetail:
    try:
        t = await svc.schedule_title(
            db, actor, title_id, publish_at=payload.publish_at, request_id=_req_id(request)
        )
    except svc.TitleNotFound as e:
        raise _err(e, 404) from e
    except svc.InvalidLifecycle as e:
        raise _err(e, 400) from e
    _bust_catalog_caches()
    from app.api.v1.titles import _title_to_detail

    return _title_to_detail(t)


@router.post("/titles/{title_id}/archive", response_model=TitleDetail)
async def archive_title(
    title_id: int, request: Request, db: DbSession, actor: ContentRoleUser
) -> TitleDetail:
    try:
        t = await svc.archive_title(db, actor, title_id, request_id=_req_id(request))
    except svc.TitleNotFound as e:
        raise _err(e, 404) from e
    _bust_catalog_caches()
    from app.api.v1.titles import _title_to_detail

    return _title_to_detail(t)


@router.delete("/titles/{title_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_title(
    title_id: int, request: Request, db: DbSession, actor: ContentRoleUser
) -> None:
    try:
        await svc.soft_delete_title(db, actor, title_id, request_id=_req_id(request))
    except svc.TitleNotFound as e:
        raise _err(e, 404) from e
    _bust_catalog_caches()


# ---- Seasons -----------------------------------------------------------------


@router.post(
    "/titles/{title_id}/seasons",
    response_model=SeasonDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_season(
    title_id: int,
    payload: SeasonCreate,
    request: Request,
    db: DbSession,
    actor: ContentRoleUser,
) -> SeasonDetail:
    try:
        s = await svc.create_season(
            db, actor, title_id, payload.model_dump(), request_id=_req_id(request)
        )
    except svc.TitleNotFound as e:
        raise _err(e, 404) from e
    except svc.TypeMismatch as e:
        raise _err(e, 409) from e
    _bust_catalog_caches()
    return SeasonDetail.model_validate(s)


@router.patch("/seasons/{season_id}", response_model=SeasonDetail)
async def update_season(
    season_id: int,
    payload: SeasonUpdate,
    request: Request,
    db: DbSession,
    actor: ContentRoleUser,
) -> SeasonDetail:
    try:
        s = await svc.update_season(
            db, actor, season_id, payload.model_dump(exclude_unset=True), request_id=_req_id(request)
        )
    except svc.SeasonNotFound as e:
        raise _err(e, 404) from e
    _bust_catalog_caches()
    return SeasonDetail.model_validate(s)


@router.delete("/seasons/{season_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_season(
    season_id: int, request: Request, db: DbSession, actor: ContentRoleUser
) -> None:
    try:
        await svc.delete_season(db, actor, season_id, request_id=_req_id(request))
    except svc.SeasonNotFound as e:
        raise _err(e, 404) from e
    _bust_catalog_caches()


# ---- Episodes ----------------------------------------------------------------


@router.post(
    "/seasons/{season_id}/episodes",
    response_model=EpisodeRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_episode(
    season_id: int,
    payload: EpisodeCreate,
    request: Request,
    db: DbSession,
    actor: ContentRoleUser,
) -> EpisodeRead:
    try:
        ep = await svc.create_episode(
            db, actor, season_id, payload.model_dump(), request_id=_req_id(request)
        )
    except svc.SeasonNotFound as e:
        raise _err(e, 404) from e
    except svc.InvalidLifecycle as e:
        raise _err(e, 400) from e
    _bust_catalog_caches()
    return EpisodeRead.model_validate(ep)


@router.patch("/episodes/{episode_id}", response_model=EpisodeRead)
async def update_episode(
    episode_id: int,
    payload: EpisodeUpdate,
    request: Request,
    db: DbSession,
    actor: ContentRoleUser,
) -> EpisodeRead:
    try:
        ep = await svc.update_episode(
            db, actor, episode_id, payload.model_dump(exclude_unset=True), request_id=_req_id(request)
        )
    except svc.EpisodeNotFound as e:
        raise _err(e, 404) from e
    _bust_catalog_caches()
    return EpisodeRead.model_validate(ep)


@router.post("/episodes/{episode_id}/publish", response_model=EpisodeRead)
async def publish_episode(
    episode_id: int, request: Request, db: DbSession, actor: ContentRoleUser
) -> EpisodeRead:
    try:
        ep = await svc.publish_episode(db, actor, episode_id, request_id=_req_id(request))
    except svc.EpisodeNotFound as e:
        raise _err(e, 404) from e
    _bust_catalog_caches()
    return EpisodeRead.model_validate(ep)


@router.delete("/episodes/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode(
    episode_id: int, request: Request, db: DbSession, actor: ContentRoleUser
) -> None:
    try:
        await svc.delete_episode(db, actor, episode_id, request_id=_req_id(request))
    except svc.EpisodeNotFound as e:
        raise _err(e, 404) from e
    _bust_catalog_caches()


# ---- Genres ------------------------------------------------------------------


@router.post("/genres", response_model=GenreRead, status_code=status.HTTP_201_CREATED)
async def create_genre(
    payload: GenreCreate, request: Request, db: DbSession, actor: ContentRoleUser
) -> GenreRead:
    try:
        g = await svc.create_genre(db, actor, payload.model_dump(), request_id=_req_id(request))
    except svc.GenreSlugInUse as e:
        raise _err(e, 409) from e
    _bust_catalog_caches()
    return GenreRead.model_validate(g)


@router.get("/genres", response_model=list[GenreRead])
async def list_admin_genres(db: DbSession, _: ContentRoleUser) -> list[GenreRead]:
    items = await svc.list_genres_admin(db)
    return [GenreRead.model_validate(g) for g in items]


# ---- Video upload (R2) ------------------------------------------------------


# Limit: 1 GB per upload to protect process memory. Storage free tiers are
# 10 GB total so this is plenty for dev. Production deploys may bump this on
# the LB+nginx side too.
_MAX_UPLOAD_BYTES = 1024 * 1024 * 1024

_ALLOWED_VIDEO_EXTS = {".mp4", ".m4v", ".mov", ".webm", ".m3u8"}
_ALLOWED_VIDEO_MIMES = {
    "video/mp4",
    "video/quicktime",
    "video/x-m4v",
    "video/webm",
    "application/vnd.apple.mpegurl",
    "application/x-mpegurl",
    "application/octet-stream",  # some browsers send this for video
}


def _ensure_storage() -> None:
    if not storage_svc.is_configured():
        raise HTTPException(
            503,
            detail={
                "error": {
                    "code": storage_svc.StorageNotConfigured.code,
                    "message": storage_svc.StorageNotConfigured.message,
                }
            },
        )


def _is_video_container(head: bytes, ext: str) -> bool:
    """Inspect the first ~32 bytes of an upload to confirm it's actually a
    known video container — defends against PE/ELF/script payloads renamed
    with a video extension.

    Recognises:
      - ISO BMFF (MP4 / MOV / M4V): bytes 4-8 == 'ftyp'
      - WebM / Matroska: starts with EBML header 1A 45 DF A3
    Other formats fall through and are rejected.
    """
    if len(head) < 8:
        return False
    # ISO BMFF — first 4 bytes are the box size (any value), bytes 4-8 are "ftyp"
    if head[4:8] == b"ftyp":
        return True
    # EBML / WebM / Matroska
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return ext in {".webm"}
    return False


def _raw_ext(filename: str | None) -> str:
    """Strict extension lookup — returns raw ext or empty string.
    Differs from _ext_of (which coerces to .mp4 for storage-key safety).
    Use this for VALIDATION, _ext_of() for KEY-NAMING."""
    if not filename:
        return ""
    dot = filename.rfind(".")
    if dot < 0:
        return ""
    return filename[dot:].lower()


def _validate_upload(file) -> None:
    """Sniff filename + content-type + first 32 bytes. The byte sniff is the
    defense-in-depth check — a malicious upload with a `.mp4` filename and
    a fake `video/mp4` content-type but PE/ELF/script bytes inside would pass
    the first two checks. We peek the head, validate it's a known video
    container, then rewind the stream so the actual upload reads from byte 0.
    """
    ext = _raw_ext(file.filename)
    if not ext or ext not in _ALLOWED_VIDEO_EXTS:
        raise HTTPException(
            415,
            detail={
                "error": {
                    "code": "unsupported_media",
                    "message": f"Extension '{ext or '(none)'}' is not allowed. Allowed: {sorted(_ALLOWED_VIDEO_EXTS)}",
                }
            },
        )

    # Magic-byte sniff (32 bytes covers every container we accept).
    # Skip for .m3u8 (a manifest is plain text starting with #EXTM3U).
    if ext != ".m3u8":
        head = file.file.read(32)
        file.file.seek(0)
        if not _is_video_container(head, ext):
            raise HTTPException(
                415,
                detail={
                    "error": {
                        "code": "content_mismatch",
                        "message": "File contents don't match a recognised video container. Magic bytes failed validation.",
                    }
                },
            )
    else:
        head = file.file.read(8)
        file.file.seek(0)
        if not head.startswith(b"#EXTM3U"):
            raise HTTPException(
                415,
                detail={
                    "error": {
                        "code": "content_mismatch",
                        "message": "File doesn't look like an HLS manifest (#EXTM3U missing).",
                    }
                },
            )

    if file.content_type and file.content_type not in _ALLOWED_VIDEO_MIMES:
        raise HTTPException(
            415,
            detail={
                "error": {
                    "code": "unsupported_media",
                    "message": f"Content-Type '{file.content_type}' is not allowed.",
                }
            },
        )


async def _safe_upload(
    *, key: str, file_obj: "_SizeLimitedStream", content_type: str
) -> str:
    """Wraps storage_svc.aupload_fileobj so an `_UploadTooLarge` raised inside
    the boto3 worker thread surfaces as an HTTP 413 instead of a 500. boto3
    wraps the inner exception in S3UploadFailedError — we unwrap and check."""
    try:
        return await storage_svc.aupload_fileobj(
            key=key, file_obj=file_obj, content_type=content_type
        )
    except _UploadTooLarge as exc:
        raise HTTPException(
            413,
            detail={
                "error": {
                    "code": "payload_too_large",
                    "message": f"Upload exceeds the {exc.limit_bytes // (1024 * 1024)} MB limit.",
                }
            },
        ) from exc
    except Exception as exc:
        # boto3's S3UploadFailedError carries the original exception in .args
        for arg in getattr(exc, "args", ()):
            if isinstance(arg, _UploadTooLarge):
                raise HTTPException(
                    413,
                    detail={
                        "error": {
                            "code": "payload_too_large",
                            "message": f"Upload exceeds the {arg.limit_bytes // (1024 * 1024)} MB limit.",
                        }
                    },
                ) from exc
        raise


class _UploadTooLarge(Exception):
    """Raised mid-stream when an upload exceeds its byte cap. We raise a plain
    Python exception (not HTTPException) because boto3.upload_fileobj reads the
    stream inside a worker thread — an HTTPException there gets wrapped by
    botocore and surfaces as a generic 500 instead of the 413 we want.
    The route handler catches this and emits the right HTTP response."""

    def __init__(self, limit_bytes: int):
        self.limit_bytes = limit_bytes


class _SizeLimitedStream:
    """Wraps an UploadFile.file (SpooledTemporaryFile) and raises if total read
    bytes exceed the limit. boto3.upload_fileobj reads in chunks so the limit
    triggers early — we don't have to buffer the whole upload."""

    def __init__(self, stream, max_bytes: int):
        self._stream = stream
        self._max = max_bytes
        self._read = 0

    def read(self, n: int = -1):
        chunk = self._stream.read(n)
        if not chunk:
            return chunk
        self._read += len(chunk)
        if self._read > self._max:
            raise _UploadTooLarge(self._max)
        return chunk

    # boto3 may also call .seek / .tell / .close on the stream (it does for
    # multipart uploads). Pass them through.
    def seek(self, *a, **kw):
        return self._stream.seek(*a, **kw)

    def tell(self):
        return self._stream.tell()

    def close(self):
        return self._stream.close()

    @property
    def closed(self):
        return getattr(self._stream, "closed", False)


@router.post("/titles/{title_id}/upload-video")
async def upload_title_video(
    title_id: int,
    request: Request,
    db: DbSession,
    actor: ContentRoleUser,
    file: UploadFile = File(...),
) -> dict:
    _ensure_storage()
    title = await db.get(Title, title_id)
    if title is None or title.deleted_at is not None:
        raise HTTPException(
            404, detail={"error": {"code": "title_not_found", "message": "Title not found."}}
        )
    if title.type != "movie":
        raise HTTPException(
            409,
            detail={
                "error": {
                    "code": "type_mismatch",
                    "message": "Use the episode upload endpoint for series.",
                }
            },
        )

    _validate_upload(file)
    # Stream into storage with a hard size limit (raises 413 mid-stream if exceeded).
    key = f"titles/{title_id}/master{_ext_of(file.filename)}"
    stored_ref = await _safe_upload(
        key=key,
        file_obj=_SizeLimitedStream(file.file, _MAX_UPLOAD_BYTES),
        content_type=file.content_type or "video/mp4",
    )

    # Replace any existing hls_manifest pointer
    await db.execute(
        sa_delete(TitleAsset).where(
            TitleAsset.title_id == title.id, TitleAsset.kind == "hls_manifest"
        )
    )
    db.add(TitleAsset(title_id=title.id, kind="hls_manifest", storage_url=stored_ref))
    await db.flush()

    await audit_svc.record(
        db,
        actor=actor,
        action="title.upload_video",
        entity_type="title",
        entity_id=title.id,
        after={"storage_url": stored_ref, "key": key},
        request_id=_req_id(request),
    )
    _bust_catalog_caches()
    return {
        "title_id": title.id,
        "key": key,
        "stored_ref": stored_ref,
        "playable_url": storage_svc.resolve_url(stored_ref),
    }


@router.post("/episodes/{episode_id}/upload-video")
async def upload_episode_video(
    episode_id: int,
    request: Request,
    db: DbSession,
    actor: ContentRoleUser,
    file: UploadFile = File(...),
) -> dict:
    _ensure_storage()
    ep = await db.get(Episode, episode_id)
    if ep is None:
        raise HTTPException(
            404, detail={"error": {"code": "episode_not_found", "message": "Episode not found."}}
        )

    _validate_upload(file)
    key = f"episodes/{episode_id}/master{_ext_of(file.filename)}"
    stored_ref = await _safe_upload(
        key=key,
        file_obj=_SizeLimitedStream(file.file, _MAX_UPLOAD_BYTES),
        content_type=file.content_type or "video/mp4",
    )

    await db.execute(
        sa_delete(EpisodeAsset).where(
            EpisodeAsset.episode_id == ep.id, EpisodeAsset.kind == "hls_manifest"
        )
    )
    db.add(EpisodeAsset(episode_id=ep.id, kind="hls_manifest", storage_url=stored_ref))
    await db.flush()

    await audit_svc.record(
        db,
        actor=actor,
        action="episode.upload_video",
        entity_type="episode",
        entity_id=ep.id,
        after={"storage_url": stored_ref, "key": key},
        request_id=_req_id(request),
    )
    _bust_catalog_caches()
    return {
        "episode_id": ep.id,
        "key": key,
        "stored_ref": stored_ref,
        "playable_url": storage_svc.resolve_url(stored_ref),
    }


def _ext_of(filename: str | None) -> str:
    if not filename:
        return ".mp4"
    dot = filename.rfind(".")
    if dot < 0 or dot >= len(filename) - 1:
        return ".mp4"
    ext = filename[dot:].lower()
    # whitelist; defaults to .mp4 to avoid weird trailing strings
    return ext if ext in {".mp4", ".m4v", ".mov", ".webm", ".m3u8"} else ".mp4"


# ---- Subtitle upload (.vtt sidecar) ------------------------------------------

# WebVTT only. SRT can be converted client-side or server-side; we keep this
# endpoint strict so the player doesn't have to deal with conversion.
_ALLOWED_SUBTITLE_EXTS = {".vtt"}
_ALLOWED_SUBTITLE_MIMES = {"text/vtt", "text/plain", "application/octet-stream"}
_MAX_SUBTITLE_BYTES = 5 * 1024 * 1024  # 5 MB — even feature-length .vtt is well under


def _validate_subtitle(file: UploadFile) -> None:
    ext = _raw_ext(file.filename)
    if not ext or ext not in _ALLOWED_SUBTITLE_EXTS:
        raise HTTPException(
            422,
            detail={
                "error": {
                    "code": "subtitle_extension_not_allowed",
                    "message": "Only .vtt subtitle files are accepted. Convert .srt before upload.",
                }
            },
        )
    if file.content_type and file.content_type not in _ALLOWED_SUBTITLE_MIMES:
        raise HTTPException(
            415,
            detail={
                "error": {
                    "code": "subtitle_mime_not_allowed",
                    "message": f"Unexpected content-type '{file.content_type}'.",
                }
            },
        )


async def _store_subtitle(
    db: DbSession,
    file: UploadFile,
    *,
    title_id: int | None,
    episode_id: int | None,
    language: str,
    kind: str,
    forced: bool,
    label: str | None,
    actor,
    request: Request,
) -> dict:
    """Shared write path for title + episode subtitle uploads.

    Side effects:
      - Streams .vtt into storage at a deterministic key
      - Upserts the SubtitleTrack row (same language replaces previous)
      - Writes an audit log entry
    """
    from app.models.language import SubtitleTrack

    _ensure_storage()
    _validate_subtitle(file)

    owner_kind = "titles" if title_id is not None else "episodes"
    owner_id = title_id if title_id is not None else episode_id
    key = f"{owner_kind}/{owner_id}/subtitles/{language}.vtt"
    stored_ref = await _safe_upload(
        key=key,
        file_obj=_SizeLimitedStream(file.file, _MAX_SUBTITLE_BYTES),
        content_type="text/vtt",
    )

    # Upsert by (owner, language) — uploading the same language twice replaces
    # the previous file instead of stacking duplicates.
    if title_id is not None:
        await db.execute(
            sa_delete(SubtitleTrack).where(
                SubtitleTrack.title_id == title_id,
                SubtitleTrack.language == language,
            )
        )
    else:
        await db.execute(
            sa_delete(SubtitleTrack).where(
                SubtitleTrack.episode_id == episode_id,
                SubtitleTrack.language == language,
            )
        )
    track = SubtitleTrack(
        title_id=title_id,
        episode_id=episode_id,
        language=language,
        kind=kind,
        forced=forced,
        storage_url=stored_ref,
        label=label,
    )
    db.add(track)
    await db.flush()

    await audit_svc.record(
        db,
        actor=actor,
        action="subtitle.upload",
        entity_type=owner_kind[:-1],  # "title" or "episode"
        entity_id=owner_id or 0,
        after={"language": language, "kind": kind, "storage_url": stored_ref, "key": key},
        request_id=_req_id(request),
    )
    _bust_catalog_caches()

    return {
        "id": track.id,
        "title_id": track.title_id,
        "episode_id": track.episode_id,
        "language": track.language,
        "kind": track.kind,
        "forced": track.forced,
        "label": track.label,
        "storage_url": stored_ref,
        "playable_url": storage_svc.resolve_url(stored_ref),
    }


@router.post("/titles/{title_id}/subtitles")
async def upload_title_subtitle(
    title_id: int,
    request: Request,
    db: DbSession,
    actor: ContentRoleUser,
    file: UploadFile = File(...),
    language: str = Query(..., min_length=2, max_length=8, description="ISO 639-1 / BCP-47, e.g. en, ta, hi"),
    kind: str = Query("subtitle", pattern="^(subtitle|cc|sdh|dubtitle)$"),
    forced: bool = Query(False),
    label: str | None = Query(None, max_length=64),
) -> dict:
    title = await db.get(Title, title_id)
    if title is None or title.deleted_at is not None:
        raise HTTPException(
            404, detail={"error": {"code": "title_not_found", "message": "Title not found."}}
        )
    return await _store_subtitle(
        db,
        file,
        title_id=title.id,
        episode_id=None,
        language=language,
        kind=kind,
        forced=forced,
        label=label,
        actor=actor,
        request=request,
    )


@router.post("/episodes/{episode_id}/subtitles")
async def upload_episode_subtitle(
    episode_id: int,
    request: Request,
    db: DbSession,
    actor: ContentRoleUser,
    file: UploadFile = File(...),
    language: str = Query(..., min_length=2, max_length=8),
    kind: str = Query("subtitle", pattern="^(subtitle|cc|sdh|dubtitle)$"),
    forced: bool = Query(False),
    label: str | None = Query(None, max_length=64),
) -> dict:
    ep = await db.get(Episode, episode_id)
    if ep is None:
        raise HTTPException(
            404, detail={"error": {"code": "episode_not_found", "message": "Episode not found."}}
        )
    return await _store_subtitle(
        db,
        file,
        title_id=None,
        episode_id=ep.id,
        language=language,
        kind=kind,
        forced=forced,
        label=label,
        actor=actor,
        request=request,
    )


@router.delete("/subtitles/{subtitle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subtitle(
    subtitle_id: int,
    request: Request,
    db: DbSession,
    actor: ContentRoleUser,
) -> None:
    """Remove a subtitle track. We delete the DB row only — the .vtt object
    is left in storage to make undo possible (object storage is cheap;
    cleaning up belongs to a separate batch job)."""
    from app.models.language import SubtitleTrack

    track = await db.get(SubtitleTrack, subtitle_id)
    if track is None:
        raise HTTPException(
            404, detail={"error": {"code": "subtitle_not_found", "message": "Subtitle not found."}}
        )
    await db.delete(track)
    await audit_svc.record(
        db,
        actor=actor,
        action="subtitle.delete",
        entity_type="subtitle",
        entity_id=subtitle_id,
        request_id=_req_id(request),
    )
    _bust_catalog_caches()


# ---- Tracks (audio + subtitle) ----------------------------------------------


@router.put("/titles/{title_id}/audio-tracks")
async def replace_audio_tracks(
    title_id: int,
    payload: AudioTracksReplace,
    request: Request,
    db: DbSession,
    actor: ContentRoleUser,
) -> dict:
    try:
        await svc.replace_audio_tracks(
            db, actor, title_id, [t.model_dump() for t in payload.tracks], request_id=_req_id(request)
        )
    except svc.TitleNotFound as e:
        raise _err(e, 404) from e
    _bust_catalog_caches()
    return {"updated": True, "count": len(payload.tracks)}


@router.put("/titles/{title_id}/subtitle-tracks")
async def replace_subtitle_tracks(
    title_id: int,
    payload: SubtitleTracksReplace,
    request: Request,
    db: DbSession,
    actor: ContentRoleUser,
) -> dict:
    try:
        await svc.replace_subtitle_tracks(
            db, actor, title_id, [t.model_dump() for t in payload.tracks], request_id=_req_id(request)
        )
    except svc.TitleNotFound as e:
        raise _err(e, 404) from e
    _bust_catalog_caches()
    return {"updated": True, "count": len(payload.tracks)}


# ---- Users (admin only) ------------------------------------------------------


class UserListResponse(BaseModel):
    items: list[UserRead]
    page: int
    page_size: int
    total: int


@router.get("/users", response_model=UserListResponse)
async def list_users(
    db: DbSession,
    _: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> UserListResponse:
    items, total = await svc.list_users(db, page=page, page_size=page_size)
    return UserListResponse(
        items=[UserRead.model_validate(u) for u in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.patch("/users/{user_id}/role", response_model=UserRead)
async def change_user_role(
    user_id: int,
    payload: UserRoleChange,
    request: Request,
    db: DbSession,
    actor: AdminUser,
) -> UserRead:
    try:
        u = await svc.change_user_role(
            db, actor, user_id, new_role=payload.role, request_id=_req_id(request)
        )
    except svc.TitleNotFound as e:
        # service re-used the exception class; semantics: target user not found
        raise HTTPException(
            404, detail={"error": {"code": "user_not_found", "message": "User not found."}}
        ) from e
    except svc.InvalidLifecycle as e:
        raise HTTPException(
            400,
            detail={"error": {"code": "invalid_role", "message": "Role must be user, viewer, content_manager, or admin."}},
        ) from e
    return UserRead.model_validate(u)


# ---- Audit log ---------------------------------------------------------------


@router.get("/audit", response_model=AuditListResponse)
async def list_audit(
    db: DbSession,
    _: AdminUser,
    entity_type: str | None = None,
    entity_id: int | None = None,
    actor_user_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> AuditListResponse:
    items, total = await audit_svc.list_entries(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        page=page,
        page_size=page_size,
    )
    return AuditListResponse(
        items=[AuditEntry.model_validate(i) for i in items],
        page=page,
        page_size=page_size,
        total=total,
    )
