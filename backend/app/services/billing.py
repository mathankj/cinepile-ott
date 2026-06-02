"""
Billing service.

Two providers behind one interface:
- `mock` (V1 default; what tests use): always-succeed in-process subscription
- `razorpay` (production-real): creates a Razorpay Plan + Subscription,
  returns a `checkout_url` the client redirects to.

The route layer never imports either provider directly — it calls
`subscribe()` / `cancel()` / `has_active_subscription()` from this module.

Settings.effective_billing_provider chooses between them at runtime.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.subscription import Plan, Subscription
from app.models.user import User

log = get_logger(__name__)


class PlanNotFound(Exception):
    code = "plan_not_found"
    message = "No active plan with that code."


class AlreadySubscribed(Exception):
    code = "already_subscribed"
    message = "User already has an active subscription."


class NoActiveSubscription(Exception):
    code = "no_active_subscription"
    message = "User has no active subscription."


class ProviderError(Exception):
    code = "provider_error"
    message = "Payment provider error."


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _period_end(start: datetime, interval: str) -> datetime:
    if interval == "year":
        return start + timedelta(days=365)
    return start + timedelta(days=30)


# ---- Read helpers (provider-agnostic) ------------------------------------------


async def list_plans(db: AsyncSession) -> list[Plan]:
    stmt = select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price_cents)
    return list((await db.scalars(stmt)).all())


async def get_my_subscription(db: AsyncSession, user: User) -> Subscription | None:
    stmt = (
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.status == "active")
        .order_by(Subscription.id.desc())
    )
    return await db.scalar(stmt)


async def has_active_subscription(db: AsyncSession, user: User) -> bool:
    sub = await get_my_subscription(db, user)
    return sub is not None


# ---- Subscribe / cancel — provider-routed ------------------------------------


async def subscribe(db: AsyncSession, user: User, *, plan_code: str) -> Subscription:
    """Create a subscription using the configured provider."""
    plan = await db.scalar(select(Plan).where(Plan.code == plan_code, Plan.is_active.is_(True)))
    if plan is None:
        raise PlanNotFound

    existing = await get_my_subscription(db, user)
    if existing is not None:
        raise AlreadySubscribed

    provider = get_settings().effective_billing_provider
    if provider == "razorpay":
        return await _subscribe_razorpay(db, user, plan)
    return await _subscribe_mock(db, user, plan)


async def cancel(db: AsyncSession, user: User) -> Subscription:
    sub = await get_my_subscription(db, user)
    if sub is None:
        raise NoActiveSubscription

    if sub.provider == "razorpay" and sub.provider_subscription_id:
        # Best-effort cancel at Razorpay; we still flip our local row regardless
        try:
            from app.services import razorpay_client

            await razorpay_client.cancel_subscription(
                sub.provider_subscription_id, cancel_at_cycle_end=True
            )
        except Exception as e:  # noqa: BLE001
            log.warning("razorpay_cancel_failed", error=str(e), sub_id=sub.id)

    sub.cancel_at_period_end = True
    await db.flush()
    return sub


# ---- Mock provider ------------------------------------------------------------


async def _subscribe_mock(db: AsyncSession, user: User, plan: Plan) -> Subscription:
    now = _now()
    sub = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        status="active",
        current_period_start=now,
        current_period_end=_period_end(now, plan.billing_interval),
        cancel_at_period_end=False,
        provider="mock",
        provider_subscription_id=f"mock_{user.id}_{int(now.timestamp())}",
    )
    db.add(sub)
    await db.flush()
    return sub


# ---- Razorpay provider --------------------------------------------------------


async def _ensure_razorpay_plan(plan: Plan) -> str:
    """Returns Razorpay plan id; creates it if not yet cached on the row."""
    if plan.provider_plan_id:
        return plan.provider_plan_id

    from app.services import razorpay_client

    rp = await razorpay_client.create_plan(
        period="monthly" if plan.billing_interval == "month" else "yearly",
        interval=1,
        item_name=plan.name,
        amount_paise=plan.price_cents,  # Razorpay uses paise; our price_cents IS paise for INR
        currency=plan.currency,
    )
    plan.provider_plan_id = rp["id"]
    return rp["id"]


async def _subscribe_razorpay(db: AsyncSession, user: User, plan: Plan) -> Subscription:
    from app.services import razorpay_client

    try:
        rp_plan_id = await _ensure_razorpay_plan(plan)
        # 12 cycles = 1 year for monthly, 1 year for yearly (1 cycle of yearly).
        total_count = 12 if plan.billing_interval == "month" else 5
        rp_sub = await razorpay_client.create_subscription(
            plan_id=rp_plan_id,
            total_count=total_count,
            customer_notify=True,
            notes={"user_id": str(user.id), "user_email": user.email},
        )
    except razorpay_client.RazorpayNotConfigured as e:
        raise ProviderError from e
    except Exception as e:  # noqa: BLE001
        log.error("razorpay_subscribe_failed", error=str(e))
        raise ProviderError from e

    now = _now()
    sub = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        # Razorpay starts as 'created'; flips to 'authenticated'/'active' after the
        # user completes checkout. We mirror this — local row stays inactive until
        # the webhook says otherwise. Browse/play check has_active_subscription
        # which only matches status='active', so user must complete checkout.
        status="pending",
        current_period_start=now,
        current_period_end=_period_end(now, plan.billing_interval),
        provider="razorpay",
        provider_subscription_id=rp_sub["id"],
        checkout_url=rp_sub.get("short_url"),
    )
    db.add(sub)
    await db.flush()
    return sub


# ---- Webhook event handlers ---------------------------------------------------


async def apply_razorpay_event(db: AsyncSession, event: dict) -> str:
    """
    Idempotent — Razorpay can retry. Returns a short status string for logging.

    Events we act on:
      subscription.activated      → flip to active
      subscription.authenticated  → flip to active (older event name)
      subscription.charged        → bump current_period_end forward
      subscription.cancelled      → status=cancelled
      subscription.completed      → status=expired (all cycles done)
      subscription.halted/paused  → status=past_due
    """
    name = event.get("event")
    payload = event.get("payload", {})
    sub_data = payload.get("subscription", {}).get("entity") or payload.get("subscription", {})
    if not isinstance(sub_data, dict):
        return "no_subscription_in_payload"
    rp_sub_id = sub_data.get("id")
    if not rp_sub_id:
        return "no_subscription_id"

    sub = await db.scalar(
        select(Subscription).where(Subscription.provider_subscription_id == rp_sub_id)
    )
    if sub is None:
        return f"unknown_subscription_{rp_sub_id}"

    status_map = {
        "subscription.activated": "active",
        "subscription.authenticated": "active",
        "subscription.charged": "active",
        "subscription.completed": "expired",
        "subscription.cancelled": "cancelled",
        "subscription.halted": "past_due",
        "subscription.paused": "past_due",
        "subscription.pending": "past_due",
    }
    new_status = status_map.get(name or "")
    if new_status is None:
        return f"unhandled_event_{name}"

    sub.status = new_status
    if new_status == "active":
        sub.checkout_url = None  # checkout completed
        # Razorpay's payload includes current_end (epoch seconds) on charged events
        current_end = sub_data.get("current_end")
        if current_end:
            sub.current_period_end = datetime.fromtimestamp(int(current_end), tz=timezone.utc)
    elif new_status in {"cancelled", "expired"}:
        sub.cancel_at_period_end = False

    await db.flush()
    return f"applied_{name}"
