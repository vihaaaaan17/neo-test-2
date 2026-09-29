"""Bind open_notebook_conversation_bindings foreign key to canonical conversations

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-09-25 01:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add foreign key pointing to canonical conversations table
    op.create_foreign_key(
        'open_notebook_conversation_bindings_conversation_id_fkey',
        'open_notebook_conversation_bindings',
        'conversations',
        ['conversation_id'],
        ['conversation_id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    op.drop_constraint(
        'open_notebook_conversation_bindings_conversation_id_fkey',
        'open_notebook_conversation_bindings',
        type_='foreignkey'
    )
