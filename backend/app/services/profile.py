"""Profile service — create/list/update/delete the per-user sub-accounts.

Invariants:
  - Every user has at least one profile (the primary, created at signup).
  - Max 4 profiles per user (Netflix's hard cap; we follow).
  - Primary profile can be renamed/avatar-changed but never deleted.
  - Profile names are unique within a single user account (the DB enforces
    this via uq_profile_user_name).

This module also owns the cross-cutting profile-scoping helpers:
  - profile_scope()         — the (user_id, profile_id) WHERE clause builder
  - KID_SAFE_RATINGS / is_kid_safe() — the kids-content policy
  - set/get_request_profile — request-scoped active profile (ContextVar)
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile

# Netflix's UI maxes at 5 profiles per Standard/Premium plan. We use 4 because
# it's the historical max and fits the Netflix-style 2×2 picker grid cleanly.
MAX_PROFILES_PER_USER = 4

# CBFC ratings in the catalog are U, U/A, A (plus 12+/16+/18+ per
# docs/db-schema.md). A "kid" profile may only see/play "U" — U/A means
# parental guidance, so it is NOT kid-safe. Titles with no rating at all are
# treated as NOT kid-safe: fail closed rather than show unrated content to kids.
KID_SAFE_RATINGS: frozenset[str] = frozenset({"U"})


def is_kid_safe(age_rating: str | None) -> bool:
    return age_rating in KID_SAFE_RATINGS


def profile_scope(profile_id_column: Any, profile: Profile | None):
    """WHERE clause scoping a per-user table to the active profile.

    NULL profile_id rows are the legacy / no-profile scope — they are matched
    ONLY when no profile is active. With a profile active, only that profile's
    rows match. This keeps pre-profiles data reachable (send no header) while
    giving each profile a fully separate history/list/reactions.
    """
    if profile is None:
        return profile_id_column.is_(None)
    return profile_id_column == profile.id


# Request-scoped active profile. The auth dependencies in app/api/deps.py
# stash the verified profile here on every authenticated request. This exists
# for ONE consumer: the playback service. The /play routes (titles.py /
# episodes.py) belong to another finished branch, so we can't add an
# ActiveProfile parameter to their signatures — instead playback reads the
# stash. Services that CAN receive the profile via normal plumbing (history,
# watchlist, reactions, browse) take it as an explicit argument.
_request_profile: ContextVar[Profile | None] = ContextVar("active_profile", default=None)


def set_request_profile(profile: Profile | None) -> None:
    _request_profile.set(profile)


def get_request_profile() -> Profile | None:
    return _request_profile.get()


class ProfileLimitReached(Exception):
    code = "profile_limit_reached"
    message = f"Maximum {MAX_PROFILES_PER_USER} profiles per account."


class ProfileNotFound(Exception):
    code = "profile_not_found"
    message = "Profile not found."


class CannotDeletePrimary(Exception):
    code = "cannot_delete_primary"
    message = "The primary profile cannot be deleted. Edit it instead."


class DuplicateName(Exception):
    code = "duplicate_profile_name"
    message = "You already have a profile with that name."


async def list_profiles(db: AsyncSession, user_id: int) -> list[Profile]:
    rows = await db.scalars(
        select(Profile).where(Profile.user_id == user_id).order_by(Profile.is_primary.desc(), Profile.created_at.asc())
    )
    return list(rows.all())


async def get_profile(db: AsyncSession, user_id: int, profile_id: int) -> Profile:
    profile = await db.scalar(
        select(Profile).where(Profile.id == profile_id, Profile.user_id == user_id)
    )
    if profile is None:
        raise ProfileNotFound
    return profile


async def ensure_primary_profile(db: AsyncSession, user_id: int, default_name: str | None = None) -> Profile:
    """Idempotently make sure a user has at least one (primary) profile.

    Called at first /me/profiles list — guarantees existing users who signed
    up before profiles existed still see a working picker. No-op for users
    who already have profiles.
    """
    existing = await db.scalar(
        select(Profile).where(Profile.user_id == user_id, Profile.is_primary.is_(True))
    )
    if existing is not None:
        return existing
    name = (default_name or "Me").strip()[:32] or "Me"
    profile = Profile(
        user_id=user_id,
        name=name,
        avatar="default",
        kind="adult",
        is_primary=True,
    )
    db.add(profile)
    await db.flush()
    return profile


async def create_profile(
    db: AsyncSession, user_id: int, *, name: str, avatar: str, kind: str
) -> Profile:
    existing = list(await db.scalars(select(Profile).where(Profile.user_id == user_id)))
    if len(existing) >= MAX_PROFILES_PER_USER:
        raise ProfileLimitReached
    if any(p.name.casefold() == name.casefold() for p in existing):
        raise DuplicateName
    profile = Profile(
        user_id=user_id,
        name=name,
        avatar=avatar,
        kind=kind,
        is_primary=False,
    )
    db.add(profile)
    await db.flush()
    return profile


async def update_profile(
    db: AsyncSession,
    user_id: int,
    profile_id: int,
    *,
    name: str | None,
    avatar: str | None,
    kind: str | None,
) -> Profile:
    profile = await get_profile(db, user_id, profile_id)
    if name is not None:
        # Name uniqueness check (skip if name unchanged)
        if name.casefold() != profile.name.casefold():
            taken = await db.scalar(
                select(Profile).where(
                    Profile.user_id == user_id,
                    Profile.id != profile_id,
                    Profile.name == name,
                )
            )
            if taken is not None:
                raise DuplicateName
        profile.name = name
    if avatar is not None:
        profile.avatar = avatar
    if kind is not None:
        profile.kind = kind
    await db.flush()
    return profile


async def delete_profile(db: AsyncSession, user_id: int, profile_id: int) -> None:
    profile = await get_profile(db, user_id, profile_id)
    if profile.is_primary:
        raise CannotDeletePrimary
    await db.delete(profile)
    await db.flush()
