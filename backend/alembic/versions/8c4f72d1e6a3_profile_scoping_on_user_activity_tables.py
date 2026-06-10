"""profile scoping on user-activity tables

Adds a nullable profile_id FK to watch_progress, watchlist_items, and
reactions, and widens each table's unique constraint to include it. This turns
the cosmetic profile picker into real per-profile scoping: every profile gets
its own history, list, and reactions.

Design notes:
  - profile_id is NULLABLE: NULL means "legacy / no-profile scope" — rows
    written before this feature, or by clients that don't send X-Profile-Id.
    They stay reachable (the API matches them when no profile is active).
  - ondelete SET NULL: deleting a profile folds its activity back into the
    account-level scope instead of erasing the user's data.
  - NULL-uniqueness: both Postgres (default NULLS DISTINCT) and SQLite treat
    NULLs as distinct in unique constraints, so NULL-profile rows are NOT
    deduped by the DB — the services' select-then-upsert guards that scope.
    The SQLite test schema is built from the model metadata, which declares
    the same constraints, so both schemas stay consistent.

Revision ID: 8c4f72d1e6a3
Revises: 4b8e21c0a9d7
Create Date: 2026-06-10 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c4f72d1e6a3'
down_revision: Union[str, Sequence[str], None] = '4b8e21c0a9d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, unique constraint name, new unique columns). Constraint names are
# kept identical to the originals so the model metadata and the live schema
# agree on naming.
_TABLES: list[tuple[str, str, list[str]]] = [
    ("watch_progress", "uq_watch_progress_unique", ["user_id", "profile_id", "title_id", "episode_id"]),
    ("watchlist_items", "uq_watchlist_user_title", ["user_id", "profile_id", "title_id"]),
    ("reactions", "uq_reactions_user_title", ["user_id", "profile_id", "title_id"]),
]


def upgrade() -> None:
    """Add profile_id (nullable, SET NULL) and widen the unique constraints."""
    for table, uq_name, uq_cols in _TABLES:
        op.add_column(table, sa.Column("profile_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_profile_id_profiles",
            table,
            "profiles",
            ["profile_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(f"ix_{table}_profile_id", table, ["profile_id"])
        # Existing rows all have profile_id NULL, so widening the constraint
        # can't collide — (user_id, ...) was already unique without profiles.
        op.drop_constraint(uq_name, table, type_="unique")
        op.create_unique_constraint(uq_name, table, uq_cols)


def downgrade() -> None:
    """Drop profile scoping again.

    NOTE: restoring the narrower unique constraints fails if two profiles of
    one user have rows for the same title — collapse profile_id first (e.g.
    keep the most recent row per (user_id, title_id, episode_id)) before
    downgrading a database that has per-profile data.
    """
    for table, uq_name, _ in _TABLES:
        op.drop_constraint(uq_name, table, type_="unique")
        op.drop_index(f"ix_{table}_profile_id", table_name=table)
        op.drop_constraint(f"fk_{table}_profile_id_profiles", table, type_="foreignkey")
        op.drop_column(table, "profile_id")

    op.create_unique_constraint(
        "uq_watch_progress_unique", "watch_progress", ["user_id", "title_id", "episode_id"]
    )
    op.create_unique_constraint(
        "uq_watchlist_user_title", "watchlist_items", ["user_id", "title_id"]
    )
    op.create_unique_constraint(
        "uq_reactions_user_title", "reactions", ["user_id", "title_id"]
    )
