"""Add phase 3 promotion lifecycle, verification, timeline epoch, and manifest fields

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-09-28 23:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, None] = 'e6f7a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. research_artifacts: promotion lifecycle & verification fields
    op.add_column('research_artifacts', sa.Column('promotion_status', sa.String(), server_default='pending_review', nullable=False))
    op.add_column('research_artifacts', sa.Column('reviewed_by', sa.UUID(), nullable=True))
    op.add_column('research_artifacts', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('research_artifacts', sa.Column('review_reason', sa.String(), nullable=True))
    op.add_column('research_artifacts', sa.Column('promoted_target_type', sa.String(), nullable=True))
    op.add_column('research_artifacts', sa.Column('promoted_target_id', sa.UUID(), nullable=True))
    op.add_column('research_artifacts', sa.Column('verification_status', sa.String(), nullable=True))
    op.add_column('research_artifacts', sa.Column('verification_reason', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('research_artifacts', sa.Column('verification_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_index('ix_research_artifacts_promotion_status', 'research_artifacts', ['promotion_status'])

    # 2. research_runs: base_commit_id
    op.add_column('research_runs', sa.Column('base_commit_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_research_runs_base_commit_id',
        'research_runs',
        'workspace_commits',
        ['base_commit_id'],
        ['commit_id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_research_runs_base_commit_id', 'research_runs', ['base_commit_id'])

    # 3. workspaces: timeline_epoch
    op.add_column('workspaces', sa.Column('timeline_epoch', sa.Integer(), server_default='1', nullable=False))

    # 4. workspace_commits: manifest JSONB
    op.add_column('workspace_commits', sa.Column('manifest', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False))


def downgrade() -> None:
    # 4. workspace_commits
    op.drop_column('workspace_commits', 'manifest')

    # 3. workspaces
    op.drop_column('workspaces', 'timeline_epoch')

    # 2. research_runs
    op.drop_index('ix_research_runs_base_commit_id', table_name='research_runs')
    op.drop_constraint('fk_research_runs_base_commit_id', 'research_runs', type_='foreignkey')
    op.drop_column('research_runs', 'base_commit_id')

    # 1. research_artifacts
    op.drop_index('ix_research_artifacts_promotion_status', table_name='research_artifacts')
    op.drop_column('research_artifacts', 'verification_metadata')
    op.drop_column('research_artifacts', 'verification_reason')
    op.drop_column('research_artifacts', 'verification_status')
    op.drop_column('research_artifacts', 'promoted_target_id')
    op.drop_column('research_artifacts', 'promoted_target_type')
    op.drop_column('research_artifacts', 'review_reason')
    op.drop_column('research_artifacts', 'reviewed_at')
    op.drop_column('research_artifacts', 'reviewed_by')
    op.drop_column('research_artifacts', 'promotion_status')
