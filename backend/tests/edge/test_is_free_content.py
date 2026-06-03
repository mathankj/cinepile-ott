"""Free vs paid content gating (is_free flag)."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_free_movie_plays_without_subscription(
    auth_client, make_title, db_session
) -> None:
    """is_free=True on a movie lets unsubscribed users play it."""
    from app.models.title import Title

    client, _, _ = auth_client
    t = await make_title(slug="freemovie")
    db_t = await db_session.get(Title, t.id)
    db_t.is_free = True
    await db_session.commit()

    resp = await client.get(f"/v1/titles/{t.id}/play")
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_paid_movie_blocks_without_subscription(auth_client, make_title) -> None:
    """Default is_free=False — unsubscribed users get 402."""
    client, _, _ = auth_client
    t = await make_title(slug="paid")
    resp = await client.get(f"/v1/titles/{t.id}/play")
    assert resp.status_code == 402


@pytest.mark.asyncio
async def test_free_episode_plays_without_subscription(
    auth_client, make_series_with_episodes, db_session
) -> None:
    """is_free=True on an episode (first-episode-free pattern) — works without
    the parent series being free."""
    from app.models.episode import Episode

    client, _, _ = auth_client
    s = await make_series_with_episodes(slug="show", seasons=1, episodes_per_season=2)
    detail = (await client.get(f"/v1/titles/{s.id}/seasons/1")).json()
    e1_id = detail["episodes"][0]["id"]
    e2_id = detail["episodes"][1]["id"]

    ep = await db_session.get(Episode, e1_id)
    ep.is_free = True
    await db_session.commit()

    r1 = await client.get(f"/v1/episodes/{e1_id}/play")
    assert r1.status_code == 200, r1.text
    r2 = await client.get(f"/v1/episodes/{e2_id}/play")
    assert r2.status_code == 402


@pytest.mark.asyncio
async def test_free_series_makes_all_episodes_free(
    auth_client, make_series_with_episodes, db_session
) -> None:
    """Title.is_free=True on a series lets unsubscribed users play any episode."""
    from app.models.title import Title

    client, _, _ = auth_client
    s = await make_series_with_episodes(slug="show", seasons=1, episodes_per_season=3)
    detail = (await client.get(f"/v1/titles/{s.id}/seasons/1")).json()

    t = await db_session.get(Title, s.id)
    t.is_free = True
    await db_session.commit()

    for ep in detail["episodes"]:
        r = await client.get(f"/v1/episodes/{ep['id']}/play")
        assert r.status_code == 200, f"episode {ep['id']} should play: {r.text}"


@pytest.mark.asyncio
async def test_is_free_surfaces_in_title_summary(client, make_title, db_session) -> None:
    """TitleSummary used in /v1/titles list — frontend uses is_free to render a 'FREE' badge."""
    from app.models.title import Title

    free = await make_title(slug="free-one")
    db_t = await db_session.get(Title, free.id)
    db_t.is_free = True
    await db_session.commit()

    resp = await client.get("/v1/titles")
    items = resp.json()["items"]
    free_item = next(i for i in items if i["slug"] == "free-one")
    assert free_item["is_free"] is True
