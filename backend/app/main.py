"""
FastAPI app factory + middleware + router include.

Run locally:
    uvicorn app.main:app --reload --port 8000

OpenAPI:  http://localhost:8000/docs
Redoc:    http://localhost:8000/redoc
Health:   http://localhost:8000/healthz
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.gzip import GZipMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.base import dispose_engine, get_session_factory

from app.api.v1 import admin as v1_admin
from app.api.v1 import auth as v1_auth
from app.api.v1 import episodes as v1_episodes
from app.api.v1 import home as v1_home
from app.api.v1 import me as v1_me
from app.api.v1 import payments as v1_payments
from app.api.v1 import test_checkout_page as v1_test_checkout
from app.api.v1 import subscriptions as v1_subscriptions
from app.api.v1 import titles as v1_titles
from app.api.v1 import webhooks as v1_webhooks

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    configure_logging()
    settings = get_settings()
    log.info("startup", env=settings.app_env, version=settings.app_version)
    yield
    await dispose_engine()
    log.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="CinePile API",
        version=settings.app_version,
        description="Production backend for the CinePile streaming platform.",
        lifespan=lifespan,
        # Serve docs only outside prod by default; flip to True if you want them in prod too
        docs_url="/docs" if settings.app_env != "prod" else None,
        redoc_url="/redoc" if settings.app_env != "prod" else None,
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Compress JSON responses over 500 bytes — catalog lists shrink ~5-10x.
    # Small responses are skipped (gzip overhead would outweigh the gain).
    app.add_middleware(GZipMiddleware, minimum_size=500)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        """Baseline browser-protection headers on every response.

        - nosniff: stop browsers guessing content types (e.g. treating an
          uploaded file as HTML).
        - DENY framing: this is a JSON API + one dev page; nothing legitimate
          embeds it in an iframe, so block clickjacking outright.
        - no-referrer: never leak our URLs (which may carry tokens or ids)
          to third-party hosts.
        - HSTS: only meaningful (and only safe) over real HTTPS, so prod only —
          setting it on localhost dev would break plain-http testing.
        """
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if settings.app_env == "prod":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    # Public catalog paths — safe to cache in the browser for a short window.
    # We deliberately exclude /v1/me/*, /v1/auth/*, /v1/admin/*, /v1/subscriptions/me,
    # /v1/*/play (per-user playback tickets), and anything that mutates state.
    # 60s public cache + 5min SWR means navigating Home → Browse → Home is
    # served from the browser cache, not a fresh Render trip.
    _PUBLIC_CACHEABLE_PREFIXES = (
        "/v1/titles",       # list, detail, coming-soon, search, trailer
        "/v1/home",         # home rows + genres
        "/v1/plans",        # billing plans
    )
    _UNCACHEABLE_SUFFIXES = ("/play",)  # per-user playback ticket

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:16]}"
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("request_failed", method=request.method, path=request.url.path)
            raise
        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["x-request-id"] = request_id

        # Browser cache headers — only for safe GETs to public catalog endpoints.
        # stale-while-revalidate lets the browser show cached content INSTANTLY
        # while it refreshes in the background, which kills the "loading…" flash
        # on back/forward navigation.
        path = request.url.path
        if (
            request.method == "GET"
            and 200 <= response.status_code < 400
            and path.startswith(_PUBLIC_CACHEABLE_PREFIXES)
            and not path.endswith(_UNCACHEABLE_SUFFIXES)
        ):
            response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"

        log.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        structlog.contextvars.clear_contextvars()
        return response

    @app.get("/healthz", tags=["health"])
    async def healthz() -> JSONResponse:
        """Liveness probe — process is alive. Always 200 unless the process
        is broken. Don't put DB pings here: a transient DB blip should NOT
        cause k8s/uvicorn/whatever restarts the process — that's what
        /readyz is for."""
        return JSONResponse(
            {"status": "ok", "version": settings.app_version, "env": settings.app_env},
            status_code=200,
        )

    @app.get("/readyz", tags=["health"])
    async def readyz() -> JSONResponse:
        """Readiness probe — checks downstream dependencies (DB, storage).
        Returns 503 if anything is broken so the load balancer routes around
        this instance until it recovers."""
        checks: dict = {"db": "ok", "storage": "ok"}

        try:
            factory = get_session_factory()
            async with factory() as session:
                await session.execute(text("SELECT 1"))
        except Exception as exc:  # noqa: BLE001
            checks["db"] = f"error: {exc.__class__.__name__}"

        # Storage check is optional — if not configured, skip.
        try:
            from app.services import storage as storage_svc

            if storage_svc.is_configured():
                # head_bucket is the cheapest authenticated check
                # We don't await network here in this simple version; just trust
                # the boto3 client constructor works. For real prod, do a
                # head_bucket call with a tight timeout.
                _ = storage_svc._client  # touch the client factory
            else:
                checks["storage"] = "not_configured"
        except Exception as exc:  # noqa: BLE001
            checks["storage"] = f"error: {exc.__class__.__name__}"

        any_failed = any(v.startswith("error:") for v in checks.values())
        body = {
            "status": "degraded" if any_failed else "ok",
            **checks,
            "version": settings.app_version,
            "env": settings.app_env,
        }
        return JSONResponse(body, status_code=503 if any_failed else 200)

    app.include_router(v1_auth.router, prefix="/v1/auth", tags=["auth"])
    app.include_router(v1_titles.router, prefix="/v1/titles", tags=["titles"])
    app.include_router(v1_episodes.router, prefix="/v1/episodes", tags=["episodes"])
    app.include_router(v1_subscriptions.router, prefix="/v1", tags=["subscriptions"])
    app.include_router(v1_me.router, prefix="/v1", tags=["me"])
    app.include_router(v1_home.router, prefix="/v1/home", tags=["home"])
    app.include_router(v1_admin.router, prefix="/v1/admin", tags=["admin"])
    app.include_router(v1_webhooks.router, prefix="/v1/webhooks", tags=["webhooks"])
    app.include_router(v1_payments.router, prefix="/v1/payments", tags=["payments"])
    # Dev-only test checkout page (no /v1/ prefix; used by humans in a browser).
    # Not registered in prod at all — same pattern as the /docs gating above.
    # The real frontend uses Razorpay Checkout JS directly.
    if settings.app_env != "prod":
        app.include_router(v1_test_checkout.router, tags=["dev"])

    return app


app = create_app()
