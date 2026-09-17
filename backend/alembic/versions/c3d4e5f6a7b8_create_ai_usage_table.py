"""create ai_usage table for per-call LLM metering (PRD §14)

Revision ID: c3d4e5f6a7b8
Revises: b2c4d6e8f0a1
Create Date: 2026-09-18

Additive observability table: one row per provider call with feature,
model, token counts, latency, outcome, and estimated cost. No prompt or
response text is ever stored (PII + size). Safe to downgrade — rows are
derived metering data, never source of truth.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c4d6e8f0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('ai_usage',
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('project_id', sa.UUID(), nullable=True),
    sa.Column('feature', sa.String(length=64), nullable=False),
    sa.Column('provider', sa.String(length=32), nullable=False),
    sa.Column('model', sa.String(length=128), nullable=False),
    sa.Column('prompt_tokens', sa.Integer(), nullable=True),
    sa.Column('completion_tokens', sa.Integer(), nullable=True),
    sa.Column('tokens_estimated', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('latency_ms', sa.Integer(), nullable=True),
    sa.Column('success', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('error_type', sa.String(length=128), nullable=True),
    sa.Column('http_status', sa.Integer(), nullable=True),
    sa.Column('cost_usd', sa.Numeric(precision=10, scale=6), nullable=True),
    sa.Column('meta', JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_usage_feature'), 'ai_usage', ['feature'], unique=False)
    op.create_index(op.f('ix_ai_usage_project_id'), 'ai_usage', ['project_id'], unique=False)
    op.create_index(op.f('ix_ai_usage_user_id'), 'ai_usage', ['user_id'], unique=False)
    op.create_index('ix_ai_usage_feature_created', 'ai_usage', ['feature', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_ai_usage_feature_created', table_name='ai_usage')
    op.drop_index(op.f('ix_ai_usage_user_id'), table_name='ai_usage')
    op.drop_index(op.f('ix_ai_usage_project_id'), table_name='ai_usage')
    op.drop_index(op.f('ix_ai_usage_feature'), table_name='ai_usage')
    op.drop_table('ai_usage')
