"""Engine attempt audit fields: routing mode, preferred engine, usage quality, timings

Revision ID: 7a3e9c5d1f68
Revises: 6d2f8b1c4e57
Create Date: 2026-10-10 10:00:00.000000

Additive and nullable: existing attempt rows are kept unchanged (their new fields are NULL).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '7a3e9c5d1f68'
down_revision: Union[str, None] = '6d2f8b1c4e57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('research_engine_attempts', sa.Column('routing_mode', sa.String(), nullable=True))
    op.add_column('research_engine_attempts', sa.Column('preferred_engine', sa.String(), nullable=True))
    op.add_column('research_engine_attempts', sa.Column('usage_quality', postgresql.JSONB(), nullable=True))
    op.add_column('research_engine_attempts', sa.Column('timings', postgresql.JSONB(), nullable=True))
    # Backfill the routing mode of existing attempts from their run (keeps history consistent).
    op.execute(
        "UPDATE research_engine_attempts a SET routing_mode = r.routing_mode "
        "FROM research_runs r WHERE r.run_id = a.run_id AND a.routing_mode IS NULL"
    )


def downgrade() -> None:
    for col in ('timings', 'usage_quality', 'preferred_engine', 'routing_mode'):
        op.drop_column('research_engine_attempts', col)
