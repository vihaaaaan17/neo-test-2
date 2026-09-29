"""Add scratchpad_entries table for durable research working state

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-09-28 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e6f7a8b9c0d1'
down_revision: Union[str, None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'scratchpad_entries',
        sa.Column('entry_id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('conversation_id', sa.UUID(), nullable=True),
        sa.Column('turn_id', sa.UUID(), nullable=True),
        sa.Column('run_id', sa.UUID(), nullable=True),
        sa.Column('entry_type', sa.String(length=32), nullable=False),
        sa.Column('lifecycle', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_pinned_to_workspace', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('pinned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('superseded_by_id', sa.UUID(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.conversation_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['research_runs.run_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['superseded_by_id'], ['scratchpad_entries.entry_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['turn_id'], ['conversation_turns.turn_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.workspace_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('entry_id')
    )
    op.create_index('ix_scratchpad_entries_workspace_id', 'scratchpad_entries', ['workspace_id'], unique=False)
    op.create_index('ix_scratchpad_entries_conversation_id', 'scratchpad_entries', ['conversation_id'], unique=False)
    op.create_index('ix_scratchpad_entries_turn_id', 'scratchpad_entries', ['turn_id'], unique=False)
    op.create_index('ix_scratchpad_entries_run_id', 'scratchpad_entries', ['run_id'], unique=False)
    op.create_index('ix_scratchpad_workspace_lifecycle', 'scratchpad_entries', ['workspace_id', 'lifecycle'], unique=False)
    op.create_index('ix_scratchpad_conversation_lifecycle', 'scratchpad_entries', ['conversation_id', 'lifecycle'], unique=False)
    op.create_index('ix_scratchpad_workspace_pinned', 'scratchpad_entries', ['workspace_id', 'is_pinned_to_workspace'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_scratchpad_workspace_pinned', table_name='scratchpad_entries')
    op.drop_index('ix_scratchpad_conversation_lifecycle', table_name='scratchpad_entries')
    op.drop_index('ix_scratchpad_workspace_lifecycle', table_name='scratchpad_entries')
    op.drop_index('ix_scratchpad_entries_run_id', table_name='scratchpad_entries')
    op.drop_index('ix_scratchpad_entries_turn_id', table_name='scratchpad_entries')
    op.drop_index('ix_scratchpad_entries_conversation_id', table_name='scratchpad_entries')
    op.drop_index('ix_scratchpad_entries_workspace_id', table_name='scratchpad_entries')
    op.drop_table('scratchpad_entries')
