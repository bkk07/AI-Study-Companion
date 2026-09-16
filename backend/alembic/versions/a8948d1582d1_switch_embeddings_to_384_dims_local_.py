"""switch embeddings to 384 dims local model

Revision ID: a8948d1582d1
Revises: d323053b3a54
Create Date: 2026-09-16 09:51:05.178488

Existing rows are derived vectors from the retired 1536-dim OpenAI model and
are dropped (re-generatable via the worker); the column is then resized.
"""
from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy  # noqa: F401 — renders VECTOR(...) below
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8948d1582d1'
down_revision: Union[str, Sequence[str], None] = 'd323053b3a54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("DELETE FROM embeddings")
    op.alter_column('embeddings', 'embedding',
               existing_type=pgvector.sqlalchemy.vector.VECTOR(dim=1536),
               type_=pgvector.sqlalchemy.vector.VECTOR(dim=384),
               existing_nullable=False,
               postgresql_using="embedding::vector(384)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM embeddings")
    op.alter_column('embeddings', 'embedding',
               existing_type=pgvector.sqlalchemy.vector.VECTOR(dim=384),
               type_=pgvector.sqlalchemy.vector.VECTOR(dim=1536),
               existing_nullable=False,
               postgresql_using="embedding::vector(1536)")
