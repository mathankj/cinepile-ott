"""
Seed the dev DB with realistic V1.5 sample data:
- 5 genres
- 2 plans
- 1 admin + 1 content_manager + 1 regular user
- 3 movies (with playable HLS streams)
- 1 series with 2 seasons of 3 episodes each (with placeholder HLS per episode)
- Multi-language audio + subtitle tracks on a couple of titles
- A few sample reactions and watchlist entries

Idempotent — safe to re-run; checks for existing records by unique key.

Usage:
    cd backend
    .venv/Scripts/python.exe ../scripts/seed_dev_data.py
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app import models  # noqa: F401, E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base, get_engine, get_session_factory  # noqa: E402
from app.models.episode import Episode, EpisodeAsset  # noqa: E402
from app.models.genre import Genre  # noqa: E402
from app.models.language import AudioTrack, SubtitleTrack  # noqa: E402
from app.models.profile import Profile  # noqa: E402
from app.models.reaction import Reaction  # noqa: E402
from app.models.season import Season  # noqa: E402
from app.models.subscription import Plan  # noqa: E402
from app.models.title import Title, TitleAsset  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.watchlist import WatchlistItem  # noqa: E402


GENRES = [
    ("animation", "Animation", "primary"),
    ("drama", "Drama", "primary"),
    ("sci-fi", "Sci-Fi", "primary"),
    ("documentary", "Documentary", "primary"),
    ("comedy", "Comedy", "primary"),
]

PLANS = [
    {"code": "monthly", "name": "Monthly", "price_cents": 19900, "billing_interval": "month"},
    {"code": "annual", "name": "Annual", "price_cents": 199000, "billing_interval": "year"},
]


# Image URL conventions for dev:
# - poster:   600x900 (2:3 portrait — for boxshot rails)
# - backdrop: 1920x1080 (16:9 landscape — for hero billboards & home-row cards)
# - picsum.photos with deterministic seeds → same dev box, same image every reload
def _poster(seed: str) -> str:
    return f"https://picsum.photos/seed/{seed}-poster/600/900"

def _backdrop(seed: str) -> str:
    return f"https://picsum.photos/seed/{seed}-backdrop/1920/1080"


MOVIES = [
    {
        "slug": "big-buck-bunny",
        "title": "Big Buck Bunny",
        "synopsis": "A giant rabbit takes revenge on three rodents.",
        "release_year": 2008,
        "runtime_minutes": 10,
        "age_rating": "U",
        "original_language": "en",
        "countries": ["NL"],
        "poster_url": _poster("bbb"),
        "backdrop_url": _backdrop("bbb"),
        "genres": ["animation"],
        "hls": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
        "audio": [{"language": "en", "kind": "original"}, {"language": "ta", "kind": "dub"}],
        "subs": [
            {"language": "en", "kind": "cc", "forced": False},
            {"language": "ta", "kind": "subtitle", "forced": False},
        ],
    },
    {
        "slug": "sintel",
        "title": "Sintel",
        "synopsis": "A lone girl searches for her lost dragon companion.",
        "release_year": 2010,
        "runtime_minutes": 15,
        "age_rating": "U/A",
        "original_language": "en",
        "countries": ["NL"],
        "poster_url": _poster("sintel"),
        "backdrop_url": _backdrop("sintel"),
        "genres": ["animation", "drama"],
        "hls": "https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8",
        "audio": [{"language": "en", "kind": "original"}],
        "subs": [{"language": "en", "kind": "subtitle", "forced": False}],
    },
    {
        "slug": "tears-of-steel",
        "title": "Tears of Steel",
        "synopsis": "Robots threaten humanity in this short Blender film.",
        "release_year": 2012,
        "runtime_minutes": 12,
        "age_rating": "U/A",
        "original_language": "en",
        "countries": ["NL"],
        "poster_url": _poster("tos"),
        "backdrop_url": _backdrop("tos"),
        "genres": ["sci-fi"],
        "hls": "https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8",
        "audio": [{"language": "en", "kind": "original"}],
        "subs": [],
    },
    # ---- Additional Blender Open Movies (Creative Commons BY) ----
    # All are freely usable. HLS URLs point at public demo CDNs; the player
    # treats them like any other manifest. Swap to self-hosted B2 URLs once
    # storage creds are configured.
    {
        "slug": "caminandes-llamigos",
        "title": "Caminandes: Llamigos",
        "synopsis": "A llama and a pesky penguin race for food in the Patagonian winter.",
        "release_year": 2016,
        "runtime_minutes": 4,
        "age_rating": "U",
        "original_language": "en",
        "countries": ["NL"],
        "poster_url": _poster("caminandes"),
        "backdrop_url": _backdrop("caminandes"),
        "genres": ["animation", "comedy"],
        "hls": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
        "audio": [{"language": "en", "kind": "original"}],
        "subs": [],
    },
    {
        "slug": "spring",
        "title": "Spring",
        "synopsis": "A girl and her dog encounter the spirit of the forest in the high mountains.",
        "release_year": 2019,
        "runtime_minutes": 8,
        "age_rating": "U",
        "original_language": "en",
        "countries": ["NL"],
        "poster_url": _poster("spring"),
        "backdrop_url": _backdrop("spring"),
        "genres": ["animation", "drama"],
        "hls": "https://test-streams.mux.dev/dai-discontinuity-deltatre/manifest.m3u8",
        "audio": [{"language": "en", "kind": "original"}],
        "subs": [],
    },
    {
        "slug": "cosmos-laundromat",
        "title": "Cosmos Laundromat",
        "synopsis": "A suicidal sheep meets a salesman with a mysterious offer on a desolate island.",
        "release_year": 2015,
        "runtime_minutes": 12,
        "age_rating": "U/A",
        "original_language": "en",
        "countries": ["NL"],
        "poster_url": _poster("cosmos"),
        "backdrop_url": _backdrop("cosmos"),
        "genres": ["animation", "drama"],
        "hls": "https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8",
        "audio": [{"language": "en", "kind": "original"}],
        "subs": [],
    },
    {
        "slug": "hero-blender",
        "title": "Hero",
        "synopsis": "A grease-monkey faces an impossible foe in this Blender real-time short.",
        "release_year": 2019,
        "runtime_minutes": 5,
        "age_rating": "U",
        "original_language": "en",
        "countries": ["NL"],
        "poster_url": _poster("hero"),
        "backdrop_url": _backdrop("hero"),
        "genres": ["animation", "sci-fi"],
        "hls": "https://test-streams.mux.dev/pts_shift/master.m3u8",
        "audio": [{"language": "en", "kind": "original"}],
        "subs": [],
    },
]

SERIES = {
    # Original demo title was "The Anjaneya Chronicles" — renamed during the
    # CinePile rebrand. We keep the OLD slug as a backwards-compat alias so
    # any in-flight test references to /title-by-slug/the-anjaneya-chronicles
    # don't break; the upsert key is the slug, so changing it would orphan
    # the existing row. Title text is the user-visible change.
    "slug": "the-anjaneya-chronicles",
    "title": "The Veilbearer Chronicles",
    "synopsis": "A sweeping anthology of stories from across the ages.",
    "release_year": 2024,
    "age_rating": "U/A",
    "original_language": "ta",
    "countries": ["IN"],
    "poster_url": _poster("chronicles"),
    "backdrop_url": _backdrop("chronicles"),
    "genres": ["drama"],
    "series_type": "ongoing",
    "audio": [{"language": "ta", "kind": "original"}, {"language": "en", "kind": "dub"}, {"language": "hi", "kind": "dub"}],
    "subs": [
        {"language": "en", "kind": "subtitle", "forced": False},
        {"language": "ta", "kind": "cc", "forced": False},
        {"language": "hi", "kind": "subtitle", "forced": False},
    ],
    "seasons": [
        {
            "season_number": 1,
            "name": "Season 1 — Beginnings",
            "episodes": [
                {"episode_number": 1, "name": "The Awakening", "runtime_seconds": 2400, "intro_start": 0, "intro_end": 60, "credits_start": 2280, "next_cue": 2350},
                {"episode_number": 2, "name": "The Calling", "runtime_seconds": 2520, "intro_start": 0, "intro_end": 60, "credits_start": 2400, "next_cue": 2470},
                {"episode_number": 3, "name": "The Trial", "runtime_seconds": 2580, "intro_start": 0, "intro_end": 60, "credits_start": 2460, "next_cue": 2530},
            ],
        },
        {
            "season_number": 2,
            "name": "Season 2 — Ascension",
            "episodes": [
                {"episode_number": 1, "name": "Return", "runtime_seconds": 2640, "intro_start": 0, "intro_end": 60, "credits_start": 2520, "next_cue": 2590},
                {"episode_number": 2, "name": "Reckoning", "runtime_seconds": 2700, "intro_start": 0, "intro_end": 60, "credits_start": 2580, "next_cue": 2650},
                {"episode_number": 3, "name": "Resolution", "runtime_seconds": 2580, "intro_start": 0, "intro_end": 60, "credits_start": 2460, "next_cue": 2530},
            ],
        },
    ],
}

# Placeholder HLS for every episode — they all use Big Buck Bunny so the
# player has something real to chew on during dev.
PLACEHOLDER_EPISODE_HLS = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"

# Pioneer One — Creative Commons (CC-BY-NC-SA) science-fiction web series, 6
# episodes 2010-2013, produced by VODO. The ONLY mainstream legit open-license
# multi-episode web series (K-dramas are all copyrighted). Original MP4s live
# on Internet Archive (https://archive.org/details/pioneer.one); for dev we
# point every episode at the same placeholder HLS so the player has real
# video to chew on. Replace with the actual streams once they're transcoded
# to your own B2 bucket as HLS.
PIONEER_ONE = {
    "slug": "pioneer-one",
    "title": "Pioneer One",
    "synopsis": (
        "A mysterious craft re-enters Earth's orbit, scattering radioactive "
        "debris over North America. As Homeland Security investigates, they "
        "discover the survivor is the long-lost child of a Cold War-era "
        "Soviet space program."
    ),
    "release_year": 2010,
    "age_rating": "U/A",
    "original_language": "en",
    "countries": ["US"],
    "poster_url": _poster("pioneer-one"),
    "backdrop_url": _backdrop("pioneer-one"),
    "genres": ["sci-fi", "drama"],
    "series_type": "limited",
    "audio": [
        {"language": "en", "kind": "original"},
    ],
    "subs": [
        {"language": "en", "kind": "subtitle", "forced": False},
    ],
    "seasons": [
        {
            "season_number": 1,
            "name": "Season 1",
            "episodes": [
                {"episode_number": 1, "name": "Pilot", "runtime_seconds": 2280, "intro_start": 0, "intro_end": 30, "credits_start": 2160, "next_cue": 2230},
                {"episode_number": 2, "name": "Cynthia", "runtime_seconds": 1620, "intro_start": 0, "intro_end": 30, "credits_start": 1500, "next_cue": 1570},
                {"episode_number": 3, "name": "Just Below the Sky", "runtime_seconds": 1500, "intro_start": 0, "intro_end": 30, "credits_start": 1380, "next_cue": 1450},
                {"episode_number": 4, "name": "It's Always Different", "runtime_seconds": 1380, "intro_start": 0, "intro_end": 30, "credits_start": 1260, "next_cue": 1330},
                {"episode_number": 5, "name": "An Earnest Reply", "runtime_seconds": 1620, "intro_start": 0, "intro_end": 30, "credits_start": 1500, "next_cue": 1570},
                {"episode_number": 6, "name": "Memory the Sense", "runtime_seconds": 1860, "intro_start": 0, "intro_end": 30, "credits_start": 1740, "next_cue": 1810},
            ],
        },
    ],
}


async def _upsert_genre(s, slug, name, kind):
    g = await s.scalar(select(Genre).where(Genre.slug == slug))
    if g is None:
        g = Genre(slug=slug, name=name, kind=kind)
        s.add(g)
        await s.flush()
    return g


async def _upsert_plan(s, plan_data):
    plan = await s.scalar(select(Plan).where(Plan.code == plan_data["code"]))
    if plan is None:
        plan = Plan(**plan_data, currency="INR", is_active=True)
        s.add(plan)
        await s.flush()
    return plan


async def _upsert_movie(s, data):
    t = await s.scalar(select(Title).where(Title.slug == data["slug"]))
    cats = [await _upsert_genre(s, g, g.title(), "primary") for g in data["genres"]]
    if t is None:
        t = Title(
            slug=data["slug"],
            type="movie",
            title=data["title"],
            synopsis=data["synopsis"],
            release_year=data["release_year"],
            runtime_minutes=data["runtime_minutes"],
            age_rating=data["age_rating"],
            original_language=data["original_language"],
            countries=data["countries"],
            poster_url=data["poster_url"],
            backdrop_url=data.get("backdrop_url"),
            # Same HLS stream used as a placeholder trailer for dev — lets the
            # "Watch Trailer" button on title detail surface. Real launches
            # would point this at a per-title trailer URL.
            trailer_url=data.get("trailer_url", data["hls"]),
            status="published",
            published_at=datetime.now(tz=timezone.utc),
        )
        t.genres = cats
        s.add(t)
        await s.flush()
        s.add(TitleAsset(title_id=t.id, kind="hls_manifest", storage_url=data["hls"]))
        for a in data.get("audio", []):
            s.add(AudioTrack(title_id=t.id, **a))
        for sb in data.get("subs", []):
            s.add(SubtitleTrack(title_id=t.id, **sb))
    else:
        # Refresh image URLs on every seed run so dev environments stay consistent
        # even if the upstream URL pattern changes.
        t.trailer_url = data.get("trailer_url", data["hls"])
        t.poster_url = data["poster_url"]
        t.backdrop_url = data.get("backdrop_url")
    return t


async def _upsert_series(s, data):
    t = await s.scalar(select(Title).where(Title.slug == data["slug"]))
    cats = [await _upsert_genre(s, g, g.title(), "primary") for g in data["genres"]]
    if t is None:
        t = Title(
            slug=data["slug"],
            type="series",
            series_type=data["series_type"],
            title=data["title"],
            synopsis=data["synopsis"],
            release_year=data["release_year"],
            age_rating=data["age_rating"],
            original_language=data["original_language"],
            countries=data["countries"],
            poster_url=data.get("poster_url"),
            backdrop_url=data.get("backdrop_url"),
            trailer_url=data.get("trailer_url", PLACEHOLDER_EPISODE_HLS),
            status="published",
            published_at=datetime.now(tz=timezone.utc),
        )
        t.genres = cats
        s.add(t)
        await s.flush()
        for a in data.get("audio", []):
            s.add(AudioTrack(title_id=t.id, **a))
        for sb in data.get("subs", []):
            s.add(SubtitleTrack(title_id=t.id, **sb))

        for season_data in data["seasons"]:
            season = Season(
                title_id=t.id,
                season_number=season_data["season_number"],
                name=season_data["name"],
            )
            s.add(season)
            await s.flush()
            for ep_data in season_data["episodes"]:
                ep = Episode(
                    season_id=season.id,
                    episode_number=ep_data["episode_number"],
                    ordinal=ep_data["episode_number"],
                    name=ep_data["name"],
                    runtime_seconds=ep_data["runtime_seconds"],
                    intro_start_sec=ep_data.get("intro_start"),
                    intro_end_sec=ep_data.get("intro_end"),
                    credits_start_sec=ep_data.get("credits_start"),
                    next_episode_cue_sec=ep_data.get("next_cue"),
                    status="published",
                    published_at=datetime.now(tz=timezone.utc),
                )
                s.add(ep)
                await s.flush()
                s.add(
                    EpisodeAsset(
                        episode_id=ep.id,
                        kind="hls_manifest",
                        storage_url=PLACEHOLDER_EPISODE_HLS,
                    )
                )
    else:
        # Refresh stable fields on every seed run so dev DBs stay consistent
        # with the script. (series_type is enum-constrained in the schema, so
        # an out-of-range value would 500 on detail — keep this in sync.)
        # Display title is also refreshed so rebrands (e.g. Anjeya→CinePile)
        # land without needing a manual DB update.
        t.title = data["title"]
        t.synopsis = data["synopsis"]
        t.poster_url = data.get("poster_url")
        t.backdrop_url = data.get("backdrop_url")
        t.series_type = data.get("series_type")
        t.trailer_url = data.get("trailer_url", PLACEHOLDER_EPISODE_HLS)
    return t


async def _ensure_user(s, email, password, role, full_name):
    user = await s.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
        )
        s.add(user)
        await s.flush()
        print(f"  -> created {role}: {email} / {password}")
    else:
        # Refresh the password every run so changes in this script propagate.
        # Otherwise an existing dev DB sticks to the original seeded password
        # and breaks tests after a password change.
        user.password_hash = hash_password(password)
        user.role = role
        user.full_name = full_name
        await s.flush()
    # Ensure a primary profile exists. We backfill so users that pre-date the
    # profiles feature still get one.
    existing_profile = await s.scalar(
        select(Profile).where(Profile.user_id == user.id, Profile.is_primary.is_(True))
    )
    if existing_profile is None:
        s.add(
            Profile(
                user_id=user.id,
                name=(full_name or email.split("@")[0])[:32],
                avatar="👤",
                kind="adult",
                is_primary=True,
            )
        )
        await s.flush()
    return user


async def main() -> None:
    # Create tables if they don't exist (dev shortcut; prod uses Alembic)
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = get_session_factory()
    async with factory() as s:
        print("Seeding genres...")
        for slug, name, kind in GENRES:
            await _upsert_genre(s, slug, name, kind)

        print("Seeding plans...")
        for plan in PLANS:
            await _upsert_plan(s, plan)

        print("Seeding users (admin / content_manager / user)...")
        admin = await _ensure_user(s, "admin@anjaneya.app", "admin1234", "admin", "Local Admin")
        cm = await _ensure_user(s, "cm@anjaneya.app", "cm123456", "content_manager", "Content Manager")
        regular = await _ensure_user(s, "user@anjaneya.app", "user1234", "user", "Regular User")

        print("Seeding movies...")
        movies = []
        for m in MOVIES:
            movies.append(await _upsert_movie(s, m))

        print("Seeding the series...")
        series = await _upsert_series(s, SERIES)
        await _upsert_series(s, PIONEER_ONE)

        await s.commit()

        # Reactions + watchlist for the regular user — only add if not already present
        print("Seeding sample reactions + watchlist...")
        existing_r = await s.scalar(select(Reaction).where(Reaction.user_id == regular.id))
        if existing_r is None and movies:
            s.add(Reaction(user_id=regular.id, title_id=movies[0].id, kind="thumbs_up"))
            s.add(Reaction(user_id=regular.id, title_id=series.id, kind="double_thumbs_up"))
        existing_w = await s.scalar(select(WatchlistItem).where(WatchlistItem.user_id == regular.id))
        if existing_w is None and len(movies) >= 2:
            s.add(WatchlistItem(user_id=regular.id, title_id=movies[1].id, added_at=datetime.now(tz=timezone.utc)))
            s.add(WatchlistItem(user_id=regular.id, title_id=series.id, added_at=datetime.now(tz=timezone.utc)))
        await s.commit()

    print()
    print("Seed complete. Try:")
    print("  curl http://localhost:8000/v1/titles")
    print("  curl http://localhost:8000/v1/home")
    print("  curl http://localhost:8000/v1/plans")
    print()
    print("Login as admin:    admin@anjaneya.app / admin1234")
    print("Login as content:  cm@anjaneya.app    / cm123456")
    print("Login as user:     user@anjaneya.app  / user1234")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
