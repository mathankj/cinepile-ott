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
    # Dev-only test checkout page (no /v1/ prefix; used by humans in a browser)
    app.include_router(v1_test_checkout.router, tags=["dev"])

    return app


app = create_app()
