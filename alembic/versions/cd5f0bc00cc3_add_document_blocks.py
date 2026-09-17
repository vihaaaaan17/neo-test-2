"""Add document_blocks

Revision ID: cd5f0bc00cc3
Revises: 62a19233e517
Create Date: 2026-09-17 00:27:16.446969

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd5f0bc00cc3'
down_revision: Union[str, None] = '62a19233e517'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'document_blocks',
        sa.Column('block_id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_id', sa.UUID(as_uuid=True), sa.ForeignKey('sources.source_id', ondelete='CASCADE'), nullable=False),
        sa.Column('snapshot_id', sa.UUID(as_uuid=True), sa.ForeignKey('source_snapshots.snapshot_id', ondelete='CASCADE'), nullable=False),
        sa.Column('block_type', sa.String(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('text_or_ref', sa.String(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('metadata_', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    op.drop_table('document_blocks')
