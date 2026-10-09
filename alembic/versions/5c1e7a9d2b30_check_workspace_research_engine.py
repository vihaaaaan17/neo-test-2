"""Constrain workspaces.research_engine to the supported research engines

Revision ID: 5c1e7a9d2b30
Revises: 4fbc1a48c26c
Create Date: 2026-10-08 10:00:00.000000

Chapter 5, Phase 2: the supported engines are open_deep_research, storm and gpt_researcher.
Any other value (there should be none after the Phase 1 migration) is reset to the default first.
"""
from typing import Sequence, Union

from alembic import op


revision: str = '5c1e7a9d2b30'
down_revision: Union[str, None] = '4fbc1a48c26c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ENGINES = "('open_deep_research', 'storm', 'gpt_researcher')"


def upgrade() -> None:
    op.execute(f"UPDATE workspaces SET research_engine = 'open_deep_research' WHERE research_engine NOT IN {ENGINES}")
    op.create_check_constraint('ck_workspaces_research_engine', 'workspaces', f"research_engine IN {ENGINES}")


def downgrade() -> None:
    op.drop_constraint('ck_workspaces_research_engine', 'workspaces', type_='check')
