"""JWT response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserRead


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime


class AuthSuccess(BaseModel):
    """What signup and login both return."""

    tokens: TokenPair
    user: UserRead


class RefreshRequest(BaseModel):
    refresh_token: str
