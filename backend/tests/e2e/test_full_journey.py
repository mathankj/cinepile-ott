"""
End-to-end user journey: signup → browse plans → subscribe → browse films →
search → play → record progress → continue-watching → logout.

This is the test that proves "the backend works for what the frontend needs."
If this passes, a real user could complete every Phase 1 V1 happy path.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_full_user_journey(client, make_plan, make_film) -> None:
    # Seed catalog + plans (admin would do this; we shortcut via fixtures)
    plan = await make_plan(code="monthly", price_cents=19900)
    film1 = await make_film(slug="big-buck-bunny", title="Big Buck Bunny", category_slugs=["animation"])
    film2 = await make_film(slug="sintel", title="Sintel", category_slugs=["animation"])
    await make_film(slug="tears-of-steel", title="Tears of Steel", category_slugs=["sci-fi"])

    # 1) Sign up
    signup = await client.post(
        "/v1/auth/signup",
        json={"email": "newuser@example.com", "password": "supersecret9", "full_name": "New"},
    )
    assert signup.status_code == 201
    tokens = signup.json()["tokens"]
    client.headers["Authorization"] = f"Bearer {tokens['access_token']}"

    # 2) Browse plans
    plans = await client.get("/v1/plans")
    assert plans.status_code == 200
    assert any(p["code"] == "monthly" for p in plans.json())

    # 3) Subscribe
    sub = await client.post("/v1/subscriptions", json={"plan_code": "monthly"})
    assert sub.status_code == 201, sub.text

    # 4) Browse catalog
    listing = await client.get("/v1/films")
    assert listing.status_code == 200
    assert listing.json()["total"] == 3

    # 5) Filter by category
    animation = await client.get("/v1/films", params={"category": "animation"})
    assert animation.json()["total"] == 2

    # 6) Search
    bunny = await client.get("/v1/films/search", params={"q": "bunny"})
    assert len(bunny.json()) == 1

    # 7) Detail
    detail = await client.get(f"/v1/films/{film1.id}")
    assert detail.status_code == 200
    assert detail.json()["slug"] == "big-buck-bunny"

    # 8) Play
    play = await client.get(f"/v1/films/{film1.id}/play")
    assert play.status_code == 200, play.text
    assert play.json()["manifest_url"]

    # 9) Record progress on two films
    p1 = await client.post(
        f"/v1/history/{film1.id}/progress", json={"position_sec": 300, "total_sec": 600}
    )
    assert p1.status_code == 204
    p2 = await client.post(
        f"/v1/history/{film2.id}/progress", json={"position_sec": 100, "total_sec": 1000}
    )
    assert p2.status_code == 204

    # 10) Continue-watching list, most recent first
    cw = await client.get("/v1/history")
    items = cw.json()["items"]
    assert len(items) == 2
    assert items[0]["film"]["slug"] == "sintel"  # most recently progressed
    assert items[1]["film"]["slug"] == "big-buck-bunny"

    # 11) Remove from history
    rm = await client.delete(f"/v1/history/{film1.id}")
    assert rm.status_code == 204
    assert len((await client.get("/v1/history")).json()["items"]) == 1

    # 12) Logout
    out = await client.post("/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert out.status_code == 204

    # 13) Refresh after logout must fail
    bad = await client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert bad.status_code == 401
