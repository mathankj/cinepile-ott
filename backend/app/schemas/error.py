"""
Common API error envelope. Every 4xx / 5xx response uses this shape so the
frontend can render one consistent error component.

See docs/api/v1.md "Error envelope".
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    details: list[dict[str, Any]] | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody
