"""Three-state reaction (thumbs_down | thumbs_up | double_thumbs_up) per user per title."""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reaction import Reaction
from app.models.title import Title
from app.models.user import User
from app.services.browse import invalidate_home_cache

VALID_KINDS = {"thumbs_down", "thumbs_up", "double_thumbs_up"}


class InvalidReactionKind(Exception):
    code = "invalid_reaction"
    message = "Reaction must be thumbs_down, thumbs_up, or double_thumbs_up."


class TitleNotFound(Exception):
    code = "title_not_found"
    message = "Title not found."


async def set_reaction(db: AsyncSession, user: User, *, title_id: int, kind: str) -> Reaction:
    if kind not in VALID_KINDS:
        raise InvalidReactionKind
    title = await db.get(Title, title_id)
    if title is None or title.deleted_at is not None or title.status != "published":
        raise TitleNotFound

    row = await db.scalar(
        select(Reaction).where(Reaction.user_id == user.id, Reaction.title_id == title_id)
    )
    if row is None:
        row = Reaction(user_id=user.id, title_id=title_id, kind=kind)
        db.add(row)
    else:
        row.kind = kind
    await db.flush()
    invalidate_home_cache(user.id)  # Recommendations row depends on reactions
    return row


async def clear_reaction(db: AsyncSession, user: User, *, title_id: int) -> int:
    res = await db.execute(
        delete(Reaction).where(Reaction.user_id == user.id, Reaction.title_id == title_id)
    )
    invalidate_home_cache(user.id)
    return res.rowcount or 0


async def list_reactions(db: AsyncSession, user: User) -> list[tuple[Reaction, Title]]:
    stmt = (
        select(Reaction, Title)
        .join(Title, Title.id == Reaction.title_id)
        .where(
            Reaction.user_id == user.id,
            Title.deleted_at.is_(None),
            Title.status == "published",
        )
        .order_by(Reaction.updated_at.desc())
    )
    return [(r, t) for r, t in (await db.execute(stmt)).all()]
