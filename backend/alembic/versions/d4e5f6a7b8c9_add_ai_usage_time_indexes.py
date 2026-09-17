"""add missing ai_usage time indexes (Phase 1 close-out)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-18

Plan asked for indexes on (created_at), (feature, created_at),
(project_id, created_at) for admin time-range aggregates. The base
migration shipped (feature, created_at) plus single-column helper
indexes only. This adds the two missing time indexes. Additive,
concurrent-safe, no data change.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_ai_usage_created', 'ai_usage', ['created_at'], unique=False)
    op.create_index('ix_ai_usage_project_created', 'ai_usage', ['project_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_ai_usage_project_created', table_name='ai_usage')
    op.drop_index('ix_ai_usage_created', table_name='ai_usage')
