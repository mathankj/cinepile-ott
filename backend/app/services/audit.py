"""
Audit log helper. Called from admin services on every write.

We accept already-serialised dicts (so callers control what shows up in the
audit log — never raw model instances which might leak fields). The route
layer can also pass the X-Request-ID for correlation.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.user import User


async def record(
    db: AsyncSession,
    *,
    actor: User,
    action: str,
    entity_type: str,
    entity_id: int,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor.id,
        actor_role=actor.role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        request_id=request_id,
    )
    db.add(entry)
    await db.flush()
    return entry


async def list_entries(
    db: AsyncSession,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    actor_user_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[AuditLog], int]:
    page = max(1, page)
    page_size = max(1, min(200, page_size))

    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
        count_stmt = count_stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
        count_stmt = count_stmt.where(AuditLog.entity_id == entity_id)
    if actor_user_id is not None:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
        count_stmt = count_stmt.where(AuditLog.actor_user_id == actor_user_id)

    stmt = stmt.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list((await db.scalars(stmt)).all())
    total = (await db.scalar(count_stmt)) or 0
    return items, int(total)
