"""hot-path indexes on titles + watch_progress

docs/db-schema.md has documented these indexes since V1.5, but no migration
ever created them — every listing/trending/continue-watching query was doing
a sequential scan on Postgres. The model files declare the same indexes (so
the SQLite test DB, built from metadata, gets them); this migration is the
Postgres side.

Created defensively with if_not_exists so environments where someone already
added them by hand don't error.

Revision ID: 4b8e21c0a9d7
Revises: ebef5353faa5
Create Date: 2026-06-10 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b8e21c0a9d7'
down_revision: Union[str, Sequence[str], None] = 'ebef5353faa5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the hot-path indexes (no-op if they already exist)."""
    # Default catalog listings filter on status and order by published_at.
    op.create_index(
        'ix_titles_status_published_at',
        'titles',
        ['status', 'published_at'],
        if_not_exists=True,
    )
    # Movie/series tab filter: WHERE type = ? AND status = 'published'.
    op.create_index(
        'ix_titles_type_status',
        'titles',
        ['type', 'status'],
        if_not_exists=True,
    )
    # Trending / top-in-country / similar rails order by view_count DESC.
    op.create_index(
        'ix_titles_view_count_desc',
        'titles',
        [sa.text('view_count DESC')],
        if_not_exists=True,
    )
    # Continue-watching + history: this user's rows, most recent first.
    op.create_index(
        'ix_watch_progress_user_id_last_played_at',
        'watch_progress',
        ['user_id', sa.text('last_played_at DESC')],
        if_not_exists=True,
    )


def downgrade() -> None:
    """Drop the hot-path indexes."""
    op.drop_index('ix_watch_progress_user_id_last_played_at', table_name='watch_progress', if_exists=True)
    op.drop_index('ix_titles_view_count_desc', table_name='titles', if_exists=True)
    op.drop_index('ix_titles_type_status', table_name='titles', if_exists=True)
    op.drop_index('ix_titles_status_published_at', table_name='titles', if_exists=True)
