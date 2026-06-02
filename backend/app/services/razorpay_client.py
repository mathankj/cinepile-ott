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
