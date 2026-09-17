"""add mastery_evidence.source + tutor evidence type (Mastery Plan A)

Revision ID: f7a3c9d2e4b5
Revises: c9d3e5f7a1b2
Create Date: 2026-09-17

Plan A splits mastery into five activity streams (quiz 35 / open_ended 25 /
practice 20 / flashcard 15 / tutor 5). The new nullable `source` column
records the stream; legacy rows keep source NULL and the engine routes them
by `evidence_type`, so existing history is untouched. `evidence_type` gains
'tutor' for graded tutor checks only — plain tutor messages never write
evidence rows.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a3c9d2e4b5'
down_revision: Union[str, Sequence[str], None] = 'c9d3e5f7a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_TYPES = "evidence_type IN ('mcq', 'open_ended', 'explain_back', 'flashcard')"
NEW_TYPES = "evidence_type IN ('mcq', 'open_ended', 'explain_back', 'flashcard', 'tutor')"
SOURCE_CHECK = "source IS NULL OR source IN ('tutor', 'practice', 'quiz', 'open_ended', 'flashcard')"


def upgrade() -> None:
    op.add_column('mastery_evidence', sa.Column('source', sa.Text(), nullable=True))
    op.create_index(op.f('ix_mastery_evidence_source'), 'mastery_evidence', ['source'], unique=False)
    op.drop_constraint('ck_mastery_evidence_type', 'mastery_evidence', type_='check')
    op.create_check_constraint('ck_mastery_evidence_type', 'mastery_evidence', NEW_TYPES)
    op.create_check_constraint('ck_mastery_evidence_source', 'mastery_evidence', SOURCE_CHECK)


def downgrade() -> None:
    bind = op.get_bind()
    tutor_rows = bind.execute(sa.text("select count(*) from mastery_evidence where evidence_type='tutor'")).scalar()
    if tutor_rows:
        raise RuntimeError(
            f"cannot downgrade with {tutor_rows} tutor evidence rows present; "
            "delete them explicitly first"
        )
    sourced_rows = bind.execute(sa.text("select count(*) from mastery_evidence where source IS NOT NULL")).scalar()
    if sourced_rows:
        raise RuntimeError(
            f"cannot downgrade with {sourced_rows} sourced evidence rows present; "
            "delete them explicitly first"
        )
    op.drop_constraint('ck_mastery_evidence_source', 'mastery_evidence', type_='check')
    op.drop_constraint('ck_mastery_evidence_type', 'mastery_evidence', type_='check')
    op.create_check_constraint('ck_mastery_evidence_type', 'mastery_evidence', OLD_TYPES)
    op.drop_index(op.f('ix_mastery_evidence_source'), table_name='mastery_evidence')
    op.drop_column('mastery_evidence', 'source')
