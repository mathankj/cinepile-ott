"""
Subscription-expiry edge cases. These cover bug C1 from the QA audit:
an active-status sub whose current_period_end has passed must not grant
playback or qualify as "has active subscription".
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.asyncio
async def test_expired_active_sub_does_not_grant_playback(
    auth_client, make_title, make_plan, make_active_subscription, db_session
) -> None:
    """A sub that's status=active but past its current_period_end should
    behave as if it's expired for ALL playback gating purposes."""
    from app.models.subscription import Subscription

    client, _, user = auth_client
    plan = await make_plan(code="monthly")
    sub = await make_active_subscription(user_id=user.id, plan_id=plan.id)

    # Hand-edit DB: set current_period_end to a day ago, leave status='active'
    db_sub = await db_session.get(Subscription, sub.id)
    db_sub.current_period_end = datetime.now(tz=timezone.utc) - timedelta(days=1)
    await db_session.commit()

    title = await make_title(slug="m")
    resp = await client.get(f"/v1/titles/{title.id}/play")
    assert resp.status_code == 402, resp.text
    assert resp.json()["detail"]["error"]["code"] == "subscription_required"


@pytest.mark.asyncio
async def test_expired_sub_still_visible_in_me_endpoint(
    auth_client, make_plan, make_active_subscription, db_session
) -> None:
    """GET /v1/subscriptions/me should return the expired sub so the frontend
    can show a 'Renew' banner."""
    from app.models.subscription import Subscription

    client, _, user = auth_client
    plan = await make_plan(code="monthly")
    sub = await make_active_subscription(user_id=user.id, plan_id=plan.id)
    db_sub = await db_session.get(Subscription, sub.id)
    db_sub.current_period_end = datetime.now(tz=timezone.utc) - timedelta(days=1)
    await db_session.commit()

    resp = await client.get("/v1/subscriptions/me")
    assert resp.status_code == 200
    body = resp.json()
    # /me shows the row regardless of period; frontend handles UX
    assert body is not None
    assert body["status"] == "active"  # status didn't change, just the period


@pytest.mark.asyncio
async def test_user_with_expired_sub_can_resubscribe(
    auth_client, make_plan, make_active_subscription, db_session
) -> None:
    """If a user's old sub is expired (period ended), they should be able to
    subscribe again — the AlreadySubscribed check uses the period-aware filter."""
    from app.models.subscription import Subscription

    client, _, user = auth_client
    plan = await make_plan(code="monthly")
    sub = await make_active_subscription(user_id=user.id, plan_id=plan.id)
    db_sub = await db_session.get(Subscription, sub.id)
    db_sub.current_period_end = datetime.now(tz=timezone.utc) - timedelta(days=1)
    await db_session.commit()

    resp = await client.post("/v1/subscriptions", json={"plan_code": "monthly"})
    assert resp.status_code == 201, resp.text
    # New row, not the expired one
    assert resp.json()["id"] != sub.id


@pytest.mark.asyncio
async def test_future_period_end_grants_playback(
    auth_client, make_title, make_plan, make_active_subscription
) -> None:
    """Sanity — the normal path still works."""
    client, _, user = auth_client
    plan = await make_plan(code="monthly")
    await make_active_subscription(user_id=user.id, plan_id=plan.id)
    title = await make_title(slug="m", hls_url="https://test/m.m3u8")
    resp = await client.get(f"/v1/titles/{title.id}/play")
    assert resp.status_code == 200
