"""create flashcards table + flashcard evidence type (Flashcards v1)

Revision ID: c4d2e8a1f7b3
Revises: 9f3a7c1e5b28
Create Date: 2026-09-16

New flashcards table (SM-2 state lives on the row; review history is
derivable from mastery_evidence rows). Extends the evidence-type CHECK with
'flashcard' (routed to the applied stream). Downgrade drops the table and
restores the old CHECK — it refuses while flashcard evidence rows exist
rather than silently orphaning mastery history.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d2e8a1f7b3'
down_revision: Union[str, Sequence[str], None] = '9f3a7c1e5b28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_TYPES = "evidence_type IN ('mcq', 'open_ended', 'explain_back')"
NEW_TYPES = "evidence_type IN ('mcq', 'open_ended', 'explain_back', 'flashcard')"


def upgrade() -> None:
    op.create_table(
        'flashcards',
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('concept_id', sa.UUID(), nullable=False),
        sa.Column('front', sa.Text(), nullable=False),
        sa.Column('back', sa.Text(), nullable=False),
        sa.Column('source', sa.Text(), nullable=False, server_default='auto'),
        sa.Column('efactor', sa.Numeric(4, 2), nullable=False, server_default='2.50'),
        sa.Column('interval_days', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('repetitions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('lapses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('next_review_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_reviews', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('correct_reviews', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('concept_id', 'front', name='uq_flashcards_concept_front'),
        sa.CheckConstraint("source IN ('auto', 'manual')", name='ck_flashcards_source'),
        sa.CheckConstraint('efactor >= 1.30', name='ck_flashcards_efactor_floor'),
        sa.CheckConstraint('interval_days >= 0', name='ck_flashcards_interval_nonneg'),
        sa.CheckConstraint('repetitions >= 0', name='ck_flashcards_reps_nonneg'),
    )
    op.create_index(op.f('ix_flashcards_project_id'), 'flashcards', ['project_id'], unique=False)
    op.create_index(op.f('ix_flashcards_concept_id'), 'flashcards', ['concept_id'], unique=False)
    op.create_index(op.f('ix_flashcards_next_review'), 'flashcards', ['next_review_at'], unique=False)
    op.drop_constraint('ck_mastery_evidence_type', 'mastery_evidence', type_='check')
    op.create_check_constraint('ck_mastery_evidence_type', 'mastery_evidence', NEW_TYPES)


def downgrade() -> None:
    lingering = op.get_bind().execute(
        sa.text("select count(*) from mastery_evidence where evidence_type='flashcard'")
    ).scalar()
    if lingering:
        raise RuntimeError(
            f"cannot downgrade with {lingering} flashcard evidence rows present; "
            "delete them explicitly first"
        )
    op.drop_constraint('ck_mastery_evidence_type', 'mastery_evidence', type_='check')
    op.create_check_constraint('ck_mastery_evidence_type', 'mastery_evidence', OLD_TYPES)
    op.drop_index(op.f('ix_flashcards_next_review'), table_name='flashcards')
    op.drop_index(op.f('ix_flashcards_concept_id'), table_name='flashcards')
    op.drop_index(op.f('ix_flashcards_project_id'), table_name='flashcards')
    op.drop_table('flashcards')
