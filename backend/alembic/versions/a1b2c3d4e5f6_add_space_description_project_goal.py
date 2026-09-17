"""add spaces.description + projects.description/goal (PRD section 4)

Revision ID: a1b2c3d4e5f6
Revises: f7a3c9d2e4b5
Create Date: 2026-09-17

PRD section 4 requires a Space to carry a name and description, and a
Project to carry a name, description, and learning goal. All three columns
are nullable Text so pre-existing rows keep working untouched — new creates
send values through the API. `projects.goal` feeds the recommendation
engine's goal bonus and the Tutor's project context; the descriptions are
display-only.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f7a3c9d2e4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('spaces', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('goal', sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    space_rows = bind.execute(sa.text("select count(*) from spaces where description IS NOT NULL")).scalar()
    if space_rows:
        raise RuntimeError(
            f"cannot downgrade with {space_rows} spaces carrying a description; "
            "clear them explicitly first"
        )
    project_rows = bind.execute(
        sa.text("select count(*) from projects where description IS NOT NULL OR goal IS NOT NULL")
    ).scalar()
    if project_rows:
        raise RuntimeError(
            f"cannot downgrade with {project_rows} projects carrying a description/goal; "
            "clear them explicitly first"
        )
    op.drop_column('projects', 'goal')
    op.drop_column('projects', 'description')
    op.drop_column('spaces', 'description')
