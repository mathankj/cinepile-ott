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
async def test_completion_threshold(auth_client, make_title) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="m")
    await client.post(f"/v1/titles/{t.id}/progress", json={"position_sec": 950, "total_sec": 1000})
    cw = (await client.get("/v1/me/continue-watching")).json()
    # Still in continue-watching (we don't auto-hide completed for V1.5)
    assert cw["items"][0]["position_sec"] == 950


@pytest.mark.asyncio
async def test_delete_progress(auth_client, make_title) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="m")
    await client.post(f"/v1/titles/{t.id}/progress", json={"position_sec": 50, "total_sec": 1000})
    r = await client.delete(f"/v1/me/continue-watching/{t.id}")
    assert r.status_code == 204
    cw = (await client.get("/v1/me/continue-watching")).json()
    assert cw["items"] == []
