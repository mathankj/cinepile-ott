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
    from app.api.v1.titles import _title_to_detail

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
    return SeasonDetail.model_validate(s)


@router.delete("/seasons/{season_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_season(
    season_id: int, request: Request, db: DbSession, actor: ContentRoleUser
) -> None:
    try:
        await svc.delete_season(db, actor, season_id, request_id=_req_id(request))
    except svc.SeasonNotFound as e:
        raise _err(e, 404) from e


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
    return EpisodeRead.model_validate(ep)


@router.post("/episodes/{episode_id}/publish", response_model=EpisodeRead)
async def publish_episode(
    episode_id: int, request: Request, db: DbSession, actor: ContentRoleUser
) -> EpisodeRead:
    try:
        ep = await svc.publish_episode(db, actor, episode_id, request_id=_req_id(request))
    except svc.EpisodeNotFound as e:
        raise _err(e, 404) from e
    return EpisodeRead.model_validate(ep)


@router.delete("/episodes/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode(
    episode_id: int, request: Request, db: DbSession, actor: ContentRoleUser
) -> None:
    try:
        await svc.delete_episode(db, actor, episode_id, request_id=_req_id(request))
    except svc.EpisodeNotFound as e:
        raise _err(e, 404) from e


# ---- Genres ------------------------------------------------------------------


@router.post("/genres", response_model=GenreRead, status_code=status.HTTP_201_CREATED)
async def create_genre(
    payload: GenreCreate, request: Request, db: DbSession, actor: ContentRoleUser
) -> GenreRead:
    try:
        g = await svc.create_genre(db, actor, payload.model_dump(), request_id=_req_id(request))
    except svc.GenreSlugInUse as e:
        raise _err(e, 409) from e
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
    """Sniff filename + content-type. Cheap rejection of clearly-wrong uploads."""
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
            raise HTTPException(
                413,
                detail={
                    "error": {
                        "code": "payload_too_large",
                        "message": f"Upload exceeds the {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
                    }
                },
            )
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
    stored_ref = await storage_svc.aupload_fileobj(
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
    stored_ref = await storage_svc.aupload_fileobj(
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
