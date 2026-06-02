"""
Object storage service — Cloudflare R2 via boto3 (S3-compatible API).

R2 is API-compatible with S3 so we use boto3 unchanged; only the endpoint URL,
region marker, and signature version differ. The signed v4 signature is mandatory.

We expose:
  upload_fileobj(key, file_obj, content_type) → public_url
  delete(key)                                  → None
  generate_presigned_url(key, ttl=3600)        → url
  is_configured()                              → bool   (route layer uses this to 503)

Lazy boto3 init means the app boots happily even without R2 credentials
configured — tests don't need real credentials thanks to moto.
"""
from __future__ import annotations

from functools import lru_cache
from typing import BinaryIO

import boto3
from botocore.client import Config

from app.core.config import get_settings


class StorageNotConfigured(Exception):
    code = "storage_not_configured"
    message = "Object storage is not configured. Set R2_* env vars."


def is_configured() -> bool:
    return get_settings().storage_configured()


@lru_cache
def _client():
    settings = get_settings()
    if not settings.storage_configured():
        raise StorageNotConfigured
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        # R2 wants 'auto' as the region marker; SigV4 is required.
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def _public_url_for(key: str) -> str:
    settings = get_settings()
    base = (settings.r2_public_url or "").rstrip("/")
    if not base:
        # Fallback to the bucket-scoped path on the endpoint — works for dev
        # against the r2.dev URL but not recommended for prod.
        return f"{settings.r2_endpoint_url.rstrip('/')}/{settings.r2_bucket}/{key}"
    return f"{base}/{key}"


def upload_fileobj(
    *, key: str, file_obj: BinaryIO, content_type: str | None = None
) -> str:
    """Upload a file-like object; returns the public URL."""
    settings = get_settings()
    extra: dict = {}
    if content_type:
        extra["ContentType"] = content_type
    _client().upload_fileobj(file_obj, settings.r2_bucket, key, ExtraArgs=extra or None)
    return _public_url_for(key)


def delete(key: str) -> None:
    settings = get_settings()
    _client().delete_object(Bucket=settings.r2_bucket, Key=key)


def generate_presigned_url(key: str, *, ttl_seconds: int = 3600) -> str:
    settings = get_settings()
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.r2_bucket, "Key": key},
        ExpiresIn=ttl_seconds,
    )
