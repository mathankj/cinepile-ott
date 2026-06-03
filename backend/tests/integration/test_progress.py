"""Watch-progress: movies + episodes + continue-watching collapse."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_movie_progress(auth_client, make_title) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="m")
    r = await client.post(f"/v1/titles/{t.id}/progress", json={"position_sec": 200, "total_sec": 1000})
    assert r.status_code == 204
    cw = (await client.get("/v1/me/continue-watching")).json()
    assert cw["items"][0]["title"]["id"] == t.id
    assert cw["items"][0]["position_sec"] == 200
    assert cw["items"][0]["episode_id"] is None


@pytest.mark.asyncio
async def test_episode_progress(auth_client, make_series_with_episodes) -> None:
    client, _, _ = auth_client
    s = await make_series_with_episodes(slug="show", seasons=1, episodes_per_season=3)
    detail = (await client.get(f"/v1/titles/{s.id}/seasons/1")).json()
    e1, e2 = detail["episodes"][0]["id"], detail["episodes"][1]["id"]

    await client.post(f"/v1/episodes/{e1}/progress", json={"position_sec": 100, "total_sec": 1000})
    await client.post(f"/v1/episodes/{e2}/progress", json={"position_sec": 500, "total_sec": 1000})

    cw = (await client.get("/v1/me/continue-watching")).json()
    # Series collapses to one entry; most-recent episode (e2) is the resume target
    assert len(cw["items"]) == 1
    assert cw["items"][0]["title"]["id"] == s.id
    assert cw["items"][0]["episode_id"] == e2
    assert cw["items"][0]["position_sec"] == 500
    assert cw["items"][0]["season_number"] == 1


@pytest.mark.asyncio
async def test_completion_threshold_removes_from_continue(auth_client, make_title) -> None:
    """Once a title is completed (>=90%), it disappears from Continue Watching.
    Netflix's pattern — finished titles move to 'Watch Again' instead."""
    client, _, _ = auth_client
    t = await make_title(slug="m")
    await client.post(f"/v1/titles/{t.id}/progress", json={"position_sec": 950, "total_sec": 1000})
    cw = (await client.get("/v1/me/continue-watching")).json()
    assert cw["items"] == []


@pytest.mark.asyncio
async def test_below_threshold_stays_in_continue(auth_client, make_title) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="m")
    await client.post(f"/v1/titles/{t.id}/progress", json={"position_sec": 500, "total_sec": 1000})
    cw = (await client.get("/v1/me/continue-watching")).json()
    assert len(cw["items"]) == 1
    assert cw["items"][0]["position_sec"] == 500


@pytest.mark.asyncio
async def test_remove_then_resume_unhides(auth_client, make_title) -> None:
    """If user removes a title from Continue Watching, then later resumes
    it (via search or direct deep link), it should re-appear."""
    client, _, _ = auth_client
    t = await make_title(slug="m")
    await client.post(f"/v1/titles/{t.id}/progress", json={"position_sec": 100, "total_sec": 1000})
    await client.delete(f"/v1/me/continue-watching/{t.id}")
    assert (await client.get("/v1/me/continue-watching")).json()["items"] == []

    # Resume — should re-surface
    await client.post(f"/v1/titles/{t.id}/progress", json={"position_sec": 200, "total_sec": 1000})
    cw = (await client.get("/v1/me/continue-watching")).json()
    assert len(cw["items"]) == 1
    assert cw["items"][0]["position_sec"] == 200


@pytest.mark.asyncio
async def test_delete_progress(auth_client, make_title) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="m")
    await client.post(f"/v1/titles/{t.id}/progress", json={"position_sec": 50, "total_sec": 1000})
    r = await client.delete(f"/v1/me/continue-watching/{t.id}")
    assert r.status_code == 204
    cw = (await client.get("/v1/me/continue-watching")).json()
    assert cw["items"] == []
