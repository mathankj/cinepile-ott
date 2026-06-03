"""
Razorpay billing provider tests.

We mock the razorpay_client module functions so tests don't hit Razorpay's
real test API. The unit under test is our billing service + webhook handler +
payment-verify endpoint.

Tests cover BOTH billing modes:
- orders         (default; no KYC needed; the path we use today)
- subscriptions  (kept for the day the client's business is KYC-activated)
"""
from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import patch

import pytest


# ---- Mode fixtures -----------------------------------------------------------


@pytest.fixture
def razorpay_orders(monkeypatch):
    """Force razorpay provider in Orders mode (default — no KYC needed)."""
    monkeypatch.setenv("BILLING_PROVIDER", "razorpay")
    monkeypatch.setenv("BILLING_MODE", "orders")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_FAKE")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "FAKE_SECRET")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "wh_test_secret")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def razorpay_subscriptions(monkeypatch):
    """Force razorpay provider in Subscriptions mode (needs business KYC IRL)."""
    monkeypatch.setenv("BILLING_PROVIDER", "razorpay")
    monkeypatch.setenv("BILLING_MODE", "subscriptions")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_FAKE")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "FAKE_SECRET")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "wh_test_secret")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ---- Orders mode (default) ---------------------------------------------------


@pytest.mark.asyncio
async def test_orders_subscribe_creates_order_and_returns_checkout_url(
    razorpay_orders, auth_client, make_plan
):
    client, _, _ = auth_client
    await make_plan(code="monthly", price_cents=19900)

    with patch(
        "app.services.razorpay_client.create_order",
        return_value={
            "id": "order_FAKE123",
            "amount": 19900,
            "currency": "INR",
            "status": "created",
        },
    ) as mock_order:
        resp = await client.post("/v1/subscriptions", json={"plan_code": "monthly"})

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["provider"] == "razorpay"
    assert body["status"] == "pending"
    # checkout_url points at our /test-checkout dev helper page (React replaces this in prod)
    assert body["checkout_url"].startswith("/test-checkout?")
    assert "order_id=order_FAKE123" in body["checkout_url"]
    assert "key_id=rzp_test_FAKE" in body["checkout_url"]
    assert "amount=19900" in body["checkout_url"]

    mock_order.assert_called_once()
    call_kwargs = mock_order.call_args.kwargs
    assert call_kwargs["amount_paise"] == 19900
    assert call_kwargs["currency"] == "INR"
    # The notes echo back on the webhook so we can find the local row
    assert call_kwargs["notes"]["user_id"]
    assert call_kwargs["notes"]["plan_code"] == "monthly"


@pytest.mark.asyncio
async def test_orders_payment_verify_endpoint_flips_to_active(
    razorpay_orders, auth_client, make_plan
):
    """Frontend POSTs razorpay_order_id+payment_id+signature; we verify + activate."""
    client, _, _ = auth_client
    await make_plan(code="monthly")

    # 1) Subscribe to get an order
    with patch(
        "app.services.razorpay_client.create_order",
        return_value={"id": "order_VFY1", "amount": 19900, "currency": "INR"},
    ):
        sub_resp = await client.post("/v1/subscriptions", json={"plan_code": "monthly"})
    assert sub_resp.json()["status"] == "pending"

    # 2) Build a valid signature for the verify call (HMAC of "order_id|payment_id" with key_secret)
    msg = b"order_VFY1|pay_FAKE"
    sig = hmac.new(b"FAKE_SECRET", msg, hashlib.sha256).hexdigest()

    verify = await client.post(
        "/v1/payments/verify",
        json={
            "razorpay_order_id": "order_VFY1",
            "razorpay_payment_id": "pay_FAKE",
            "razorpay_signature": sig,
        },
    )
    assert verify.status_code == 200, verify.text
    assert verify.json()["status"] == "active"
    assert verify.json()["checkout_url"] is None


