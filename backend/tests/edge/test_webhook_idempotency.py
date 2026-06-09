"""Webhook idempotency (C11) + replay-window (C12) tests."""
from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest


@pytest.fixture
def razorpay_env(monkeypatch):
    monkeypatch.setenv("BILLING_PROVIDER", "razorpay")
    monkeypatch.setenv("BILLING_MODE", "orders")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_FAKE")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "FAKE_SECRET")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "wh_test_secret")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _signed_webhook(body_dict: dict) -> tuple[bytes, str]:
    body = json.dumps(body_dict).encode("utf-8")
    sig = hmac.new(b"wh_test_secret", body, hashlib.sha256).hexdigest()
    return body, sig


@pytest.mark.asyncio
async def test_duplicate_event_id_returns_duplicate_outcome(
    razorpay_env, auth_client, make_plan, client
):
    """Two deliveries of the same event_id — second returns 'duplicate'
    without re-applying side effects."""
    from unittest.mock import patch

    cm_client, _, _ = auth_client
    await make_plan(code="monthly")
    with patch(
        "app.services.razorpay_client.create_order",
        return_value={"id": "order_DUP", "amount": 19900, "currency": "INR"},
    ):
        await cm_client.post("/v1/subscriptions", json={"plan_code": "monthly"})

    body, sig = _signed_webhook(
        {
            "event": "payment.captured",
            "created_at": int(time.time()),
            "payload": {
                "payment": {"entity": {"id": "pay_DUP", "order_id": "order_DUP", "status": "captured"}}
            },
        }
    )
    headers = {
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": "evt_DUPLICATE",
        "Content-Type": "application/json",
    }

    r1 = await client.post("/v1/webhooks/razorpay", content=body, headers=headers)
    assert r1.status_code == 200
    assert r1.json()["outcome"] == "applied_payment.captured"

    r2 = await client.post("/v1/webhooks/razorpay", content=body, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["outcome"] == "duplicate"


@pytest.mark.asyncio
async def test_old_event_rejected_as_stale(razorpay_env, client):
    """C12 — events older than 10 min are rejected (replay window)."""
    body, sig = _signed_webhook(
        {
            "event": "payment.captured",
            "created_at": int(time.time()) - 3600,  # 1 hour ago
            "payload": {"payment": {"entity": {"id": "x", "order_id": "x"}}},
        }
    )
    resp = await client.post(
        "/v1/webhooks/razorpay",
        content=body,
        headers={
            "X-Razorpay-Signature": sig,
            "X-Razorpay-Event-Id": "evt_OLD",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["outcome"] == "stale_event_rejected"


@pytest.mark.asyncio
async def test_webhook_without_event_id_is_rejected(razorpay_env, client):
    """No X-Razorpay-Event-Id → 400. Without it we can't de-dup, and
    processing anyway would silently bypass the idempotency guarantee.
    Razorpay always sends the header, so a request without it isn't Razorpay."""
    body, sig = _signed_webhook(
        {
            "event": "payment.captured",
            "created_at": int(time.time()),
            "payload": {"payment": {"entity": {"id": "p", "order_id": "order_NOID"}}},
        }
    )
    resp = await client.post(
        "/v1/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
        # No X-Razorpay-Event-Id
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"]["code"] == "missing_event_id"


@pytest.mark.asyncio
async def test_webhook_without_created_at_is_rejected(razorpay_env, client):
    """No created_at in the body → 400. Without it the replay window can't be
    enforced, so we fail closed instead of skipping the check."""
    body, sig = _signed_webhook(
        {
            "event": "payment.captured",
            "payload": {"payment": {"entity": {"id": "p", "order_id": "order_NOTS"}}},
        }
    )
    resp = await client.post(
        "/v1/webhooks/razorpay",
        content=body,
        headers={
            "X-Razorpay-Signature": sig,
            "X-Razorpay-Event-Id": "evt_NO_TS",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"]["code"] == "missing_created_at"
