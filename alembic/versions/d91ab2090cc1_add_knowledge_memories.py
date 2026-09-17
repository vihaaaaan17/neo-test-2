"""Add knowledge_memories

Revision ID: d91ab2090cc1
Revises: cd5f0bc00cc3
Create Date: 2026-09-17 00:43:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd91ab2090cc1'
down_revision: Union[str, None] = 'cd5f0bc00cc3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'knowledge_memories',
        sa.Column('knowledge_id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', sa.UUID(as_uuid=True), sa.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=False),
        sa.Column('owner_id', sa.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('knowledge_type', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('provenance', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('entities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('domain', sa.String(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_table('knowledge_memories')
