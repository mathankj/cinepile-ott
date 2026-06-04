"""Pydantic schemas for user-facing user data — never expose password_hash."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserSignup(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    """Output schema for user data — uses `str` for email, not EmailStr.

    Why: Pydantic's EmailStr rejects RFC-6761 reserved TLDs (.local, .test,
    .example, .localhost). On INPUT (signup) we want that validation. On
    OUTPUT we just want to return whatever is in the DB without crashing
    the whole list endpoint when one legacy row has a `.local` email.
    Found in QA: `admin@anjaneya.local` from an old test seed was 500'ing
    GET /v1/admin/users for every admin viewer.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime
