"""Subscription endpoint tests."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_plans(client, make_plan) -> None:
    await make_plan(code="monthly", price_cents=19900)
    await make_plan(code="annual", price_cents=199000)
    resp = await client.get("/v1/plans")
    assert resp.status_code == 200
    codes = [p["code"] for p in resp.json()]
    assert "monthly" in codes and "annual" in codes


@pytest.mark.asyncio
async def test_subscribe_requires_auth(client) -> None:
    resp = await client.post("/v1/subscriptions", json={"plan_code": "monthly"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_subscribe_happy_path(auth_client, make_plan) -> None:
    client, _, _ = auth_client
    await make_plan(code="monthly")
    resp = await client.post("/v1/subscriptions", json={"plan_code": "monthly"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "active"
    assert body["provider"] == "mock"


@pytest.mark.asyncio
async def test_subscribe_rejects_unknown_plan(auth_client) -> None:
    client, _, _ = auth_client
    resp = await client.post("/v1/subscriptions", json={"plan_code": "nonsense"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_double_subscribe_blocked(auth_client, make_plan) -> None:
    client, _, _ = auth_client
    await make_plan(code="monthly")
    r1 = await client.post("/v1/subscriptions", json={"plan_code": "monthly"})
    assert r1.status_code == 201
    r2 = await client.post("/v1/subscriptions", json={"plan_code": "monthly"})
    assert r2.status_code == 409
    assert r2.json()["detail"]["error"]["code"] == "already_subscribed"


@pytest.mark.asyncio
async def test_cancel_subscription(auth_client, make_plan) -> None:
    client, _, _ = auth_client
    await make_plan(code="monthly")
    await client.post("/v1/subscriptions", json={"plan_code": "monthly"})
    resp = await client.post("/v1/subscriptions/cancel")
    assert resp.status_code == 200
    assert resp.json()["subscription"]["cancel_at_period_end"] is True


@pytest.mark.asyncio
async def test_get_my_subscription(auth_client, make_plan) -> None:
    client, _, _ = auth_client
    await make_plan(code="monthly")
    await client.post("/v1/subscriptions", json={"plan_code": "monthly"})
    resp = await client.get("/v1/subscriptions/me")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"
