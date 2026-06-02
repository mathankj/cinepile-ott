"""
Application config.

All runtime settings flow through this single Settings class.
We use pydantic-settings so missing required keys fail at process startup
(not on first request), and types are enforced (e.g. ints aren't strings).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import EmailStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    app_env: Literal["dev", "staging", "prod"] = "dev"
    app_name: str = "anjaneya-ott"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database — must be set for the app to start
    database_url: str = Field(..., description="SQLAlchemy URL, e.g. postgresql+asyncpg://...")

    # JWT
    jwt_secret: str = Field(..., min_length=16)
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 7
    jwt_algorithm: str = "HS256"

    # CORS
    allowed_origins: str = "http://localhost:5173"

    # First admin bootstrap
    bootstrap_admin_email: EmailStr | None = None
    bootstrap_admin_password: str | None = None

    # Storage (Phase 1.1)
    storage_bucket: str | None = None
    storage_region: str | None = None

    # Razorpay
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None
    # 'auto' picks razorpay if key_id is set, otherwise mock
    billing_provider: Literal["auto", "mock", "razorpay"] = "auto"

    @property
    def effective_billing_provider(self) -> Literal["mock", "razorpay"]:
        if self.billing_provider == "auto":
            return "razorpay" if self.razorpay_key_id else "mock"
        return self.billing_provider  # type: ignore[return-value]

    # Object storage — any S3-compatible provider (Backblaze B2, Cloudflare R2,
    # AWS S3, Storj, etc.). Empty = uploads disabled, GET still works for any
    # already-stored full URLs.
    storage_endpoint_url: str | None = None
    storage_access_key_id: str | None = None
    storage_secret_access_key: str | None = None
    storage_bucket: str | None = None
    # Optional. If set, files are stored as public and storage_url contains the
    # final public URL. If unset, bucket is treated as private and the playback
    # service generates short-lived presigned URLs from the stored bucket key.
    storage_public_url: str | None = None
    # Default presigned-URL TTL in seconds (4h covers a full feature film comfortably)
    storage_presigned_ttl_seconds: int = 14400

    def storage_configured(self) -> bool:
        return all(
            [
                self.storage_endpoint_url,
                self.storage_access_key_id,
                self.storage_secret_access_key,
                self.storage_bucket,
            ]
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached singleton — call this anywhere config is needed."""
    return Settings()  # type: ignore[call-arg]
