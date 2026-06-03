"""Profile (Netflix "Who's watching?") schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProfileRead(BaseModel):
    id: int
    name: str
    avatar: str
    kind: Literal["adult", "kid"]
    is_primary: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    avatar: str = Field(min_length=1, max_length=8, default="👤")
    kind: Literal["adult", "kid"] = "adult"


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=32)
    avatar: str | None = Field(default=None, min_length=1, max_length=8)
    kind: Literal["adult", "kid"] | None = None


class ProfileList(BaseModel):
    items: list[ProfileRead]
    max_profiles: int  # Soft limit so the frontend can disable "+ Add" at the cap
