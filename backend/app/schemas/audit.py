"""Audit log read schema."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_user_id: int | None
    actor_role: str
    action: str
    entity_type: str
    entity_id: int
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    request_id: str | None
    created_at: datetime


class AuditListResponse(BaseModel):
    items: list[AuditEntry]
    page: int
    page_size: int
    total: int


class UserRoleChange(BaseModel):
    role: str
