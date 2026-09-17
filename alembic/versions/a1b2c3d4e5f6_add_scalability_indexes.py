"""Add composite indexes for 1000-user scalability

Revision ID: a1b2c3d4e5f6
Revises: e3c4578b22e1
Create Date: 2026-09-17 12:10:00.000000

These indexes eliminate full table scans on every read-hot query path.
Without them, tables exceeding ~1000 rows will degrade with linear scans
on every authenticated request. Each index is a composite covering the
tenant-scoping column (owner_id or workspace_id) plus the most common
filter/ordering columns.
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e3c4578b22e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # workspaces — filtered by owner on every auth request
    op.create_index('ix_workspaces_owner_id', 'workspaces', ['owner_id'])
    op.create_index('ix_workspaces_owner_status', 'workspaces', ['owner_id', 'status'])

    # document_blocks — retrieved by source in chunk-read order
    op.create_index('ix_document_blocks_source_sequence', 'document_blocks', ['source_id', 'sequence'])

    # sources — tenant-scoped lookup
    op.create_index('ix_sources_workspace_id', 'sources', ['workspace_id'])

    # source_snapshots — joined from source on every grounded query
    op.create_index('ix_source_snapshots_source_id', 'source_snapshots', ['source_id'])

    # knowledge_memories — workspace-scoped memory reads
    op.create_index('ix_knowledge_memories_workspace_id', 'knowledge_memories', ['workspace_id'])
    op.create_index('ix_knowledge_memories_workspace_source_mode', 'knowledge_memories', ['workspace_id', 'source_mode'])

    # episodic_memories — workspace-scoped episode reads
    op.create_index('ix_episodic_memories_workspace_id', 'episodic_memories', ['workspace_id'])
    op.create_index('ix_episodic_memories_workspace_created', 'episodic_memories', ['workspace_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_episodic_memories_workspace_created', table_name='episodic_memories')
    op.drop_index('ix_episodic_memories_workspace_id', table_name='episodic_memories')
    op.drop_index('ix_knowledge_memories_workspace_source_mode', table_name='knowledge_memories')
    op.drop_index('ix_knowledge_memories_workspace_id', table_name='knowledge_memories')
    op.drop_index('ix_source_snapshots_source_id', table_name='source_snapshots')
    op.drop_index('ix_sources_workspace_id', table_name='sources')
    op.drop_index('ix_document_blocks_source_sequence', table_name='document_blocks')
    op.drop_index('ix_workspaces_owner_status', table_name='workspaces')
    op.drop_index('ix_workspaces_owner_id', table_name='workspaces')
