"""Playback — movies + episodes, entitlement gating, view counter bump."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_play_movie_requires_auth(client, make_title) -> None:
    t = await make_title(slug="m")
    resp = await client.get(f"/v1/titles/{t.id}/play")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_play_movie_requires_subscription(auth_client, make_title) -> None:
    client, _, _ = auth_client
    t = await make_title(slug="m")
    resp = await client.get(f"/v1/titles/{t.id}/play")
    assert resp.status_code == 402


@pytest.mark.asyncio
async def test_play_movie_happy_path(
    auth_client, make_title, make_plan, make_active_subscription
) -> None:
    client, _, user = auth_client
    plan = await make_plan(code="monthly")
    await make_active_subscription(user_id=user.id, plan_id=plan.id)
    t = await make_title(slug="m", hls_url="https://test.example/m.m3u8")
    resp = await client.get(f"/v1/titles/{t.id}/play")
    assert resp.status_code == 200
    body = resp.json()
    assert body["manifest_url"] == "https://test.example/m.m3u8"
    assert body["ref_type"] == "title"


@pytest.mark.asyncio
async def test_play_movie_endpoint_rejects_series(
    auth_client, make_series_with_episodes, make_plan, make_active_subscription
) -> None:
    client, _, user = auth_client
    plan = await make_plan(code="monthly")
    await make_active_subscription(user_id=user.id, plan_id=plan.id)
    s = await make_series_with_episodes(slug="show", seasons=1, episodes_per_season=1)
    resp = await client.get(f"/v1/titles/{s.id}/play")
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"]["code"] == "type_mismatch"


@pytest.mark.asyncio
async def test_play_episode_happy_path(
    auth_client, make_series_with_episodes, make_plan, make_active_subscription, db_session
) -> None:
    client, _, user = auth_client
    plan = await make_plan(code="monthly")
    await make_active_subscription(user_id=user.id, plan_id=plan.id)
    s = await make_series_with_episodes(slug="show", seasons=1, episodes_per_season=2)

    # Get episode id from detail
    detail = (await client.get(f"/v1/titles/{s.id}/seasons/1")).json()
    ep_id = detail["episodes"][0]["id"]

    resp = await client.get(f"/v1/episodes/{ep_id}/play")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ref_type"] == "episode"
    assert body["ref_id"] == ep_id


@pytest.mark.asyncio
async def test_play_bumps_view_count(
    auth_client, make_title, make_plan, make_active_subscription
) -> None:
    client, _, user = auth_client
    plan = await make_plan(code="monthly")
    await make_active_subscription(user_id=user.id, plan_id=plan.id)
    t = await make_title(slug="m", hls_url="https://test.example/m.m3u8")
    before = (await client.get(f"/v1/titles/{t.id}")).json()["view_count"]
    await client.get(f"/v1/titles/{t.id}/play")
    after = (await client.get(f"/v1/titles/{t.id}")).json()["view_count"]
    assert after == before + 1
