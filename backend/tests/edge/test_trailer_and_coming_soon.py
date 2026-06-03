"""Trailer endpoint (C7) and Coming Soon (C8) tests."""
from __future__ import annotations

import pytest


async def _login(client, email, password="password123"):
    r = await client.post("/v1/auth/login", json={"email": email, "password": password})
    return r.json()["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_trailer_endpoint_no_auth_required(client, make_user) -> None:
    """Trailers are marketing — public, no auth, no subscription.
    Set trailer_url via the admin update endpoint so we go through the same
    DB session as the test client."""
    await make_user(email="adm@x.com", role="admin")
    admin_token = await _login(client, "adm@x.com")
    client.headers["Authorization"] = f"Bearer {admin_token}"

    # Create title + set trailer_url via admin
    create = await client.post(
        "/v1/admin/titles",
        json={
            "slug": "with-trailer",
            "type": "movie",
            "title": "WT",
            "status": "published",
            "trailer_url": "https://example.com/trailer.m3u8",
        },
    )
    tid = create.json()["id"]

    # Anonymous fetch — trailer should be public
    del client.headers["Authorization"]
    resp = await client.get(f"/v1/titles/{tid}/trailer")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["trailer_url"] == "https://example.com/trailer.m3u8"


@pytest.mark.asyncio
async def test_trailer_404_when_none_configured(client, make_title) -> None:
    title = await make_title(slug="m")
    resp = await client.get(f"/v1/titles/{title.id}/trailer")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"]["code"] == "no_trailer"


@pytest.mark.asyncio
async def test_coming_soon_lists_scheduled_titles(client, make_user) -> None:
    """C8 — scheduled titles with future publish_at appear in coming-soon."""
    await make_user(email="adm@x.com", role="admin")
    admin_token = await _login(client, "adm@x.com")
    client.headers["Authorization"] = f"Bearer {admin_token}"

    create = await client.post(
        "/v1/admin/titles",
        json={"slug": "future-title", "type": "movie", "title": "Future", "status": "draft"},
    )
    tid = create.json()["id"]
    await client.post(
        f"/v1/admin/titles/{tid}/schedule",
        json={"publish_at": "2099-12-25T00:00:00Z"},
    )

    del client.headers["Authorization"]
    resp = await client.get("/v1/titles/coming-soon")
    assert resp.status_code == 200
    slugs = [t["slug"] for t in resp.json()]
    assert "future-title" in slugs


@pytest.mark.asyncio
async def test_coming_soon_excludes_already_published(client, make_title) -> None:
    await make_title(slug="published-already")
    resp = await client.get("/v1/titles/coming-soon")
    assert resp.status_code == 200
    slugs = [t["slug"] for t in resp.json()]
    assert "published-already" not in slugs


@pytest.mark.asyncio
async def test_coming_soon_excludes_past_publish_at(client, make_user) -> None:
    """Past publish_at auto-promotes to published when /v1/titles is read,
    so coming-soon shouldn't include it either."""
    await make_user(email="adm@x.com", role="admin")
    admin_token = await _login(client, "adm@x.com")
    client.headers["Authorization"] = f"Bearer {admin_token}"

    create = await client.post(
        "/v1/admin/titles",
        json={"slug": "past", "type": "movie", "title": "Past", "status": "draft"},
    )
    tid = create.json()["id"]
    await client.post(f"/v1/admin/titles/{tid}/schedule", json={"publish_at": "2020-01-01T00:00:00Z"})

    del client.headers["Authorization"]
    resp = await client.get("/v1/titles/coming-soon")
    slugs = [t["slug"] for t in resp.json()]
    assert "past" not in slugs
