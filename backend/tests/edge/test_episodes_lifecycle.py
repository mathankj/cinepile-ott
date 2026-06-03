"""Episode-level edge cases — weekly release pattern, parent series gating."""
from __future__ import annotations

import pytest


async def _login(client, email, password="password123"):
    r = await client.post("/v1/auth/login", json={"email": email, "password": password})
    return r.json()["tokens"]["access_token"]


def _as(client, token):
    client.headers["Authorization"] = f"Bearer {token}"


@pytest.mark.asyncio
async def test_weekly_release_pattern(client, make_user) -> None:
    """A series has S1E1 published while S1E2 is still scheduled.
    The season detail endpoint returns both rows; only E1 has status=published."""
    await make_user(email="adm@x.com", role="admin")
    admin_token = await _login(client, "adm@x.com")
    _as(client, admin_token)

    series_resp = await client.post(
        "/v1/admin/titles",
        json={"slug": "weekly", "type": "series", "title": "Weekly", "status": "published"},
    )
    series_id = series_resp.json()["id"]
    season_resp = await client.post(
        f"/v1/admin/titles/{series_id}/seasons", json={"season_number": 1}
    )
    season_id = season_resp.json()["id"]

    await client.post(
        f"/v1/admin/seasons/{season_id}/episodes",
        json={"episode_number": 1, "name": "Pilot", "status": "published"},
    )
    await client.post(
        f"/v1/admin/seasons/{season_id}/episodes",
        json={
            "episode_number": 2,
            "name": "Episode 2",
            "status": "scheduled",
            "publish_at": "2099-01-01T00:00:00Z",
        },
    )

    # Public read shows both — frontend renders scheduled as a "coming soon" card.
    del client.headers["Authorization"]
    season = await client.get(f"/v1/titles/{series_id}/seasons/1")
    assert season.status_code == 200
    statuses = sorted([e["status"] for e in season.json()["episodes"]])
    assert "published" in statuses
    assert "scheduled" in statuses


@pytest.mark.asyncio
async def test_episode_play_blocked_if_parent_series_archived(
    client, make_user, make_plan, make_active_subscription, make_series_with_episodes
) -> None:
    """C4 — episode play must check the parent series isn't archived."""
    admin = await make_user(email="adm@x.com", role="admin")
    user = await make_user(email="usr@x.com")
    plan = await make_plan(code="monthly")
    await make_active_subscription(user_id=user.id, plan_id=plan.id)

    series = await make_series_with_episodes(slug="show", seasons=1, episodes_per_season=1)
    user_token = await _login(client, "usr@x.com")
    admin_token = await _login(client, "adm@x.com")

    # As user — play works while series is published
    _as(client, user_token)
    detail = await client.get(f"/v1/titles/{series.id}/seasons/1")
    ep_id = detail.json()["episodes"][0]["id"]
    play_ok = await client.get(f"/v1/episodes/{ep_id}/play")
    assert play_ok.status_code == 200

    # As admin — archive the series
    _as(client, admin_token)
    archive = await client.post(f"/v1/admin/titles/{series.id}/archive")
    assert archive.status_code == 200

    # Back as user — episode play must now 404
    _as(client, user_token)
    play_after = await client.get(f"/v1/episodes/{ep_id}/play")
    assert play_after.status_code == 404


@pytest.mark.asyncio
async def test_episode_play_blocked_if_parent_soft_deleted(
    client, make_user, make_plan, make_active_subscription, make_series_with_episodes
) -> None:
    admin = await make_user(email="adm@x.com", role="admin")
    user = await make_user(email="usr@x.com")
    plan = await make_plan(code="monthly")
    await make_active_subscription(user_id=user.id, plan_id=plan.id)
    series = await make_series_with_episodes(slug="show", seasons=1, episodes_per_season=1)

    user_token = await _login(client, "usr@x.com")
    admin_token = await _login(client, "adm@x.com")

    _as(client, user_token)
    detail = await client.get(f"/v1/titles/{series.id}/seasons/1")
    ep_id = detail.json()["episodes"][0]["id"]
    play_ok = await client.get(f"/v1/episodes/{ep_id}/play")
    assert play_ok.status_code == 200

    _as(client, admin_token)
    await client.delete(f"/v1/admin/titles/{series.id}")

    _as(client, user_token)
    play_after = await client.get(f"/v1/episodes/{ep_id}/play")
    assert play_after.status_code == 404
