"""
Pytest fixtures.

Per-test SQLite engine (shared-cache file-backed in-memory) with full schema
created via SQLAlchemy metadata. Dependency override for `get_db` so route
handlers and direct service calls share the test session.
"""
from __future__ import annotations

import asyncio
import os
import uuid as _uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

import pytest
import pytest_asyncio

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-32")
os.environ.setdefault("APP_ENV", "dev")
# Force mock billing in tests — never hit Razorpay's API even if .env has live keys
os.environ["BILLING_PROVIDER"] = "mock"
os.environ["BILLING_MODE"] = "orders"  # default; razorpay tests opt into other modes
# The demo .env disables the subscription gate; tests assert real gating
# behaviour, so force it back on here. Demo-mode tests monkeypatch settings.
os.environ["BILLING_GATE_ENABLED"] = "true"
os.environ.pop("RAZORPAY_KEY_ID", None)
os.environ.pop("RAZORPAY_KEY_SECRET", None)

# Default storage settings to empty (so storage.is_configured() returns False
# unless a test explicitly enables it via the storage_mock fixture).
# We set empty strings rather than popping, because pydantic-settings will
# otherwise fall through to reading the .env file's values.
for k in (
    "STORAGE_ENDPOINT_URL",
    "STORAGE_ACCESS_KEY_ID",
    "STORAGE_SECRET_ACCESS_KEY",
    "STORAGE_BUCKET",
    "STORAGE_PUBLIC_URL",
):
    os.environ[k] = ""

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app import models  # noqa: F401, E402  -- registers all models on Base.metadata
from app.api.deps import get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models.episode import Episode, EpisodeAsset  # noqa: E402
from app.models.genre import Genre  # noqa: E402
from app.models.season import Season  # noqa: E402
from app.models.subscription import Plan, Subscription  # noqa: E402
from app.models.title import Title, TitleAsset  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    name = f"test_{_uuid.uuid4().hex}"
    url = f"sqlite+aiosqlite:///file:{name}?mode=memory&cache=shared&uri=true"
    engine = create_async_engine(url, connect_args={"uri": True}, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncIterator[AsyncClient]:
    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            else:
                await session.commit()

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


# ---------- Convenience builders -------------------------------------------------


@pytest_asyncio.fixture
async def make_user(db_engine):
    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

    async def _make(*, email: str, password: str = "password123", role: str = "user") -> User:
        async with factory() as s:
            u = User(
                email=email.lower(),
                password_hash=hash_password(password),
                role=role,
                full_name=email.split("@")[0],
            )
            s.add(u)
            await s.commit()
            await s.refresh(u)
            return u

    return _make


@pytest_asyncio.fixture
async def make_genre(db_engine):
    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

    async def _make(slug: str, name: str | None = None, kind: str = "primary") -> Genre:
        async with factory() as s:
            existing = await s.scalar(select(Genre).where(Genre.slug == slug))
            if existing:
                return existing
            g = Genre(slug=slug, name=name or slug.title(), kind=kind)
            s.add(g)
            await s.commit()
            await s.refresh(g)
            return g

    return _make


@pytest_asyncio.fixture
async def make_title(db_engine, make_genre):
    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

    async def _make(
        *,
        slug: str,
        type: str = "movie",
        title: str | None = None,
        status: str = "published",
        hls_url: str | None = "https://test.example/hls/manifest.m3u8",
        genres: list[str] | None = None,
        original_language: str | None = "en",
        countries: list[str] | None = None,
        release_year: int = 2024,
        runtime_minutes: int = 90,
        series_type: str | None = None,
    ) -> Title:
        async with factory() as s:
            t = Title(
                slug=slug,
                type=type,
                series_type=series_type,
                title=title or slug.replace("-", " ").title(),
                synopsis="Test title.",
                release_year=release_year,
                runtime_minutes=runtime_minutes if type == "movie" else None,
                age_rating="U",
                original_language=original_language,
                countries=countries or ["IN"],
                status=status,
                published_at=datetime.now(tz=timezone.utc) if status == "published" else None,
            )
            if genres:
                cats = []
                for slug_ in genres:
                    g = await make_genre(slug_)
                    g = await s.merge(g)
                    cats.append(g)
                t.genres = cats
            s.add(t)
            await s.flush()
            if hls_url and type == "movie":
                s.add(TitleAsset(title_id=t.id, kind="hls_manifest", storage_url=hls_url))
            await s.commit()
            await s.refresh(
                t,
                attribute_names=["assets", "genres", "audio_tracks", "subtitle_tracks", "credits", "seasons"],
            )
            return t

    return _make


@pytest_asyncio.fixture
async def make_series_with_episodes(db_engine, make_title):
    """Helper: create a series + N seasons with M episodes each, all published with HLS."""
    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

    async def _make(
        *,
        slug: str,
        seasons: int = 1,
        episodes_per_season: int = 3,
        title: str | None = None,
        genres: list[str] | None = None,
    ) -> Title:
        series = await make_title(slug=slug, type="series", title=title, genres=genres)
        async with factory() as s:
            series = await s.merge(series)
            for sn in range(1, seasons + 1):
                season = Season(title_id=series.id, season_number=sn, name=f"Season {sn}")
                s.add(season)
                await s.flush()
                for en in range(1, episodes_per_season + 1):
                    ep = Episode(
                        season_id=season.id,
                        episode_number=en,
                        ordinal=en,
                        name=f"S{sn}E{en}",
                        runtime_seconds=2400,
                        status="published",
                        published_at=datetime.now(tz=timezone.utc),
                    )
                    s.add(ep)
                    await s.flush()
                    s.add(
                        EpisodeAsset(
                            episode_id=ep.id,
                            kind="hls_manifest",
                            storage_url=f"https://test.example/s{slug}-s{sn}-e{en}.m3u8",
                        )
                    )
            await s.commit()
            await s.refresh(series, attribute_names=["seasons"])
            return series

    return _make


@pytest_asyncio.fixture
async def make_plan(db_engine):
    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

    async def _make(*, code: str = "monthly", price_cents: int = 19900) -> Plan:
        async with factory() as s:
            plan = Plan(
                code=code,
                name=f"{code.title()} Plan",
                price_cents=price_cents,
                currency="INR",
                billing_interval="year" if "annual" in code else "month",
                is_active=True,
            )
            s.add(plan)
            await s.commit()
            await s.refresh(plan)
            return plan

    return _make


@pytest_asyncio.fixture
async def make_active_subscription(db_engine):
    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    from datetime import timedelta

    async def _make(*, user_id: int, plan_id: int) -> Subscription:
        async with factory() as s:
            now = datetime.now(tz=timezone.utc)
            sub = Subscription(
                user_id=user_id,
                plan_id=plan_id,
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
                provider="mock",
            )
            s.add(sub)
            await s.commit()
            await s.refresh(sub)
            return sub

    return _make


@pytest_asyncio.fixture
async def auth_client(client, make_user):
    """Returns (client, token, user) for a fresh signed-up regular user."""
    user = await make_user(email="user@example.com", password="password123")
    resp = await client.post(
        "/v1/auth/login", json={"email": "user@example.com", "password": "password123"}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["tokens"]["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client, token, user


@pytest_asyncio.fixture
async def admin_client(client, make_user):
    user = await make_user(email="admin@example.com", password="password123", role="admin")
    resp = await client.post(
        "/v1/auth/login", json={"email": "admin@example.com", "password": "password123"}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["tokens"]["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client, token, user


def _setup_storage_mock(monkeypatch, *, public_url: str | None):
    """Shared helper for both public and private storage_mock fixtures."""
    import boto3
    from moto import mock_aws

    bucket_name = "anjaneya-test-bucket"

    # moto 5.x intercepts at URL-pattern level — uses AWS hostnames. Point
    # STORAGE_ENDPOINT_URL at an AWS-shape URL so moto's interceptor catches it.
    monkeypatch.setenv("STORAGE_ENDPOINT_URL", "https://s3.us-east-1.amazonaws.com")
    monkeypatch.setenv("STORAGE_ACCESS_KEY_ID", "test-access-key")
    monkeypatch.setenv("STORAGE_SECRET_ACCESS_KEY", "test-secret-key")
    monkeypatch.setenv("STORAGE_BUCKET", bucket_name)
    if public_url:
        monkeypatch.setenv("STORAGE_PUBLIC_URL", public_url)
    else:
        monkeypatch.delenv("STORAGE_PUBLIC_URL", raising=False)

    from app.core.config import get_settings
    from app.services import storage as storage_svc

    get_settings.cache_clear()
    storage_svc._client.cache_clear()

    mock = mock_aws()
    mock.start()
    boto3.client(
        "s3",
        aws_access_key_id="test-access-key",
        aws_secret_access_key="test-secret-key",
        region_name="us-east-1",
    ).create_bucket(Bucket=bucket_name)
    return mock, storage_svc, get_settings, bucket_name


@pytest.fixture(autouse=True)
def _clear_module_caches():
    """Wipe the per-process TTL caches before each test.

    The /v1/titles and /v1/home/genres endpoints have module-level dicts
    that survive across tests. Without this, a test that creates titles
    after a previous test had already cached an empty list would see the
    stale cached value instead of its freshly-inserted rows.
    """
    from app.api.v1 import home as _home_router, titles as _titles_router
    from app.services import browse as _browse_svc

    # invalidate_titles_cache() covers the list cache AND the per-title /
    # per-season detail caches, so new caches added there stay covered here.
    _titles_router.invalidate_titles_cache()
    _home_router._GENRES_CACHE = None  # noqa: SLF001 — test cleanup needs internals
    _browse_svc._HOME_CACHE.clear()
    yield


@pytest.fixture
def storage_mock(monkeypatch):
    """Public bucket mode — STORAGE_PUBLIC_URL set; uploads return full URLs."""
    mock, storage_svc, get_settings, bucket = _setup_storage_mock(
        monkeypatch, public_url="https://pub-test.r2.dev"
    )
    yield {"bucket": bucket, "public_url": "https://pub-test.r2.dev"}
    mock.stop()
    get_settings.cache_clear()
    storage_svc._client.cache_clear()


@pytest.fixture
def storage_mock_private(monkeypatch):
    """Private bucket mode — no STORAGE_PUBLIC_URL; uploads return bucket keys."""
    mock, storage_svc, get_settings, bucket = _setup_storage_mock(monkeypatch, public_url=None)
    yield {"bucket": bucket}
    mock.stop()
    get_settings.cache_clear()
    storage_svc._client.cache_clear()


@pytest_asyncio.fixture
async def content_manager_client(client, make_user):
    user = await make_user(email="cm@example.com", password="password123", role="content_manager")
    resp = await client.post(
        "/v1/auth/login", json={"email": "cm@example.com", "password": "password123"}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["tokens"]["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client, token, user
