"""
Webhook endpoints.

Razorpay sends webhooks on every subscription state change. We verify the
HMAC-SHA256 signature against our RAZORPAY_WEBHOOK_SECRET, then dispatch to
billing.apply_razorpay_event() which updates the local Subscription row.

Idempotency: Razorpay retries on 5xx. apply_razorpay_event() is idempotent
(it just sets the status; double-applying is a no-op).
"""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.api.deps import DbSession
from app.core.logging import get_logger
from app.services import billing
from app.services import razorpay_client

router = APIRouter()
log = get_logger(__name__)


@router.post("/razorpay", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    db: DbSession,
    x_razorpay_signature: str | None = Header(default=None),
) -> dict:
    body = await request.body()

    # Signature MUST be verified before parsing JSON — if it's missing or wrong,
    # we 401 immediately without touching the payload.
    if not x_razorpay_signature or not razorpay_client.verify_webhook_signature(
        body=body, signature=x_razorpay_signature
    ):
        raise HTTPException(
            401,
            detail={"error": {"code": "invalid_signature", "message": "Webhook signature failed verification."}},
        )

    try:
        import json

        event = json.loads(body)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            400, detail={"error": {"code": "invalid_payload", "message": "Body is not valid JSON."}}
        ) from e

    outcome = await billing.apply_razorpay_event(db, event)
    log.info("razorpay_webhook", razorpay_event=event.get("event"), outcome=outcome)
    return {"received": True, "outcome": outcome}
