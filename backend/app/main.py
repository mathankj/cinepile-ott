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

# Routers will be included here as they are built in Phase 1
# from app.api.v1 import auth, films, subscriptions, history, admin

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
        title="Anjaneya OTT API",
        version=settings.app_version,
        description="Production backend for the Anjaneya OTT platform.",
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
        """Liveness probe — also pings the DB."""
        db_status = "ok"
        try:
            factory = get_session_factory()
            async with factory() as session:
                await session.execute(text("SELECT 1"))
        except Exception as exc:  # noqa: BLE001
            db_status = f"error: {exc.__class__.__name__}"

        body = {
            "status": "ok" if db_status == "ok" else "degraded",
            "db": db_status,
            "version": settings.app_version,
            "env": settings.app_env,
        }
        return JSONResponse(body, status_code=200 if db_status == "ok" else 503)

    # Include API v1 routers (added as built):
    # app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
    # app.include_router(films.router, prefix="/v1/films", tags=["films"])
    # app.include_router(subscriptions.router, prefix="/v1/subscriptions", tags=["subscriptions"])
    # app.include_router(history.router, prefix="/v1/history", tags=["history"])
    # app.include_router(admin.router, prefix="/v1/admin", tags=["admin"])

    return app


app = create_app()
