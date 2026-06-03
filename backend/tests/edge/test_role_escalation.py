"""Tests that prevent mass-assignment / role escalation attempts."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_signup_cannot_set_role(client) -> None:
    """Signup must not honour a `role` field even if the client sends one."""
    resp = await client.post(
        "/v1/auth/signup",
        json={
            "email": "sneaky@x.com",
            "password": "password123",
            "full_name": "Sneaky",
            "role": "admin",  # the attack — sneaking 'admin' into the payload
        },
    )
    # Pydantic ignores unknown fields by default (UserSignup doesn't declare extra='forbid'),
    # so the request succeeds — but the SERVICE hardcodes role='user'. Verify:
    assert resp.status_code == 201
    token = resp.json()["tokens"]["access_token"]
    me = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "user"  # NOT admin


@pytest.mark.asyncio
async def test_regular_user_cannot_promote_self(auth_client) -> None:
    """No endpoint lets a regular user change their own role.
    /v1/admin/users/{id}/role requires admin role itself."""
    client, _, user = auth_client
    resp = await client.patch(f"/v1/admin/users/{user.id}/role", json={"role": "admin"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_title_update_rejects_unknown_field(admin_client, make_title) -> None:
    """C17 — extra='forbid' on TitleUpdate blocks unknown keys."""
    client, _, _ = admin_client
    title = await make_title(slug="t")
    resp = await client.patch(
        f"/v1/admin/titles/{title.id}",
        json={"title": "Updated", "deleted_at": "2026-01-01T00:00:00Z"},
    )
    assert resp.status_code == 422  # extra='forbid' rejects deleted_at


@pytest.mark.asyncio
async def test_episode_update_rejects_unknown_field(admin_client) -> None:
    """C17 — extra='forbid' on EpisodeUpdate."""
    client, _, _ = admin_client
    # Create a series + season + episode via admin
    series_resp = await client.post(
        "/v1/admin/titles",
        json={"slug": "s", "type": "series", "title": "S", "status": "published"},
    )
    season_resp = await client.post(
        f"/v1/admin/titles/{series_resp.json()['id']}/seasons",
        json={"season_number": 1},
    )
    ep_resp = await client.post(
        f"/v1/admin/seasons/{season_resp.json()['id']}/episodes",
        json={"episode_number": 1, "name": "E1", "status": "published"},
    )
    ep_id = ep_resp.json()["id"]

    resp = await client.patch(
        f"/v1/admin/episodes/{ep_id}",
        json={"name": "Renamed", "season_id": 9999},  # season_id is not in EpisodeUpdate
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_content_manager_cannot_change_user_role(content_manager_client, make_user) -> None:
    client, _, _ = content_manager_client
    victim = await make_user(email="victim@x.com")
    resp = await client.patch(f"/v1/admin/users/{victim.id}/role", json={"role": "admin"})
    assert resp.status_code == 403
