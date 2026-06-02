"""
Razorpay billing provider tests.

We mock the razorpay_client module functions so tests don't hit Razorpay's
real test API. The unit under test is our billing service + webhook handler.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest


@pytest.fixture
def razorpay_provider(monkeypatch):
    """Force billing_provider to razorpay for this test only."""
    # Patch the cached settings to return razorpay
    monkeypatch.setenv("BILLING_PROVIDER", "razorpay")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_FAKE")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "FAKE_SECRET")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "wh_test_secret")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_razorpay_subscribe_creates_plan_and_subscription(
    razorpay_provider, auth_client, make_plan
):
    client, _, _ = auth_client
    await make_plan(code="monthly", price_cents=19900)

    with (
        patch(
            "app.services.razorpay_client.create_plan",
            return_value={"id": "plan_FAKE123", "period": "monthly"},
        ) as mock_plan,
        patch(
            "app.services.razorpay_client.create_subscription",
            return_value={
                "id": "sub_FAKE456",
                "short_url": "https://rzp.io/i/checkout-link",
                "status": "created",
            },
        ) as mock_sub,
    ):
        resp = await client.post("/v1/subscriptions", json={"plan_code": "monthly"})

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["provider"] == "razorpay"
    assert body["status"] == "pending"  # pending until user completes checkout
    assert body["checkout_url"] == "https://rzp.io/i/checkout-link"

    mock_plan.assert_called_once()
    mock_sub.assert_called_once()


@pytest.mark.asyncio
async def test_razorpay_plan_id_cached_on_second_subscribe(
    razorpay_provider, auth_client, make_user, make_plan, db_session
):
    """First subscribe creates the Razorpay plan; second sub on same plan reuses it."""
    client, _, _ = auth_client
    plan = await make_plan(code="monthly")
    plan_id = plan.id

    with (
        patch(
            "app.services.razorpay_client.create_plan",
            return_value={"id": "plan_FAKE123"},
        ) as mock_plan,
        patch(
            "app.services.razorpay_client.create_subscription",
            return_value={"id": "sub_FAKE1", "short_url": "https://rzp.io/i/x"},
        ),
    ):
        r1 = await client.post("/v1/subscriptions", json={"plan_code": "monthly"})
    assert r1.status_code == 201

    # A second user subscribes to the same plan — Razorpay plan create should NOT be called again
    u2 = await make_user(email="u2@example.com")
    login = await client.post(
        "/v1/auth/login", json={"email": "u2@example.com", "password": "password123"}
    )
    client.headers["Authorization"] = f"Bearer {login.json()['tokens']['access_token']}"

    with (
        patch("app.services.razorpay_client.create_plan") as mock_plan_2,
        patch(
            "app.services.razorpay_client.create_subscription",
            return_value={"id": "sub_FAKE2", "short_url": "https://rzp.io/i/y"},
        ),
    ):
        r2 = await client.post("/v1/subscriptions", json={"plan_code": "monthly"})
    assert r2.status_code == 201
    mock_plan_2.assert_not_called()  # cached on the Plan row


@pytest.mark.asyncio
async def test_webhook_rejects_unsigned_request(razorpay_provider, client):
    resp = await client.post("/v1/webhooks/razorpay", json={"event": "subscription.activated"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"]["code"] == "invalid_signature"


@pytest.mark.asyncio
async def test_webhook_rejects_wrong_signature(razorpay_provider, client):
    resp = await client.post(
        "/v1/webhooks/razorpay",
        json={"event": "subscription.activated"},
        headers={"X-Razorpay-Signature": "definitely-not-the-right-hmac"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_webhook_activates_subscription(razorpay_provider, auth_client, make_plan, client):
    import hashlib
    import hmac

    cm_client, _, _ = auth_client
    await make_plan(code="monthly")
    with (
        patch(
            "app.services.razorpay_client.create_plan",
            return_value={"id": "plan_FAKE"},
        ),
        patch(
            "app.services.razorpay_client.create_subscription",
            return_value={"id": "sub_INCOMING", "short_url": "https://rzp.io/i/x"},
        ),
    ):
        sub_resp = await cm_client.post("/v1/subscriptions", json={"plan_code": "monthly"})
    assert sub_resp.json()["status"] == "pending"

    # Build a properly-signed webhook
    body = json.dumps(
        {
            "event": "subscription.activated",
            "payload": {"subscription": {"entity": {"id": "sub_INCOMING"}}},
        }
    ).encode("utf-8")
    sig = hmac.new(b"wh_test_secret", body, hashlib.sha256).hexdigest()

    # Webhooks don't require an auth header
    wh_client = client  # use the fresh unauthed client
    resp = await wh_client.post(
        "/v1/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["outcome"] == "applied_subscription.activated"

    # Subscription should now be active and checkout_url cleared
    me = await cm_client.get("/v1/subscriptions/me")
    assert me.json()["status"] == "active"
    assert me.json()["checkout_url"] is None


@pytest.mark.asyncio
async def test_webhook_unknown_subscription_returns_known(razorpay_provider, client):
    import hashlib
    import hmac

    body = json.dumps(
        {
            "event": "subscription.activated",
            "payload": {"subscription": {"entity": {"id": "sub_NOTKNOWN"}}},
        }
    ).encode("utf-8")
    sig = hmac.new(b"wh_test_secret", body, hashlib.sha256).hexdigest()

    resp = await client.post(
        "/v1/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
    )
    # 200 with informative outcome — webhooks should never return 5xx for unknown
    # subs because Razorpay will retry indefinitely
    assert resp.status_code == 200
    assert "unknown_subscription" in resp.json()["outcome"]
