"""create tutor_conversations and tutor_messages tables

Revision ID: b8c2d4e6f0a1
Revises: 7e1b9c4a2d05
Create Date: 2026-09-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b8c2d4e6f0a1'
down_revision: Union[str, Sequence[str], None] = '7e1b9c4a2d05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('tutor_conversations',
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tutor_conversations_project_id'), 'tutor_conversations', ['project_id'], unique=False)
    op.create_index(op.f('ix_tutor_conversations_user_id'), 'tutor_conversations', ['user_id'], unique=False)
    op.create_table('tutor_messages',
    sa.Column('conversation_id', sa.UUID(), nullable=False),
    sa.Column('role', sa.String(length=16), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('supported', sa.Boolean(), nullable=True),
    sa.Column('citations', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('follow_ups', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("role IN ('user', 'assistant')", name='ck_tutor_messages_role'),
    sa.ForeignKeyConstraint(['conversation_id'], ['tutor_conversations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tutor_messages_conversation_id'), 'tutor_messages', ['conversation_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_tutor_messages_conversation_id'), table_name='tutor_messages')
    op.drop_table('tutor_messages')
    op.drop_index(op.f('ix_tutor_conversations_user_id'), table_name='tutor_conversations')
    op.drop_index(op.f('ix_tutor_conversations_project_id'), table_name='tutor_conversations')
    op.drop_table('tutor_conversations')
