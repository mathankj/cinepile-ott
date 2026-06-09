"""GET /v1/titles/{id}/similar — "More Like This" rail.

Public endpoint (no auth, like the trailer endpoint). Returns published,
non-deleted titles sharing at least one genre with the seed, excluding the
seed itself, ordered by view_count desc.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.title import Title


async def _set_title(db_engine, title_id: int, **values) -> None:
    """Direct column update — lets tests soft-delete or bump view_count
    without going through (and being shaped by) the admin API."""
    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with factory() as s:
        await s.execute(sa_update(Title).where(Title.id == title_id).values(**values))
        await s.commit()


@pytest.mark.asyncio
async def test_similar_shares_genre_and_excludes_self(client, make_title) -> None:
    seed = await make_title(slug="seed-action", genres=["action"])
    match_a = await make_title(slug="match-a", genres=["action", "thriller"])
    match_b = await make_title(slug="match-b", genres=["action"])
    await make_title(slug="unrelated-comedy", genres=["comedy"])

    resp = await client.get(f"/v1/titles/{seed.id}/similar")
    assert resp.status_code == 200, resp.text
    slugs = [t["slug"] for t in resp.json()]
    assert set(slugs) == {"match-a", "match-b"}
    assert "seed-action" not in slugs  # never recommend the title to itself
    assert match_a.id != match_b.id  # sanity: distinct fixtures


@pytest.mark.asyncio
async def test_similar_ordered_by_view_count_desc(client, db_engine, make_title) -> None:
    seed = await make_title(slug="seed", genres=["drama"])
    low = await make_title(slug="low-views", genres=["drama"])
    high = await make_title(slug="high-views", genres=["drama"])
    await _set_title(db_engine, low.id, view_count=5)
    await _set_title(db_engine, high.id, view_count=500)

    resp = await client.get(f"/v1/titles/{seed.id}/similar")
    assert resp.status_code == 200
    assert [t["slug"] for t in resp.json()] == ["high-views", "low-views"]


@pytest.mark.asyncio
async def test_similar_excludes_drafts_and_deleted(client, db_engine, make_title) -> None:
    seed = await make_title(slug="seed", genres=["action"])
    await make_title(slug="draft-match", genres=["action"], status="draft")
    deleted = await make_title(slug="deleted-match", genres=["action"])
    await _set_title(db_engine, deleted.id, deleted_at=datetime.now(tz=timezone.utc))
    visible = await make_title(slug="visible-match", genres=["action"])

    resp = await client.get(f"/v1/titles/{seed.id}/similar")
    assert resp.status_code == 200
    assert [t["slug"] for t in resp.json()] == [visible.slug]


@pytest.mark.asyncio
async def test_similar_404_for_missing_title(client) -> None:
    resp = await client.get("/v1/titles/999999/similar")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"]["code"] == "title_not_found"


@pytest.mark.asyncio
async def test_similar_404_for_deleted_title(client, db_engine, make_title) -> None:
    seed = await make_title(slug="gone", genres=["action"])
    await _set_title(db_engine, seed.id, deleted_at=datetime.now(tz=timezone.utc))
    resp = await client.get(f"/v1/titles/{seed.id}/similar")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"]["code"] == "title_not_found"


@pytest.mark.asyncio
async def test_similar_limit_bounds(client, make_title) -> None:
    seed = await make_title(slug="seed", genres=["drama"])
    for i in range(3):
        await make_title(slug=f"match-{i}", genres=["drama"])

    # limit must be 1..40 — out-of-range values are validation errors
    assert (await client.get(f"/v1/titles/{seed.id}/similar", params={"limit": 0})).status_code == 422
    assert (await client.get(f"/v1/titles/{seed.id}/similar", params={"limit": 41})).status_code == 422

    resp = await client.get(f"/v1/titles/{seed.id}/similar", params={"limit": 1})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_similar_empty_when_seed_has_no_genres(client, make_title) -> None:
    seed = await make_title(slug="genre-less")
    await make_title(slug="other", genres=["drama"])
    resp = await client.get(f"/v1/titles/{seed.id}/similar")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_similar_summary_shape(client, make_title) -> None:
    """Response items are TitleSummary cards — the contract the frontend's
    catalog.similar client already expects."""
    seed = await make_title(slug="seed", genres=["drama"])
    await make_title(slug="match", genres=["drama"])
    resp = await client.get(f"/v1/titles/{seed.id}/similar")
    item = resp.json()[0]
    assert {"id", "slug", "type", "title", "poster_url", "is_free"} <= set(item.keys())
    # Detail-only payloads (genres, credits, assets) must NOT leak into cards
    assert "genres" not in item and "credits" not in item
