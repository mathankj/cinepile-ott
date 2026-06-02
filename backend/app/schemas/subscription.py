"""Subscription/plan schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    price_cents: int
    currency: str
    billing_interval: Literal["month", "year"]


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    plan_id: int
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    provider: str


class SubscriptionCreate(BaseModel):
    plan_code: str


class SubscriptionCancelResponse(BaseModel):
    subscription: SubscriptionRead
    message: str
