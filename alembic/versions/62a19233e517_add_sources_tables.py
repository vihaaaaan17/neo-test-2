"""Add sources tables

Revision ID: 62a19233e517
Revises: f23c3a900272
Create Date: 2026-09-17 00:06:15.483524

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '62a19233e517'
down_revision: Union[str, None] = 'f23c3a900272'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sources',
        sa.Column('source_id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', sa.UUID(as_uuid=True), sa.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=False),
        sa.Column('owner_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_table(
        'source_snapshots',
        sa.Column('snapshot_id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_id', sa.UUID(as_uuid=True), sa.ForeignKey('sources.source_id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_uri', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('checksum_sha256', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )


def downgrade() -> None:
    op.drop_table('source_snapshots')
    op.drop_table('sources')
