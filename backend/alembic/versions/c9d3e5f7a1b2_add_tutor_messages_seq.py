"""add tutor_messages.seq insertion-order column

Revision ID: c9d3e5f7a1b2
Revises: b8c2d4e6f0a1
Create Date: 2026-09-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d3e5f7a1b2'
down_revision: Union[str, Sequence[str], None] = 'b8c2d4e6f0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE SEQUENCE IF NOT EXISTS tutor_messages_seq")
    op.add_column('tutor_messages', sa.Column('seq', sa.Integer(), nullable=True))
    op.execute("UPDATE tutor_messages SET seq = nextval('tutor_messages_seq')")
    op.alter_column('tutor_messages', 'seq', existing_type=sa.Integer(),
                    nullable=False, server_default=sa.text("nextval('tutor_messages_seq')"))
    op.create_index(op.f('ix_tutor_messages_seq'), 'tutor_messages', ['seq'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_tutor_messages_seq'), table_name='tutor_messages')
    op.alter_column('tutor_messages', 'seq', existing_type=sa.Integer(), nullable=True,
                    server_default=None)
    op.drop_column('tutor_messages', 'seq')
    op.execute("DROP SEQUENCE IF EXISTS tutor_messages_seq")
