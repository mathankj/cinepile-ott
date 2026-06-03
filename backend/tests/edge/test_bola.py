"""
BOLA (Broken Object-Level Authorization) tests.

#1 OWASP API risk for OTT: can user A read/write user B's resources?
Every per-user endpoint must be gated by current_user.id == resource.user_id.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_user_a_cannot_see_user_b_continue_watching(
    client, make_user, make_title
) -> None:
    user_a = await make_user(email="a@x.com", password="password123")
    user_b = await make_user(email="b@x.com", password="password123")
    title = await make_title(slug="m")

    # User A posts progress
    a_login = await client.post("/v1/auth/login", json={"email": "a@x.com", "password": "password123"})
    client.headers["Authorization"] = f"Bearer {a_login.json()['tokens']['access_token']}"
    await client.post(f"/v1/titles/{title.id}/progress", json={"position_sec": 300, "total_sec": 1000})

    # Switch to user B
    b_login = await client.post("/v1/auth/login", json={"email": "b@x.com", "password": "password123"})
    client.headers["Authorization"] = f"Bearer {b_login.json()['tokens']['access_token']}"

    cw = await client.get("/v1/me/continue-watching")
    assert cw.status_code == 200
    # User B sees an empty list — never user A's progress
    assert cw.json()["items"] == []


@pytest.mark.asyncio
async def test_user_a_cannot_see_user_b_watchlist(
    client, make_user, make_title
) -> None:
    await make_user(email="a@x.com", password="password123")
    await make_user(email="b@x.com", password="password123")
    title = await make_title(slug="m")

    # A adds to list
    a_login = await client.post("/v1/auth/login", json={"email": "a@x.com", "password": "password123"})
    client.headers["Authorization"] = f"Bearer {a_login.json()['tokens']['access_token']}"
    await client.post(f"/v1/me/list/{title.id}")

    # B's list must be empty
    b_login = await client.post("/v1/auth/login", json={"email": "b@x.com", "password": "password123"})
    client.headers["Authorization"] = f"Bearer {b_login.json()['tokens']['access_token']}"
    assert (await client.get("/v1/me/list")).json()["items"] == []


@pytest.mark.asyncio
async def test_user_a_cannot_see_user_b_reactions(
    client, make_user, make_title
) -> None:
    await make_user(email="a@x.com", password="password123")
    await make_user(email="b@x.com", password="password123")
    title = await make_title(slug="m")

    a_login = await client.post("/v1/auth/login", json={"email": "a@x.com", "password": "password123"})
    client.headers["Authorization"] = f"Bearer {a_login.json()['tokens']['access_token']}"
    await client.put(f"/v1/titles/{title.id}/reaction", json={"kind": "thumbs_up"})

    b_login = await client.post("/v1/auth/login", json={"email": "b@x.com", "password": "password123"})
    client.headers["Authorization"] = f"Bearer {b_login.json()['tokens']['access_token']}"
    assert (await client.get("/v1/me/reactions")).json()["items"] == []


@pytest.mark.asyncio
async def test_user_a_cannot_see_user_b_subscription(
    client, make_user, make_plan, make_active_subscription
) -> None:
    user_a = await make_user(email="a@x.com", password="password123")
    user_b = await make_user(email="b@x.com", password="password123")
    plan = await make_plan(code="monthly")
    await make_active_subscription(user_id=user_a.id, plan_id=plan.id)
    # B has no subscription

    b_login = await client.post("/v1/auth/login", json={"email": "b@x.com", "password": "password123"})
    client.headers["Authorization"] = f"Bearer {b_login.json()['tokens']['access_token']}"
    me = await client.get("/v1/subscriptions/me")
    # User B sees None — they don't have a sub. Never A's row.
    assert me.json() is None
