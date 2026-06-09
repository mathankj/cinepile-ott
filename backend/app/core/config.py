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

    # Demo mode: when False, the playback service skips the subscription check
    # entirely so any logged-in user can play any title. Flip to True post-demo
    # once real billing is wired up.
    billing_gate_enabled: bool = True

    # Razorpay
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None
    # 'auto' picks razorpay if key_id is set, otherwise mock
    billing_provider: Literal["auto", "mock", "razorpay"] = "auto"
    # Within the Razorpay provider, choose the integration shape:
    #   orders        — one-time payment per period via Razorpay Orders API.
    #                   Works without business KYC; we handle renewal in code.
    #                   This is the default while the client's business isn't activated.
    #   subscriptions — Razorpay Subscriptions with eMandate/UPI Autopay.
    #                   Requires the merchant account to be KYC-activated.
    billing_mode: Literal["orders", "subscriptions"] = "orders"

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

    # ---- DRM (Widevine / PlayReady / FairPlay) ----
    # When ANY of these are set, the playback ticket carries the license-server
    # URL + auth token for the corresponding key system. Player picks the one
    # matching the user's browser (EME: navigator.requestMediaKeySystemAccess).
    # See docs/decisions/0003-drm.md for provider integration guides.
    drm_widevine_license_url: str | None = None     # Chrome / Edge / Android
    drm_playready_license_url: str | None = None    # Edge / Windows
    drm_fairplay_license_url: str | None = None     # Safari / iOS / tvOS
    drm_fairplay_cert_url: str | None = None        # FairPlay needs an extra app-cert URL
    drm_provider: Literal["none", "ezdrm", "buydrm", "axinom", "verimatrix", "self"] = "none"
    # Optional shared secret used to sign per-playback license-request tokens.
    # If set, backend mints a short-lived JWT alongside each playback ticket
    # that the license server verifies before issuing a key.
    drm_token_secret: str | None = None
    drm_token_ttl_seconds: int = 60 * 60  # 1h — license requests happen at play start

    def drm_configured(self) -> bool:
        return any(
            [
                self.drm_widevine_license_url,
                self.drm_playready_license_url,
                self.drm_fairplay_license_url,
            ]
        )

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
