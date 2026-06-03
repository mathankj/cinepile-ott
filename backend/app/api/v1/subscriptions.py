"""Plans + subscriptions routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.subscription import (
    PlanRead,
    SubscriptionCancelResponse,
    SubscriptionCreate,
    SubscriptionRead,
)
from app.services import billing

router = APIRouter()


@router.get("/plans", response_model=list[PlanRead], tags=["plans"])
async def list_plans(db: DbSession) -> list[PlanRead]:
    plans = await billing.list_plans(db)
    return [PlanRead.model_validate(p) for p in plans]


@router.get("/subscriptions/me", response_model=SubscriptionRead | None)
async def get_my_subscription(db: DbSession, user: CurrentUser) -> SubscriptionRead | None:
    """
    Returns the user's most-recent subscription regardless of status — so the
    frontend can show 'pending checkout', 'expired', 'cancelled', 'past_due'
    banners. Playback gating uses a stricter check (active + still in period).
    """
    sub = await billing.get_my_subscription_any_status(db, user)
    return SubscriptionRead.model_validate(sub) if sub else None


@router.post("/subscriptions", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
async def subscribe(
    payload: SubscriptionCreate, db: DbSession, user: CurrentUser
) -> SubscriptionRead:
    try:
        sub = await billing.subscribe(db, user, plan_code=payload.plan_code)
    except billing.PlanNotFound as e:
        raise HTTPException(404, detail={"error": {"code": e.code, "message": e.message}}) from e
    except billing.AlreadySubscribed as e:
        raise HTTPException(409, detail={"error": {"code": e.code, "message": e.message}}) from e
    except billing.ProviderError as e:
        raise HTTPException(502, detail={"error": {"code": e.code, "message": e.message}}) from e
    return SubscriptionRead.model_validate(sub)


@router.post("/subscriptions/cancel", response_model=SubscriptionCancelResponse)
async def cancel_subscription(db: DbSession, user: CurrentUser) -> SubscriptionCancelResponse:
    try:
        sub = await billing.cancel(db, user)
    except billing.NoActiveSubscription as e:
        raise HTTPException(404, detail={"error": {"code": e.code, "message": e.message}}) from e
    return SubscriptionCancelResponse(
        subscription=SubscriptionRead.model_validate(sub),
        message="Subscription will end at the end of the current billing period.",
    )
