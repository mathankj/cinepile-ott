"""
Frontend-side payment verification.

When the frontend Razorpay Checkout completes successfully, it returns three
values to the browser: razorpay_order_id, razorpay_payment_id, razorpay_signature.

The frontend POSTs them here to *immediately* confirm the subscription is active,
without waiting for the webhook to arrive. This is the standard Razorpay
"handler function on success" pattern.

The webhook (when it arrives) is still authoritative and idempotent — it just
acts as a back-up + handles cases where the user closes the tab right after pay.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.logging import get_logger
from app.models.subscription import Subscription
from app.schemas.subscription import SubscriptionRead
from app.services import razorpay_client

router = APIRouter()
log = get_logger(__name__)


class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.post("/verify", response_model=SubscriptionRead)
async def verify_payment(
    payload: PaymentVerifyRequest, db: DbSession, user: CurrentUser
) -> SubscriptionRead:
    """Verify Razorpay's signature for a completed Checkout payment and finalize the sub."""
    ok = razorpay_client.verify_payment_signature(
        order_id=payload.razorpay_order_id,
        payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature,
    )
    if not ok:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "invalid_signature",
                    "message": "Razorpay payment signature failed verification.",
                }
            },
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

    if sub.status != "active":
        sub.status = "active"
        sub.checkout_url = None
        await db.flush()
        log.info("payment_verified", subscription_id=sub.id, order_id=payload.razorpay_order_id)

    return SubscriptionRead.model_validate(sub)