@pytest.mark.asyncio
async def test_orders_payment_verify_rejects_bad_signature(
    razorpay_orders, auth_client, make_plan
):
    client, _, _ = auth_client
    await make_plan(code="monthly")
    with patch(
        "app.services.razorpay_client.create_order",
        return_value={"id": "order_VFY2", "amount": 19900, "currency": "INR"},
    ):
        await client.post("/v1/subscriptions", json={"plan_code": "monthly"})

    resp = await client.post(
        "/v1/payments/verify",
        json={
            "razorpay_order_id": "order_VFY2",
            "razorpay_payment_id": "pay_X",
            "razorpay_signature": "definitely-not-the-right-hmac",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"]["code"] == "invalid_signature"


@pytest.mark.asyncio
async def test_orders_webhook_payment_captured_activates(
    razorpay_orders, auth_client, make_plan, client
):
    cm_client, _, _ = auth_client
    await make_plan(code="monthly")

    with patch(
        "app.services.razorpay_client.create_order",
        return_value={"id": "order_WH1", "amount": 19900},
    ):
        await cm_client.post("/v1/subscriptions", json={"plan_code": "monthly"})

    body = json.dumps(
        {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_WH1",
                        "order_id": "order_WH1",
                        "amount": 19900,
                        "status": "captured",
                    }
                }
            },
        }
    ).encode("utf-8")
    sig = hmac.new(b"wh_test_secret", body, hashlib.sha256).hexdigest()

    resp = await client.post(
        "/v1/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["outcome"] == "applied_payment.captured"

    me = await cm_client.get("/v1/subscriptions/me")
    assert me.json()["status"] == "active"


@pytest.mark.asyncio
async def test_orders_webhook_payment_failed_keeps_pending(
    razorpay_orders, auth_client, make_plan, client
):
    cm_client, _, _ = auth_client
    await make_plan(code="monthly")
    with patch(
        "app.services.razorpay_client.create_order",
        return_value={"id": "order_FAIL", "amount": 19900},
    ):
        await cm_client.post("/v1/subscriptions", json={"plan_code": "monthly"})

    body = json.dumps(
        {
            "event": "payment.failed",
            "payload": {
                "payment": {"entity": {"id": "pay_FAIL", "order_id": "order_FAIL"}}
            },
        }
    ).encode("utf-8")
    sig = hmac.new(b"wh_test_secret", body, hashlib.sha256).hexdigest()

    resp = await client.post(
        "/v1/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    # User retains pending status so they can retry
    me = await cm_client.get("/v1/subscriptions/me")
    # subscriptions/me only returns ACTIVE subs; pending → None
    assert me.json() is None


# ---- Webhook signature gating (mode-independent) -----------------------------


@pytest.mark.asyncio
async def test_webhook_rejects_unsigned_request(razorpay_orders, client):
    resp = await client.post("/v1/webhooks/razorpay", json={"event": "payment.captured"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"]["code"] == "invalid_signature"


@pytest.mark.asyncio
async def test_webhook_rejects_wrong_signature(razorpay_orders, client):
    resp = await client.post(
        "/v1/webhooks/razorpay",
        json={"event": "payment.captured"},
        headers={"X-Razorpay-Signature": "definitely-not-the-right-hmac"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_webhook_unknown_order_returns_200(razorpay_orders, client):
    """Webhooks for orders we never created should return 200 (idempotent) with informative outcome."""
    body = json.dumps(
        {
            "event": "payment.captured",
            "payload": {
                "payment": {"entity": {"id": "pay_X", "order_id": "order_UNKNOWN"}}
            },
        }
    ).encode("utf-8")
    sig = hmac.new(b"wh_test_secret", body, hashlib.sha256).hexdigest()
    resp = await client.post(
        "/v1/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert "unknown_order" in resp.json()["outcome"]


# ---- Subscriptions mode (kept for when KYC is done) --------------------------


@pytest.mark.asyncio
async def test_subscriptions_subscribe_creates_plan_and_subscription(
    razorpay_subscriptions, auth_client, make_plan
):
    client, _, _ = auth_client
    await make_plan(code="monthly", price_cents=19900)

    with (
        patch(
            "app.services.razorpay_client.create_plan",
            return_value={"id": "plan_SUB123"},
        ) as mock_plan,
        patch(
            "app.services.razorpay_client.create_subscription",
            return_value={"id": "sub_SUB456", "short_url": "https://rzp.io/i/checkout"},
        ) as mock_sub,
    ):
        resp = await client.post("/v1/subscriptions", json={"plan_code": "monthly"})

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["checkout_url"] == "https://rzp.io/i/checkout"
    mock_plan.assert_called_once()
    mock_sub.assert_called_once()


@pytest.mark.asyncio
async def test_subscriptions_webhook_subscription_activated(
    razorpay_subscriptions, auth_client, make_plan, client
):
    cm_client, _, _ = auth_client
    await make_plan(code="monthly")
    with (
        patch(
            "app.services.razorpay_client.create_plan", return_value={"id": "plan_X"}
        ),
        patch(
            "app.services.razorpay_client.create_subscription",
            return_value={"id": "sub_INCOMING", "short_url": "https://rzp.io/i/x"},
        ),
    ):
        await cm_client.post("/v1/subscriptions", json={"plan_code": "monthly"})

    body = json.dumps(
        {
            "event": "subscription.activated",
            "payload": {"subscription": {"entity": {"id": "sub_INCOMING"}}},
        }
    ).encode("utf-8")
    sig = hmac.new(b"wh_test_secret", body, hashlib.sha256).hexdigest()
    resp = await client.post(
        "/v1/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    me = await cm_client.get("/v1/subscriptions/me")
    assert me.json()["status"] == "active"
