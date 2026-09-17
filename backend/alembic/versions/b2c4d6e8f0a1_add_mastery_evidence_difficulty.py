"""add mastery_evidence.difficulty for difficulty-weighted mastery

Revision ID: b2c4d6e8f0a1
Revises: a1b2c3d4e5f6
Create Date: 2026-09-18

The Plan A engine supports per-difficulty EMA weights (easy 0.2 / medium
0.3 / hard 0.4), but evidence rows never recorded difficulty, so every
update silently used the 0.3 default. The new nullable `difficulty` column
lets MCQ writers store the question's difficulty; legacy rows and non-MCQ
evidence keep NULL and the engine behavior for them is unchanged.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c4d6e8f0a1'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DIFFICULTY_CHECK = "difficulty IS NULL OR difficulty IN ('easy', 'medium', 'hard')"


def upgrade() -> None:
    op.add_column('mastery_evidence', sa.Column('difficulty', sa.Text(), nullable=True))
    op.create_check_constraint('ck_mastery_evidence_difficulty', 'mastery_evidence', DIFFICULTY_CHECK)


def downgrade() -> None:
    bind = op.get_bind()
    filled = bind.execute(sa.text("select count(*) from mastery_evidence where difficulty IS NOT NULL")).scalar()
    if filled:
        raise RuntimeError(
            f"cannot downgrade with {filled} difficulty-tagged evidence rows present; "
            "null them out explicitly first"
        )
    op.drop_constraint('ck_mastery_evidence_difficulty', 'mastery_evidence', type_='check')
    op.drop_column('mastery_evidence', 'difficulty')
