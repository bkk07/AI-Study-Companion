"""create learning_events table for product-behavior tracking (PRD §12)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-18

Additive observability table: one row per domain action with user /
project / space scope, a closed event_type set, a polymorphic
(entity_type, entity_id) ref, a small payload (counts/scores, never
full text), and a unique idempotency_key so API/Celery retries dedupe
via ON CONFLICT DO NOTHING. Safe to downgrade — rows are derived
activity data, never source of truth.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('learning_events',
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('project_id', sa.UUID(), nullable=True),
    sa.Column('space_id', sa.UUID(), nullable=True),
    sa.Column('event_type', sa.String(length=64), nullable=False),
    sa.Column('entity_type', sa.String(length=64), nullable=True),
    sa.Column('entity_id', sa.UUID(), nullable=True),
    sa.Column('payload', JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('idempotency_key', sa.String(length=128), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint(
        "event_type IN ('project.created', 'material.uploaded', 'material.ready', "
        "'material.failed', 'tutor.message', 'quiz.started', 'quiz.completed', "
        "'question.answered', 'assessment.completed', 'mastery.updated', "
        "'recommendation.generated')",
        name='ck_learning_events_type',
    ),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['space_id'], ['spaces.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('idempotency_key', name='uq_learning_events_idempotency_key')
    )
    op.create_index('ix_learning_events_user_created', 'learning_events', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_learning_events_project_created', 'learning_events', ['project_id', 'created_at'], unique=False)
    op.create_index('ix_learning_events_type_created', 'learning_events', ['event_type', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_learning_events_type_created', table_name='learning_events')
    op.drop_index('ix_learning_events_project_created', table_name='learning_events')
    op.drop_index('ix_learning_events_user_created', table_name='learning_events')
    op.drop_table('learning_events')
