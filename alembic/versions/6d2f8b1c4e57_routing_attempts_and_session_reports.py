"""Engine routing attempts and study-session reports

Revision ID: 6d2f8b1c4e57
Revises: 5c1e7a9d2b30
Create Date: 2026-10-09 10:00:00.000000

Chapter 6:
- research_runs.routing_mode ('auto' | 'explicit'); engine becomes nullable (auto runs record the answering engine).
- research_engine_attempts: one row per sequential engine attempt.
- research_reports / research_artifacts can be anchored to a conversation (study-session paper and its candidate)
  instead of a run. Existing rows are run-scoped and unchanged.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '6d2f8b1c4e57'
down_revision: Union[str, None] = '5c1e7a9d2b30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('research_runs', sa.Column('routing_mode', sa.String(), server_default='explicit', nullable=False))
    op.create_check_constraint('ck_research_runs_routing_mode', 'research_runs', "routing_mode IN ('auto', 'explicit')")
    op.alter_column('research_runs', 'engine', existing_type=sa.String(), nullable=True)
    op.create_check_constraint('ck_research_runs_explicit_engine', 'research_runs',
                               "routing_mode = 'auto' OR engine IS NOT NULL")

    op.create_table(
        'research_engine_attempts',
        sa.Column('attempt_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('research_runs.run_id', ondelete='CASCADE'), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('engine', sa.String(), nullable=False),
        sa.Column('budget_profile', sa.String(), nullable=True),
        sa.Column('trigger', sa.String(), nullable=False),
        sa.Column('reason', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('assessment', postgresql.JSONB(), nullable=True),
        sa.Column('error', sa.String(), nullable=True),
        sa.Column('evidence_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost', sa.Float(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('run_id', 'sequence', name='uq_research_engine_attempt_sequence'),
    )
    op.create_index('ix_research_engine_attempts_run_id', 'research_engine_attempts', ['run_id'])

    for table in ('research_reports', 'research_artifacts'):
        op.alter_column(table, 'run_id', existing_type=postgresql.UUID(as_uuid=True), nullable=True)
        op.add_column(table, sa.Column('workspace_id', postgresql.UUID(as_uuid=True),
                                       sa.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=True))
        op.add_column(table, sa.Column('conversation_id', postgresql.UUID(as_uuid=True),
                                       sa.ForeignKey('conversations.conversation_id', ondelete='CASCADE'), nullable=True))
        op.create_index(f'ix_{table}_workspace_id', table, ['workspace_id'])
        op.create_index(f'ix_{table}_conversation_id', table, ['conversation_id'])

    op.add_column('research_reports', sa.Column('scope', sa.String(), server_default='run', nullable=False))
    op.create_check_constraint(
        'ck_research_reports_scope_anchor', 'research_reports',
        "(scope = 'run' AND run_id IS NOT NULL) OR "
        "(scope = 'study_session' AND workspace_id IS NOT NULL AND conversation_id IS NOT NULL)",
    )
    op.create_check_constraint(
        'ck_research_artifacts_anchor', 'research_artifacts',
        "run_id IS NOT NULL OR (workspace_id IS NOT NULL AND conversation_id IS NOT NULL)",
    )


def downgrade() -> None:
    # Session-scoped rows have no run and cannot satisfy the old NOT NULL run_id; they are removed.
    op.drop_constraint('ck_research_artifacts_anchor', 'research_artifacts', type_='check')
    op.drop_constraint('ck_research_reports_scope_anchor', 'research_reports', type_='check')
    op.execute("DELETE FROM research_reports WHERE run_id IS NULL")
    op.execute("DELETE FROM research_artifacts WHERE run_id IS NULL")
    op.drop_column('research_reports', 'scope')
    for table in ('research_reports', 'research_artifacts'):
        op.drop_index(f'ix_{table}_conversation_id', table_name=table)
        op.drop_index(f'ix_{table}_workspace_id', table_name=table)
        op.drop_column(table, 'conversation_id')
        op.drop_column(table, 'workspace_id')
        op.alter_column(table, 'run_id', existing_type=postgresql.UUID(as_uuid=True), nullable=False)

    op.drop_index('ix_research_engine_attempts_run_id', table_name='research_engine_attempts')
    op.drop_table('research_engine_attempts')
    op.drop_constraint('ck_research_runs_explicit_engine', 'research_runs', type_='check')
    op.execute("DELETE FROM research_runs WHERE engine IS NULL")
    op.alter_column('research_runs', 'engine', existing_type=sa.String(), nullable=False)
    op.drop_constraint('ck_research_runs_routing_mode', 'research_runs', type_='check')
    op.drop_column('research_runs', 'routing_mode')
