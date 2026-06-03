"""
Razorpay client wrapper.

The official `razorpay` SDK is synchronous (uses `requests`). We wrap every
call in `asyncio.to_thread()` so we don't block the FastAPI event loop.

Singleton — built lazily so the app boots even without Razorpay credentials
(tests, dev-without-billing).
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
from functools import lru_cache
from typing import Any

import razorpay

from app.core.config import get_settings


class RazorpayNotConfigured(Exception):
    code = "razorpay_not_configured"
    message = "Razorpay credentials are not configured."


@lru_cache
def _client() -> razorpay.Client:
    settings = get_settings()
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise RazorpayNotConfigured
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


# ---- Plans -----------------------------------------------------------------


async def create_plan(
    *, period: str, interval: int, item_name: str, amount_paise: int, currency: str = "INR"
) -> dict[str, Any]:
    """
    period: 'monthly' | 'yearly' | 'weekly' | 'daily'
    interval: 1 = every period; 3 = every 3 periods (quarterly etc.)
    amount_paise: price in the smallest currency unit (paise for INR)
    """
    client = _client()
    payload = {
        "period": period,
        "interval": interval,
        "item": {"name": item_name, "amount": amount_paise, "currency": currency},
    }
    return await asyncio.to_thread(client.plan.create, payload)


# ---- Subscriptions ---------------------------------------------------------


async def create_subscription(
    *, plan_id: str, total_count: int = 12, customer_notify: bool = True, notes: dict | None = None
) -> dict[str, Any]:
    """
    total_count: number of billing cycles to attempt (12 = 1 year for monthly).
    Returns a Subscription with a `short_url` the client should redirect the user to.
    """
    client = _client()
    payload: dict[str, Any] = {
        "plan_id": plan_id,
        "total_count": total_count,
        "customer_notify": 1 if customer_notify else 0,
    }
    if notes:
        payload["notes"] = notes
    return await asyncio.to_thread(client.subscription.create, payload)


async def fetch_subscription(subscription_id: str) -> dict[str, Any]:
    client = _client()
    return await asyncio.to_thread(client.subscription.fetch, subscription_id)


async def cancel_subscription(subscription_id: str, *, cancel_at_cycle_end: bool = True) -> dict[str, Any]:
    """
    cancel_at_cycle_end=True keeps the sub active until the end of the current
    billing period. False cancels immediately.
    """
    client = _client()
    payload = {"cancel_at_cycle_end": 1 if cancel_at_cycle_end else 0}
    return await asyncio.to_thread(
        client.subscription.cancel, subscription_id, payload
    )


# ---- Orders (one-time payment per period) ----------------------------------


async def create_order(
    *, amount_paise: int, currency: str = "INR", receipt: str, notes: dict | None = None
) -> dict[str, Any]:
    """
    Create a Razorpay Order — works WITHOUT business activation (the path we use
    until the client's company completes KYC for live recurring).

    receipt: a short string of our own that ties this order back to a local row.
             Razorpay enforces uniqueness only within a 30-day window.
    notes:   key-value bag echoed back on the webhook. Put user_id, local subscription
             id here so the webhook handler can find the right row.
    """
    client = _client()
    payload: dict[str, Any] = {
        "amount": amount_paise,
        "currency": currency,
        "receipt": receipt[:40],  # Razorpay caps receipt at 40 chars
        "payment_capture": 1,     # auto-capture on payment success
    }
    if notes:
        payload["notes"] = notes
    return await asyncio.to_thread(client.order.create, payload)


async def fetch_order(order_id: str) -> dict[str, Any]:
    return await asyncio.to_thread(_client().order.fetch, order_id)


async def fetch_payment(payment_id: str) -> dict[str, Any]:
    return await asyncio.to_thread(_client().payment.fetch, payment_id)


def verify_payment_signature(
    *, order_id: str, payment_id: str, signature: str, secret: str | None = None
) -> bool:
    """
    Verify the signature Razorpay Checkout returns to the frontend on success.
    HMAC-SHA256 of `f"{order_id}|{payment_id}"` with our key_secret.

    This is separate from the webhook signature (which uses webhook_secret).
    """
    s = secret or get_settings().razorpay_key_secret
    if not s:
        return False
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    expected = hmac.new(s.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# ---- Webhook signature verification ----------------------------------------


def verify_webhook_signature(*, body: bytes, signature: str, secret: str | None = None) -> bool:
    """
    Razorpay sends `X-Razorpay-Signature` header on every webhook. We HMAC-SHA256
    the raw request body with our webhook secret and compare to it.

    Returns True iff signature matches. Constant-time compare prevents timing
    attacks.
    """
    s = secret or get_settings().razorpay_webhook_secret
    if not s:
        return False
    expected = hmac.new(s.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
