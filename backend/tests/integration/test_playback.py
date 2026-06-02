"""Playback endpoint tests — entitlement gating + token issuance."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_play_requires_auth(client, make_film) -> None:
    film = await make_film(slug="x")
    resp = await client.get(f"/v1/films/{film.id}/play")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_play_requires_subscription(auth_client, make_film) -> None:
    client, _, _ = auth_client
    film = await make_film(slug="x")
    resp = await client.get(f"/v1/films/{film.id}/play")
    assert resp.status_code == 402
    assert resp.json()["detail"]["error"]["code"] == "subscription_required"


@pytest.mark.asyncio
async def test_play_with_active_subscription(
    auth_client, make_film, make_plan, make_active_subscription
) -> None:
    client, _, user = auth_client
    plan = await make_plan(code="monthly")
    await make_active_subscription(user_id=user.id, plan_id=plan.id)
    film = await make_film(slug="x", hls_url="https://test.example/x.m3u8")

    resp = await client.get(f"/v1/films/{film.id}/play")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["manifest_url"] == "https://test.example/x.m3u8"
    assert body["token"]
    assert body["film_id"] == film.id


@pytest.mark.asyncio
async def test_play_film_without_asset_409(
    auth_client, make_film, make_plan, make_active_subscription
) -> None:
    client, _, user = auth_client
    plan = await make_plan(code="monthly")
    await make_active_subscription(user_id=user.id, plan_id=plan.id)
    film = await make_film(slug="no-asset", hls_url=None)

    resp = await client.get(f"/v1/films/{film.id}/play")
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"]["code"] == "no_playable_asset"
