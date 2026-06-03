"""
Object storage service — works with any S3-compatible provider
(Backblaze B2, Cloudflare R2, AWS S3, Storj, IDrive e2, etc.).

Storage URL convention:
- When uploaded to a PUBLIC bucket (STORAGE_PUBLIC_URL set): we store the full
  permanent URL on the asset row, no signing needed at play time.
- When uploaded to a PRIVATE bucket (STORAGE_PUBLIC_URL not set): we store the
  bucket KEY (e.g. "titles/5/master.mp4") on the asset row. The playback service
  calls resolve_url() to generate a short-lived presigned URL on each /play.
- For pre-seeded test streams (Big Buck Bunny etc.), the stored value is already
  a full https://... URL — resolve_url() returns it as-is.

Functions:
  is_configured()                              → bool — route layer 503s if False
  upload_fileobj(key, file_obj, content_type)  → stored reference (URL or key)
  delete(key)                                  → None
  resolve_url(stored_ref, ttl=...)             → playable URL (signs if needed)
  generate_presigned_url(key, ttl=...)         → presigned URL (lower-level)
"""
from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import BinaryIO

import boto3
from botocore.client import Config
from fastapi.concurrency import run_in_threadpool

from app.core.config import get_settings


class StorageNotConfigured(Exception):
    code = "storage_not_configured"
    message = "Object storage is not configured. Set STORAGE_* env vars."


def is_configured() -> bool:
    return get_settings().storage_configured()


@lru_cache
def _client():
    settings = get_settings()
    if not settings.storage_configured():
        raise StorageNotConfigured
    return boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint_url,
        aws_access_key_id=settings.storage_access_key_id,
        aws_secret_access_key=settings.storage_secret_access_key,
        # B2 + R2 both want 'auto' or a real AWS region; SigV4 required.
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def _public_url_for(key: str) -> str:
    """Build a public URL for a key when STORAGE_PUBLIC_URL is configured."""
    settings = get_settings()
    base = (settings.storage_public_url or "").rstrip("/")
    return f"{base}/{key}"


def upload_fileobj(
    *, key: str, file_obj: BinaryIO, content_type: str | None = None
) -> str:
    """Upload a file-like object (SYNC — call via run_in_threadpool from async).

    Returns the **stored reference** for asset.storage_url:
      - the full public URL if STORAGE_PUBLIC_URL is set
      - the bucket key itself otherwise (private bucket — playback signs at read time)

    This is the sync version used internally. Async routes should prefer
    `await aupload_fileobj(...)` which runs it on the threadpool.
    """
    settings = get_settings()
    extra: dict = {}
    if content_type:
        extra["ContentType"] = content_type
    _client().upload_fileobj(file_obj, settings.storage_bucket, key, ExtraArgs=extra or None)
    if settings.storage_public_url:
        return _public_url_for(key)
    return key


async def aupload_fileobj(
    *, key: str, file_obj: BinaryIO, content_type: str | None = None
) -> str:
    """Async wrapper — runs the sync boto3 upload on the threadpool so the
    FastAPI event loop is never blocked on the network. Critical at any scale."""
    return await run_in_threadpool(
        upload_fileobj, key=key, file_obj=file_obj, content_type=content_type
    )


def delete(key: str) -> None:
    """Sync — use adelete() from async code."""
    settings = get_settings()
    _client().delete_object(Bucket=settings.storage_bucket, Key=key)


async def adelete(key: str) -> None:
    await run_in_threadpool(delete, key)


def generate_presigned_url(key: str, *, ttl_seconds: int | None = None) -> str:
    """Sync. CPU-only (no network), so wrapping in threadpool is optional —
    but we provide an async helper for consistency."""
    settings = get_settings()
    ttl = ttl_seconds if ttl_seconds is not None else settings.storage_presigned_ttl_seconds
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.storage_bucket, "Key": key},
        ExpiresIn=ttl,
    )


def resolve_url(stored_ref: str, *, ttl_seconds: int | None = None) -> str:
    """
    Turn whatever's in asset.storage_url into a playable URL:
      - already a full URL (`http://` or `https://`) → return as-is
      - else treat as a bucket key → return a presigned URL with TTL

    SYNC. Sign-URL is a local crypto op (HMAC-SHA256), not a network call, so
    wrapping in threadpool isn't necessary in hot paths.
    """
    if not stored_ref:
        return stored_ref
    low = stored_ref.lower()
    if low.startswith("http://") or low.startswith("https://"):
        return stored_ref
    return generate_presigned_url(stored_ref, ttl_seconds=ttl_seconds)
