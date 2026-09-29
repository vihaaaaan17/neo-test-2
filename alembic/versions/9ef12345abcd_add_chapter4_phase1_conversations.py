"""Add Chapter 4 Phase 1 conversations, conversation_turns, chat_events, and research_run links

Revision ID: 9ef12345abcd
Revises: 7da81234abcd
Create Date: 2026-09-24 18:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9ef12345abcd'
down_revision: Union[str, None] = '7da81234abcd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create conversations table
    op.create_table(
        'conversations',
        sa.Column('conversation_id', sa.UUID(), primary_key=True),
        sa.Column('workspace_id', sa.UUID(), sa.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('last_turn_sequence', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_conversations_workspace_id', 'conversations', ['workspace_id'])
    op.create_index('ix_conversations_owner_id', 'conversations', ['owner_id'])
    op.create_index('ix_conversations_workspace_updated', 'conversations', ['workspace_id', sa.text('updated_at DESC')])
    op.create_index('ix_conversations_workspace_owner', 'conversations', ['workspace_id', 'owner_id'])

    # 2. Create conversation_turns table
    op.create_table(
        'conversation_turns',
        sa.Column('turn_id', sa.UUID(), primary_key=True),
        sa.Column('conversation_id', sa.UUID(), sa.ForeignKey('conversations.conversation_id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.UUID(), sa.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('sequence', sa.BigInteger(), nullable=False),
        sa.Column('mode', sa.String(length=32), nullable=False),
        sa.Column('user_message', sa.Text(), nullable=False),
        sa.Column('assistant_message', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('research_run_id', sa.UUID(), sa.ForeignKey('research_runs.run_id', ondelete='SET NULL'), nullable=True),
        sa.Column('client_request_id', sa.String(length=255), nullable=True),
        sa.Column('source_scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ground_evidence_refs', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('context_version', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('error_code', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('conversation_id', 'sequence', name='uq_conversation_turn_sequence'),
        sa.UniqueConstraint('conversation_id', 'client_request_id', name='uq_conversation_turn_client_request_id')
    )
    op.create_index('ix_conversation_turns_conversation_id', 'conversation_turns', ['conversation_id'])
    op.create_index('ix_conversation_turns_workspace_id', 'conversation_turns', ['workspace_id'])
    op.create_index('ix_conversation_turns_owner_id', 'conversation_turns', ['owner_id'])
    op.create_index('ix_conversation_turns_research_run_id', 'conversation_turns', ['research_run_id'])
    op.create_index('ix_turns_workspace_conversation', 'conversation_turns', ['workspace_id', 'conversation_id'])

    # 3. Create chat_events table
    op.create_table(
        'chat_events',
        sa.Column('event_id', sa.UUID(), primary_key=True),
        sa.Column('turn_id', sa.UUID(), sa.ForeignKey('conversation_turns.turn_id', ondelete='CASCADE'), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('turn_id', 'sequence', name='uq_chat_event_sequence')
    )
    op.create_index('ix_chat_events_turn_id', 'chat_events', ['turn_id'])

    # 4. Add conversation_id and turn_id to research_runs
    op.add_column('research_runs', sa.Column('conversation_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_research_runs_conversation_id',
        'research_runs', 'conversations',
        ['conversation_id'], ['conversation_id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_research_runs_conversation_id', 'research_runs', ['conversation_id'])

    op.add_column('research_runs', sa.Column('turn_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_research_runs_turn_id',
        'research_runs', 'conversation_turns',
        ['turn_id'], ['turn_id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_research_runs_turn_id', 'research_runs', ['turn_id'])


def downgrade() -> None:
    op.drop_index('ix_research_runs_turn_id', table_name='research_runs')
    op.drop_constraint('fk_research_runs_turn_id', 'research_runs', type_='foreignkey')
    op.drop_column('research_runs', 'turn_id')

    op.drop_index('ix_research_runs_conversation_id', table_name='research_runs')
    op.drop_constraint('fk_research_runs_conversation_id', 'research_runs', type_='foreignkey')
    op.drop_column('research_runs', 'conversation_id')

    op.drop_table('chat_events')
    op.drop_table('conversation_turns')
    op.drop_table('conversations')
