"""Relax open_notebook_conversation_bindings foreign key to support canonical conversations

Revision ID: c4d5e6f7a8b9
Revises: 9ef12345abcd
Create Date: 2026-09-24 19:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = '9ef12345abcd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the legacy foreign key pointing strictly to ground_conversations
    # This allows open_notebook_conversation_bindings to bind both canonical conversations and legacy conversations
    op.drop_constraint(
        'open_notebook_conversation_bindings_conversation_id_fkey',
        'open_notebook_conversation_bindings',
        type_='foreignkey'
    )


def downgrade() -> None:
    op.create_foreign_key(
        'open_notebook_conversation_bindings_conversation_id_fkey',
        'open_notebook_conversation_bindings',
        'ground_conversations',
        ['conversation_id'],
        ['conversation_id'],
        ondelete='CASCADE'
    )
