"""
Webhook event-id store — used for idempotency.

Razorpay (and any other webhook source) can deliver the same event multiple
times. We persist `provider:event_id` on first receive; subsequent deliveries
short-circuit with a 200 instead of re-applying side effects.

Append-only. No deletes. We can prune entries older than 30 days in a future cron.
"""
from __future__ import annotations

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (UniqueConstraint("provider", "event_id", name="uq_webhook_events_provider_id"),)

    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # Razorpay uses `X-Razorpay-Event-Id` header (an opaque string).
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(128), nullable=True)
