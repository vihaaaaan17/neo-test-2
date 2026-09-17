"""Add processing_status to sources table

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-09-17 12:18:00.000000

Sources now track their background parsing job lifecycle:
  pending    -> source created, job not yet picked up
  processing -> worker has started parsing/chunking
  completed  -> parsing and chunking finished successfully
  failed     -> parsing or chunking raised an unrecoverable error

The column defaults to 'pending' so all historical rows are correctly labelled.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a1'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'sources',
        sa.Column('processing_status', sa.String(), nullable=False, server_default='pending')
    )
    # Index for efficient status polling (e.g. "show me all failed jobs in workspace")
    op.create_index(
        'ix_sources_workspace_processing_status',
        'sources',
        ['workspace_id', 'processing_status']
    )


def downgrade() -> None:
    op.drop_index('ix_sources_workspace_processing_status', table_name='sources')
    op.drop_column('sources', 'processing_status')
