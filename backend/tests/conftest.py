"""
Pytest fixtures shared across all tests.

We use one in-memory SQLite engine per test session (with shared cache so multiple
connections see the same DB). FastAPI's `get_db` is overridden to yield from that
engine, so route handlers and direct service calls hit the same DB.
"""
from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

# Set env BEFORE importing app modules — config validates at import time.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-32")
os.environ.setdefault("APP_ENV", "dev")

from httpx import ASGITransport, AsyncClient  # noqa: E402
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
from app.models.film import Category, Film, FilmAsset  # noqa: E402
from app.models.subscription import Plan, Subscription  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    # File-backed in-memory DB (per-process unique) so multiple connections see the same schema.
    import uuid as _uuid

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


# ---------- Convenience builders for integration tests ----------


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
async def make_film(db_engine):
    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    from datetime import datetime, timezone

    async def _make(
        *,
        slug: str,
        title: str | None = None,
        status: str = "published",
        hls_url: str | None = "https://test.example/hls/manifest.m3u8",
        category_slugs: list[str] | None = None,
    ) -> Film:
        async with factory() as s:
            film = Film(
                slug=slug,
                title=title or slug.replace("-", " ").title(),
                synopsis="A test film.",
                release_year=2024,
                runtime_minutes=90,
                age_rating="U",
                primary_language="en",
                status=status,
                published_at=datetime.now(tz=timezone.utc) if status == "published" else None,
            )
            if category_slugs:
                cats = []
                for slug_ in category_slugs:
                    existing = await s.scalar(
                        __import__("sqlalchemy").select(Category).where(Category.slug == slug_)
                    )
                    if existing is None:
                        existing = Category(slug=slug_, name=slug_.title())
                        s.add(existing)
                        await s.flush()
                    cats.append(existing)
                film.categories = cats
            s.add(film)
            await s.flush()
            if hls_url:
                s.add(FilmAsset(film_id=film.id, kind="hls_manifest", storage_url=hls_url))
            await s.commit()
            await s.refresh(film, attribute_names=["assets", "categories"])
            return film

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
    """Directly creates an active subscription without going through billing."""
    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    from datetime import datetime, timedelta, timezone

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

    async def _login(*, email: str = "user@example.com", password: str = "password123") -> tuple:
        resp = await client.post(
            "/v1/auth/login", json={"email": email, "password": password}
        )
        return resp

    user = await make_user(email="user@example.com", password="password123")
    resp = await _login()
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
