"""
Frontend-side payment verification.

When the frontend Razorpay Checkout completes successfully, it returns three
values to the browser: razorpay_order_id, razorpay_payment_id, razorpay_signature.

The frontend POSTs them here to *immediately* confirm the subscription is active,
without waiting for the webhook to arrive. This is the standard Razorpay
"handler function on success" pattern.

The webhook (when it arrives) is still authoritative and idempotent — it just
acts as a back-up + handles cases where the user closes the tab right after pay.

Defence in depth before activating a subscription:
  1. HMAC signature check (proves the values came from Razorpay).
  2. Fetch the payment from Razorpay's API and require status == "captured"
     AND the paid amount to equal the plan amount — a valid signature on an
     authorized-but-not-captured or short-paid payment must not unlock access.
"""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, get_current_user_optional
from app.core.logging import get_logger
from app.core.security import TokenError, decode_checkout_token
from app.models.subscription import Plan, Subscription
from app.models.user import User
from app.schemas.subscription import SubscriptionRead
from app.services import razorpay_client

router = APIRouter()
log = get_logger(__name__)


class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


def _bad_request(code: str, message: str) -> HTTPException:
    return HTTPException(
        status.HTTP_400_BAD_REQUEST,
        detail={"error": {"code": code, "message": message}},
    )


async def _resolve_caller(
    db: AsyncSession, authorization: str | None, *, order_id: str
) -> User:
    """Who is allowed to verify a payment?

    1. A normally logged-in user (regular Bearer access token) — the prod
       Razorpay Checkout-JS flow.
    2. The dev /test-checkout page, whose URL carries a short-lived
       single-purpose token (purpose='checkout') instead of the user's real
       access token. That token is only honoured for the exact order it was
       minted for — it cannot touch any other endpoint or order.
    """
    user = await get_current_user_optional(db, authorization)
    if user is not None:
        return user

    # Fall back to a checkout-purpose token (dev test-checkout flow).
    if authorization:
        scheme, _, raw_token = authorization.partition(" ")
        if scheme.lower() == "bearer" and raw_token:
            try:
                claims = decode_checkout_token(raw_token)
            except TokenError:
                claims = None
            if claims is not None and claims.get("order_id") == order_id:
                token_user = await db.get(User, int(claims["sub"]))
                if token_user is not None and token_user.is_active:
                    return token_user

    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": "unauthorized", "message": "Not authenticated."}},
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/verify", response_model=SubscriptionRead)
async def verify_payment(
    payload: PaymentVerifyRequest,
    db: DbSession,
    authorization: str | None = Header(default=None),
) -> SubscriptionRead:
    """Verify Razorpay's signature for a completed Checkout payment and finalize the sub."""
    user = await _resolve_caller(db, authorization, order_id=payload.razorpay_order_id)

    ok = razorpay_client.verify_payment_signature(
        order_id=payload.razorpay_order_id,
        payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature,
    )
    if not ok:
        raise _bad_request(
            "invalid_signature", "Razorpay payment signature failed verification."
        )

    # Find the local Subscription row that owns this order
    sub = await db.scalar(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.provider_subscription_id == payload.razorpay_order_id,
        )
    )
    if sub is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "subscription_not_found",
                    "message": "No pending subscription found for that order.",
                }
            },
        )

    # Capture check — the signature only proves the callback is genuine, not
    # that the money actually moved. Confirm with Razorpay's API that the
    # payment is captured and the amount matches the plan price.
    try:
        payment = await razorpay_client.fetch_payment(payload.razorpay_payment_id)
    except Exception as e:  # noqa: BLE001 — SDK/network error: fail closed
        log.error("razorpay_payment_fetch_failed", error=str(e), sub_id=sub.id)
        raise _bad_request(
            "payment_fetch_failed", "Could not confirm the payment with Razorpay."
        ) from e

    if payment.get("status") != "captured":
        log.warning(
            "payment_not_captured",
            subscription_id=sub.id,
            payment_status=payment.get("status"),
        )
        raise _bad_request("payment_not_captured", "Payment has not been captured.")

    plan = await db.get(Plan, sub.plan_id)
    expected_amount = plan.price_cents if plan else None
    if expected_amount is None or payment.get("amount") != expected_amount:
        log.warning(
            "payment_amount_mismatch",
            subscription_id=sub.id,
            expected=expected_amount,
            actual=payment.get("amount"),
        )
        raise _bad_request(
            "amount_mismatch", "Payment amount does not match the plan price."
        )

    if sub.status != "active":
        sub.status = "active"
        sub.checkout_url = None
        await db.flush()
        log.info("payment_verified", subscription_id=sub.id, order_id=payload.razorpay_order_id)

    return SubscriptionRead.model_validate(sub)
