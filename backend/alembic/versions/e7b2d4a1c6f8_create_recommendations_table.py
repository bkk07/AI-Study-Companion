"""create recommendations table

Revision ID: e7b2d4a1c6f8
Revises: f3a1c9e2b4d5
Create Date: 2026-09-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7b2d4a1c6f8'
down_revision: Union[str, Sequence[str], None] = 'f3a1c9e2b4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('recommendations',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('concept_id', sa.UUID(), nullable=False),
    sa.Column('action_type', sa.Text(), nullable=False),
    sa.Column('score', sa.Numeric(precision=6, scale=2), nullable=False),
    sa.Column('reasoning', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default='active', nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("action_type IN ('ask_tutor', 'targeted_quiz', 'explain_back', 'review_material', 'exam_mode')", name='ck_recommendations_action'),
    sa.CheckConstraint("status IN ('active', 'accepted', 'dismissed', 'expired')", name='ck_recommendations_status'),
    sa.ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recommendations_concept_id'), 'recommendations', ['concept_id'], unique=False)
    op.create_index(op.f('ix_recommendations_project_id'), 'recommendations', ['project_id'], unique=False)
    op.create_index(op.f('ix_recommendations_user_id'), 'recommendations', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_recommendations_user_id'), table_name='recommendations')
    op.drop_index(op.f('ix_recommendations_project_id'), table_name='recommendations')
    op.drop_index(op.f('ix_recommendations_concept_id'), table_name='recommendations')
    op.drop_table('recommendations')
