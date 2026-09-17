"""Add episodic_memories

Revision ID: e3c4578b22e1
Revises: d91ab2090cc1
Create Date: 2026-09-17 01:13:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e3c4578b22e1'
down_revision: Union[str, None] = 'd91ab2090cc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'episodic_memories',
        sa.Column('episode_id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', sa.UUID(as_uuid=True), sa.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=False),
        sa.Column('owner_id', sa.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('importance', sa.Float(), nullable=True),
        sa.Column('run_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('task_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('outcome', sa.String(), nullable=True),
        sa.Column('entities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('embedding_ref', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True)
    )

def downgrade() -> None:
    op.drop_table('episodic_memories')
