"""merge heads + allow mistake.pattern_detected learning event

Revision ID: e8f1a2b3c4d5
Revises: b7c8d9e0f1a2, c9f1a2b3d4e5
Create Date: 2026-09-18

Merges the e5f6a7b8c9d0 branchpoint (embeddings model-default fix and
material figures) and extends ck_learning_events_type with the
repeated-mistake workflow's `mistake.pattern_detected` event (H4):
Identify Pattern -> Update Learning Context -> Targeted Recommendation.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e8f1a2b3c4d5'
down_revision: Union[str, Sequence[str], None] = ('b7c8d9e0f1a2', 'c9f1a2b3d4e5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_TYPES = (
    "'project.created', 'material.uploaded', 'material.ready', "
    "'material.failed', 'tutor.message', 'quiz.started', 'quiz.completed', "
    "'question.answered', 'assessment.completed', 'mastery.updated', "
    "'recommendation.generated'"
)
_NEW_TYPES = _OLD_TYPES + ", 'mistake.pattern_detected'"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE learning_events DROP CONSTRAINT ck_learning_events_type")
    op.execute(
        "ALTER TABLE learning_events ADD CONSTRAINT ck_learning_events_type "
        f"CHECK (event_type IN ({_NEW_TYPES}))"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM learning_events WHERE event_type = 'mistake.pattern_detected'")
    op.execute("ALTER TABLE learning_events DROP CONSTRAINT ck_learning_events_type")
    op.execute(
        "ALTER TABLE learning_events ADD CONSTRAINT ck_learning_events_type "
        f"CHECK (event_type IN ({_OLD_TYPES}))"
    )
