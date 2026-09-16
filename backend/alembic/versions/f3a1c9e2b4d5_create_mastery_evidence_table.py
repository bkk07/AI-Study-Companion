"""create mastery_evidence table

Revision ID: f3a1c9e2b4d5
Revises: a8948d1582d1
Create Date: 2026-09-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a1c9e2b4d5'
down_revision: Union[str, Sequence[str], None] = 'a8948d1582d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('mastery_evidence',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('concept_id', sa.UUID(), nullable=False),
    sa.Column('evidence_type', sa.Text(), nullable=False),
    sa.Column('raw_score', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('feedback', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("evidence_type IN ('mcq', 'open_ended', 'explain_back')", name='ck_mastery_evidence_type'),
    sa.CheckConstraint('raw_score BETWEEN 0 AND 100', name='ck_mastery_evidence_score'),
    sa.ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mastery_evidence_concept_id'), 'mastery_evidence', ['concept_id'], unique=False)
    op.create_index(op.f('ix_mastery_evidence_project_id'), 'mastery_evidence', ['project_id'], unique=False)
    op.create_index(op.f('ix_mastery_evidence_user_id'), 'mastery_evidence', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_mastery_evidence_user_id'), table_name='mastery_evidence')
    op.drop_index(op.f('ix_mastery_evidence_project_id'), table_name='mastery_evidence')
    op.drop_index(op.f('ix_mastery_evidence_concept_id'), table_name='mastery_evidence')
    op.drop_table('mastery_evidence')
