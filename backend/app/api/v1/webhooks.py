"""
Webhook endpoints.

Razorpay sends webhooks on every subscription/payment state change. We:
  1. Verify the HMAC-SHA256 signature against RAZORPAY_WEBHOOK_SECRET
     (constant-time compare).
  2. Require `created_at` in the body and the `X-Razorpay-Event-Id` header —
     without them the replay window and idempotency checks below would be
     silently skipped, so we reject (400) instead of processing.
  3. Reject events older than 10 minutes (replay-attack window).
  4. Idempotency-check via the `X-Razorpay-Event-Id` header against the
     webhook_events table. Duplicate delivery → 200 with `outcome="duplicate"`,
     no side effects.
  5. Dispatch to billing.apply_razorpay_event(), which is itself idempotent.

Idempotency: Razorpay retries on 5xx. apply_razorpay_event() is idempotent at
the business-logic layer; the event_id store guarantees we never even reach
that layer twice for the same event.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession
from app.core.logging import get_logger
from app.models.webhook_event import WebhookEvent
from app.services import billing
from app.services import razorpay_client

router = APIRouter()
log = get_logger(__name__)


REPLAY_WINDOW_SECONDS = 600  # 10 minutes


@router.post("/razorpay", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    db: DbSession,
    x_razorpay_signature: str | None = Header(default=None),
    x_razorpay_event_id: str | None = Header(default=None),
) -> dict:
    body = await request.body()

    # 1. Signature MUST be verified before parsing JSON.
    if not x_razorpay_signature or not razorpay_client.verify_webhook_signature(
        body=body, signature=x_razorpay_signature
    ):
        raise HTTPException(
            401,
            detail={"error": {"code": "invalid_signature", "message": "Webhook signature failed verification."}},
        )

    # 2. Parse payload (after signature so we don't risk parser-DOS on unsigned input)
    try:
        event = json.loads(body)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            400, detail={"error": {"code": "invalid_payload", "message": "Body is not valid JSON."}}
        ) from e

    event_name = event.get("event")

    # 3. Strictness: created_at and X-Razorpay-Event-Id are REQUIRED.
    # Razorpay always sends both; an event without them cannot be checked for
    # replay or deduplicated, so processing it would silently bypass those
    # protections. Fail closed with 400 instead.
    if not x_razorpay_event_id:
        raise HTTPException(
            400,
            detail={
                "error": {
                    "code": "missing_event_id",
                    "message": "X-Razorpay-Event-Id header is required.",
                }
            },
        )
    created_at_epoch = event.get("created_at")
    try:
        event_time = datetime.fromtimestamp(int(created_at_epoch), tz=timezone.utc)
    except (TypeError, ValueError) as e:
        raise HTTPException(
            400,
            detail={
                "error": {
                    "code": "missing_created_at",
                    "message": "Event is missing a valid created_at timestamp.",
                }
            },
        ) from e

    # 4. Replay-attack window — reject events older than REPLAY_WINDOW_SECONDS.
    if datetime.now(tz=timezone.utc) - event_time > timedelta(seconds=REPLAY_WINDOW_SECONDS):
        log.warning(
            "razorpay_webhook_too_old",
            razorpay_event=event_name,
            event_age_seconds=(datetime.now(tz=timezone.utc) - event_time).total_seconds(),
        )
        # Return 200 — Razorpay shouldn't keep retrying an event we'll never accept
        return {"received": True, "outcome": "stale_event_rejected"}

    # 5. Idempotency — if this event_id was already processed, short-circuit.
    existing = await db.scalar(
        select(WebhookEvent).where(
            WebhookEvent.provider == "razorpay",
            WebhookEvent.event_id == x_razorpay_event_id,
        )
    )
    if existing is not None:
        log.info(
            "razorpay_webhook_duplicate",
            razorpay_event=event_name,
            event_id=x_razorpay_event_id,
            original_outcome=existing.outcome,
        )
        return {"received": True, "outcome": "duplicate", "previous_outcome": existing.outcome}

    # 6. Apply the event
    outcome = await billing.apply_razorpay_event(db, event)

    # 7. Record event_id (best-effort — if it races with another concurrent
    # delivery we'll hit a UNIQUE violation; that's fine because both ended
    # up applying the same idempotent business logic).
    try:
        db.add(
            WebhookEvent(
                provider="razorpay",
                event_id=x_razorpay_event_id,
                event_name=event_name,
                outcome=outcome,
            )
        )
        await db.flush()
    except IntegrityError:
        await db.rollback()

    log.info("razorpay_webhook", razorpay_event=event_name, outcome=outcome)
    return {"received": True, "outcome": outcome}
