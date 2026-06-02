"""Admin endpoint tests."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_regular_user_blocked_from_admin(auth_client) -> None:
    client, _, _ = auth_client
    resp = await client.post(
        "/v1/admin/films",
        json={"slug": "x", "title": "X"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_create_film(admin_client) -> None:
    client, _, _ = admin_client
    resp = await client.post(
        "/v1/admin/films",
        json={
            "slug": "big-buck-bunny",
            "title": "Big Buck Bunny",
            "synopsis": "A bunny film.",
            "release_year": 2008,
            "runtime_minutes": 10,
            "status": "published",
            "hls_manifest_url": "https://test.example/bbb.m3u8",
            "category_slugs": ["animation"],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "published"
    assert body["published_at"] is not None
    assert any(a["kind"] == "hls_manifest" for a in body["assets"])


@pytest.mark.asyncio
async def test_admin_create_rejects_duplicate_slug(admin_client) -> None:
    client, _, _ = admin_client
    payload = {"slug": "dup", "title": "Dup"}
    await client.post("/v1/admin/films", json=payload)
    r2 = await client.post("/v1/admin/films", json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_admin_update_film(admin_client, make_film) -> None:
    client, _, _ = admin_client
    film = await make_film(slug="x", status="draft")
    resp = await client.patch(
        f"/v1/admin/films/{film.id}", json={"status": "published"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"


@pytest.mark.asyncio
async def test_admin_soft_delete(admin_client, make_film) -> None:
    client, _, _ = admin_client
    film = await make_film(slug="x")
    r = await client.delete(f"/v1/admin/films/{film.id}")
    assert r.status_code == 204
    # Public should no longer see it
    r2 = await client.get(f"/v1/films/{film.id}")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_admin_list_users(admin_client, make_user) -> None:
    client, _, _ = admin_client
    await make_user(email="extra@example.com")
    resp = await client.get("/v1/admin/users")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2  # admin + extra
