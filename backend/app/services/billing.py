"""
Billing service — V1 uses a MOCK provider that always succeeds.

V1.1 will swap the implementation behind the same interface to call Razorpay or
Stripe. Routes never import the provider directly; they call these functions.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Plan, Subscription
from app.models.user import User


class PlanNotFound(Exception):
    code = "plan_not_found"
    message = "No active plan with that code."


class AlreadySubscribed(Exception):
    code = "already_subscribed"
    message = "User already has an active subscription."


class NoActiveSubscription(Exception):
    code = "no_active_subscription"
    message = "User has no active subscription."


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _period_end(start: datetime, interval: str) -> datetime:
    if interval == "year":
        return start + timedelta(days=365)
    return start + timedelta(days=30)


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


async def subscribe(db: AsyncSession, user: User, *, plan_code: str) -> Subscription:
    plan = await db.scalar(select(Plan).where(Plan.code == plan_code, Plan.is_active.is_(True)))
    if plan is None:
        raise PlanNotFound

    existing = await get_my_subscription(db, user)
    if existing is not None:
        raise AlreadySubscribed

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


async def cancel(db: AsyncSession, user: User) -> Subscription:
    sub = await get_my_subscription(db, user)
    if sub is None:
        raise NoActiveSubscription
    sub.cancel_at_period_end = True
    await db.flush()
    return sub


async def has_active_subscription(db: AsyncSession, user: User) -> bool:
    sub = await get_my_subscription(db, user)
    return sub is not None
