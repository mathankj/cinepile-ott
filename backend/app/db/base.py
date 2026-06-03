"""
SQLAlchemy declarative base + async engine factory.

We keep the engine creation lazy so tests can swap DATABASE_URL freely.
The session factory lives in db/session.py.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import MetaData, func
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import get_settings

# Naming convention so Alembic-generated constraint names are deterministic and short
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Common columns: id + created_at + updated_at."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[Any] | None = None


def get_engine() -> AsyncEngine:
    """
    Create the async engine.

    On Neon's pooler endpoint (`-pooler.` hostname), PgBouncer is in TRANSACTION
    pooling mode which does NOT support prepared statements. We disable asyncpg's
    statement cache when we detect the pooler hostname; otherwise we'd hit
    "prepared statement does not exist" errors at random.

    `statement_timeout` and `idle_in_transaction_session_timeout` are set as
    server-side parameters so a runaway query can't park a connection.
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        url = settings.database_url
        is_pooler = "-pooler" in url

        connect_args: dict = {}
        if "asyncpg" in url:
            connect_args["server_settings"] = {
                "statement_timeout": "10000",  # ms; kills any single query > 10s
                "idle_in_transaction_session_timeout": "30000",  # ms; releases stuck txns
            }
            if is_pooler:
                # PgBouncer transaction mode incompatible with prepared statements.
                connect_args["statement_cache_size"] = 0
                connect_args["prepared_statement_cache_size"] = 0

        engine_kwargs: dict = {
            "echo": False,
            "pool_pre_ping": True,
            "connect_args": connect_args,
        }
        # SQLite (used in tests) uses StaticPool which doesn't accept pool_size etc.
        if "sqlite" not in url:
            engine_kwargs["pool_size"] = 10
            engine_kwargs["max_overflow"] = 20
            engine_kwargs["pool_recycle"] = 300  # Neon idle suspend safety

        _engine = create_async_engine(url, **engine_kwargs)
    return _engine


def get_session_factory() -> async_sessionmaker[Any]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def dispose_engine() -> None:
    """Called from FastAPI shutdown hook."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
