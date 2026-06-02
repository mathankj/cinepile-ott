"""Admin V1.5: roles, title/season/episode CRUD, scheduling, audit log."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


# ---- Role gates --------------------------------------------------------------


@pytest.mark.asyncio
async def test_regular_user_blocked_from_admin(auth_client) -> None:
    client, _, _ = auth_client
    resp = await client.post("/v1/admin/titles", json={"slug": "x", "type": "movie", "title": "X"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_content_manager_can_write_catalog(content_manager_client) -> None:
    client, _, _ = content_manager_client
    resp = await client.post(
        "/v1/admin/titles",
        json={"slug": "cm-movie", "type": "movie", "title": "CM Movie", "status": "published"},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_content_manager_cannot_manage_users(content_manager_client, make_user) -> None:
    client, _, _ = content_manager_client
    extra = await make_user(email="someone@example.com")
    resp = await client.get("/v1/admin/users")
    assert resp.status_code == 403


# ---- Title CRUD --------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_create_movie(admin_client) -> None:
    client, _, _ = admin_client
    resp = await client.post(
        "/v1/admin/titles",
        json={
            "slug": "bbb",
            "type": "movie",
            "title": "Big Buck Bunny",
            "synopsis": "Bunny.",
            "release_year": 2008,
            "runtime_minutes": 10,
            "status": "published",
            "hls_manifest_url": "https://test.example/bbb.m3u8",
            "genre_slugs": ["animation"],  # genre auto-resolved (won't create — empty)
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "published"
    assert body["published_at"] is not None
    assert any(a["kind"] == "hls_manifest" for a in body["assets"])


@pytest.mark.asyncio
async def test_admin_create_series_then_seasons_and_episodes(admin_client) -> None:
    client, _, _ = admin_client
    series_resp = await client.post(
        "/v1/admin/titles",
        json={"slug": "show", "type": "series", "title": "The Show", "status": "published"},
    )
    assert series_resp.status_code == 201
    series_id = series_resp.json()["id"]

    season_resp = await client.post(
        f"/v1/admin/titles/{series_id}/seasons", json={"season_number": 1, "name": "S1"}
    )
    assert season_resp.status_code == 201
    season_id = season_resp.json()["id"]

    ep_resp = await client.post(
        f"/v1/admin/seasons/{season_id}/episodes",
        json={
            "episode_number": 1,
            "name": "Pilot",
            "runtime_seconds": 2400,
            "status": "published",
            "intro_start_sec": 0,
            "intro_end_sec": 60,
            "credits_start_sec": 2280,
            "next_episode_cue_sec": 2350,
            "hls_manifest_url": "https://test.example/show-s1-e1.m3u8",
        },
    )
    assert ep_resp.status_code == 201, ep_resp.text
    body = ep_resp.json()
    assert body["intro_end_sec"] == 60
    assert any(a["kind"] == "hls_manifest" for a in body["assets"])


@pytest.mark.asyncio
async def test_duplicate_slug_rejected(admin_client) -> None:
    client, _, _ = admin_client
    p = {"slug": "dup", "type": "movie", "title": "Dup"}
    r1 = await client.post("/v1/admin/titles", json=p)
    assert r1.status_code == 201
    r2 = await client.post("/v1/admin/titles", json=p)
    assert r2.status_code == 409


# ---- Lifecycle ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_schedule_and_publish_flow(admin_client) -> None:
    client, _, _ = admin_client
    r = await client.post(
        "/v1/admin/titles",
        json={"slug": "sched", "type": "movie", "title": "Sched", "status": "draft"},
    )
    tid = r.json()["id"]

    future = (datetime.now(tz=timezone.utc) + timedelta(days=7)).isoformat()
    sch = await client.post(f"/v1/admin/titles/{tid}/schedule", json={"publish_at": future})
    assert sch.status_code == 200
    assert sch.json()["status"] == "scheduled"

    pub = await client.post(f"/v1/admin/titles/{tid}/publish")
    assert pub.status_code == 200
    assert pub.json()["status"] == "published"


@pytest.mark.asyncio
async def test_auto_promote_on_read(admin_client, content_manager_client, db_session) -> None:
    """Title scheduled with publish_at in the past flips to published on next read."""
    admin, _, _ = admin_client
    past = (datetime.now(tz=timezone.utc) - timedelta(minutes=5)).isoformat()
    r = await admin.post(
        "/v1/admin/titles",
        json={"slug": "past", "type": "movie", "title": "Past", "status": "draft"},
    )
    tid = r.json()["id"]
    await admin.post(f"/v1/admin/titles/{tid}/schedule", json={"publish_at": past})

    # public read triggers auto-promote
    listing = (await admin.get("/v1/titles")).json()
    slugs = {i["slug"] for i in listing["items"]}
    assert "past" in slugs


@pytest.mark.asyncio
async def test_archive_and_soft_delete(admin_client) -> None:
    client, _, _ = admin_client
    r = await client.post(
        "/v1/admin/titles",
        json={"slug": "x", "type": "movie", "title": "X", "status": "published"},
    )
    tid = r.json()["id"]

    ar = await client.post(f"/v1/admin/titles/{tid}/archive")
    assert ar.json()["status"] == "archived"

    rm = await client.delete(f"/v1/admin/titles/{tid}")
    assert rm.status_code == 204

    # gone from public
    assert (await client.get(f"/v1/titles/{tid}")).status_code == 404


# ---- Audio + subtitle tracks -------------------------------------------------


@pytest.mark.asyncio
async def test_replace_audio_tracks(admin_client) -> None:
    client, _, _ = admin_client
    r = await client.post("/v1/admin/titles", json={"slug": "tracks", "type": "movie", "title": "Tracks"})
    tid = r.json()["id"]

    upd = await client.put(
        f"/v1/admin/titles/{tid}/audio-tracks",
        json={"tracks": [{"language": "en", "kind": "original"}, {"language": "ta", "kind": "dub"}]},
    )
    assert upd.status_code == 200
    detail = (await client.get(f"/v1/admin/titles/{tid}"
              if False else f"/v1/titles/{tid}")).json()
    # not necessarily published; let's flip then re-read
    await client.post(f"/v1/admin/titles/{tid}/publish")
    detail = (await client.get(f"/v1/titles/{tid}")).json()
    langs = [t["language"] for t in detail["audio_tracks"]]
    assert "en" in langs and "ta" in langs


# ---- Audit log ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_log_records_writes(admin_client) -> None:
    client, _, _ = admin_client
    r = await client.post(
        "/v1/admin/titles",
        json={"slug": "audited", "type": "movie", "title": "A", "status": "published"},
    )
    tid = r.json()["id"]

    await client.patch(f"/v1/admin/titles/{tid}", json={"title": "A2"})
    await client.post(f"/v1/admin/titles/{tid}/archive")

    audit = await client.get("/v1/admin/audit", params={"entity_type": "title", "entity_id": tid})
    assert audit.status_code == 200
    actions = [e["action"] for e in audit.json()["items"]]
    # Most-recent first
    assert "title.archived" in actions
    assert "title.update" in actions
    assert "title.create" in actions


# ---- User role change (admin only) -------------------------------------------


@pytest.mark.asyncio
async def test_admin_can_change_role(admin_client, make_user) -> None:
    client, _, _ = admin_client
    u = await make_user(email="promote@example.com")
    r = await client.patch(f"/v1/admin/users/{u.id}/role", json={"role": "content_manager"})
    assert r.status_code == 200
    assert r.json()["role"] == "content_manager"


@pytest.mark.asyncio
async def test_role_change_invalidates_existing_token(admin_client, make_user, client) -> None:
    """Bumping session_version on role change means the user's old token stops working."""
    admin, _, _ = admin_client
    u = await make_user(email="rotate@example.com")
    login = await client.post(
        "/v1/auth/login", json={"email": "rotate@example.com", "password": "password123"}
    )
    old_token = login.json()["tokens"]["access_token"]

    await admin.patch(f"/v1/admin/users/{u.id}/role", json={"role": "content_manager"})

    me = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert me.status_code == 401
