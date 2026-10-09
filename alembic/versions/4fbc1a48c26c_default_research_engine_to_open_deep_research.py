"""Default workspaces.research_engine to open_deep_research and migrate legacy workspaces

Revision ID: 4fbc1a48c26c
Revises: f7a8b9c0d1e2
Create Date: 2026-10-07 10:00:00.000000

Chapter 5, Phase 1: the legacy research engine is removed, so ODR becomes the only
supported engine. Only workspaces.research_engine = 'legacy' is rewritten. Historical
research_runs.engine values are intentionally left untouched.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '4fbc1a48c26c'
down_revision: Union[str, None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE workspaces SET research_engine = 'open_deep_research' WHERE research_engine = 'legacy'")
    op.alter_column('workspaces', 'research_engine', server_default='open_deep_research')


def downgrade() -> None:
    # Restores only the server default. The data update in upgrade() is NOT reversible:
    # we cannot know which workspaces were 'legacy' before the migration.
    op.alter_column('workspaces', 'research_engine', server_default='legacy')
