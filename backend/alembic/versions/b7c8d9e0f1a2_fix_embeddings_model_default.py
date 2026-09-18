"""fix embeddings model default to local 384-dim model

Revision ID: b7c8d9e0f1a2
Revises: e5f6a7b8c9d0
Create Date: 2026-09-18

The embeddings column is Vector(384). The previous server_default
'text-embedding-3-small' (1536-dim natively) misled operators into thinking
the OpenAI default fit the column. Both providers now write 384-dim vectors
(local natively; OpenAI via truncated `dimensions`=384), so the default label
points at the local model. The worker always writes `model` explicitly, so
this only affects the DB-level default for backfilled rows.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'embeddings', 'model',
        existing_type=sa.String(length=64),
        server_default='BAAI/bge-small-en-v1.5',
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'embeddings', 'model',
        existing_type=sa.String(length=64),
        server_default='text-embedding-3-small',
        existing_nullable=False,
    )
