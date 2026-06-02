"""
Seed the dev DB with realistic sample data so load tests + manual browsing have
something to hit.

Usage:
    cd backend
    .venv/Scripts/python.exe ../scripts/seed_dev_data.py

Idempotent — safe to re-run; uses ON CONFLICT semantics for slugs/codes.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running from project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app import models  # noqa: F401, E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base, get_engine, get_session_factory  # noqa: E402
from app.models.film import Category, Film, FilmAsset  # noqa: E402
from app.models.subscription import Plan  # noqa: E402
from app.models.user import User  # noqa: E402


SAMPLE_FILMS = [
    {
        "slug": "big-buck-bunny",
        "title": "Big Buck Bunny",
        "synopsis": "A giant rabbit takes revenge on three rodents.",
        "release_year": 2008,
        "runtime_minutes": 10,
        "age_rating": "U",
        "poster_url": "https://upload.wikimedia.org/wikipedia/commons/c/c5/Big_buck_bunny_poster_big.jpg",
        "primary_language": "en",
        "categories": ["animation"],
        "hls": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
    },
    {
        "slug": "sintel",
        "title": "Sintel",
        "synopsis": "A lone girl searches for her lost dragon companion.",
        "release_year": 2010,
        "runtime_minutes": 15,
        "age_rating": "U/A",
        "poster_url": "https://upload.wikimedia.org/wikipedia/commons/c/c1/Sintel_poster.jpg",
        "primary_language": "en",
        "categories": ["animation", "drama"],
        "hls": "https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8",
    },
    {
        "slug": "tears-of-steel",
        "title": "Tears of Steel",
        "synopsis": "Robots threaten humanity in this short Blender film.",
        "release_year": 2012,
        "runtime_minutes": 12,
        "age_rating": "U/A",
        "poster_url": "https://upload.wikimedia.org/wikipedia/commons/7/7a/Tears_of_Steel_frame.jpg",
        "primary_language": "en",
        "categories": ["sci-fi"],
        "hls": "https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8",
    },
]

CATEGORIES = [
    ("animation", "Animation"),
    ("drama", "Drama"),
    ("sci-fi", "Sci-Fi"),
    ("action", "Action"),
    ("documentary", "Documentary"),
]

PLANS = [
    {"code": "monthly", "name": "Monthly", "price_cents": 19900, "billing_interval": "month"},
    {"code": "annual", "name": "Annual", "price_cents": 199000, "billing_interval": "year"},
]


async def _upsert_category(s, slug: str, name: str) -> Category:
    cat = await s.scalar(select(Category).where(Category.slug == slug))
    if cat is None:
        cat = Category(slug=slug, name=name)
        s.add(cat)
        await s.flush()
    return cat


async def _upsert_plan(s, plan_data: dict) -> Plan:
    plan = await s.scalar(select(Plan).where(Plan.code == plan_data["code"]))
    if plan is None:
        plan = Plan(**plan_data, currency="INR", is_active=True)
        s.add(plan)
        await s.flush()
    return plan


async def _upsert_film(s, data: dict) -> Film:
    film = await s.scalar(select(Film).where(Film.slug == data["slug"]))
    cats = [await _upsert_category(s, cs, cs.title()) for cs in data["categories"]]

    if film is None:
        film = Film(
            slug=data["slug"],
            title=data["title"],
            synopsis=data["synopsis"],
            release_year=data["release_year"],
            runtime_minutes=data["runtime_minutes"],
            age_rating=data["age_rating"],
            poster_url=data["poster_url"],
            primary_language=data["primary_language"],
            status="published",
            published_at=datetime.now(tz=timezone.utc),
        )
        film.categories = cats
        s.add(film)
        await s.flush()
        s.add(FilmAsset(film_id=film.id, kind="hls_manifest", storage_url=data["hls"]))
    return film


async def _ensure_admin(s) -> User:
    email = "admin@anjaneya.local"
    user = await s.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password("admin1234"),
            full_name="Local Admin",
            role="admin",
        )
        s.add(user)
        await s.flush()
        print(f"  -> created admin user: {email} / admin1234")
    return user


async def main() -> None:
    # Create tables if they don't exist (dev convenience — prod uses Alembic)
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = get_session_factory()
    async with factory() as s:
        print("Seeding categories...")
        for slug, name in CATEGORIES:
            await _upsert_category(s, slug, name)
        print("Seeding plans...")
        for plan_data in PLANS:
            await _upsert_plan(s, plan_data)
        print("Seeding films...")
        for film_data in SAMPLE_FILMS:
            await _upsert_film(s, film_data)
        print("Ensuring admin user...")
        await _ensure_admin(s)
        await s.commit()

    print("\nSeed complete. Try:")
    print("  curl http://localhost:8000/v1/films")
    print("  curl http://localhost:8000/v1/plans")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
