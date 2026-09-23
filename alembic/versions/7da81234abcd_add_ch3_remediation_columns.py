"""Add Chapter 3 remediation columns

Revision ID: 7da81234abcd
Revises: 89b7da012555
Create Date: 2026-09-22 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7da81234abcd'
down_revision: Union[str, None] = '89b7da012555'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # research_runs
    op.add_column('research_runs', sa.Column('current_attempt_id', sa.UUID(), nullable=True))

    # research_evidence
    op.add_column('research_evidence', sa.Column('source_resolution_status', sa.String(), server_default='unresolved_external', nullable=False))
    op.add_column('research_evidence', sa.Column('provider', sa.String(), nullable=True))
    op.add_column('research_evidence', sa.Column('provider_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # research_reports
    op.add_column('research_reports', sa.Column('provenance_version', sa.String(), server_default='v1', nullable=False))
    op.add_column('research_reports', sa.Column('status', sa.String(), server_default='draft', nullable=False))

    # research_events
    op.add_column('research_events', sa.Column('sequence', sa.Integer(), server_default='1', nullable=False))


def downgrade() -> None:
    op.drop_column('research_events', 'sequence')
    op.drop_column('research_reports', 'status')
    op.drop_column('research_reports', 'provenance_version')
    op.drop_column('research_evidence', 'provider_reference')
    op.drop_column('research_evidence', 'provider')
    op.drop_column('research_evidence', 'source_resolution_status')
    op.drop_column('research_runs', 'current_attempt_id')
