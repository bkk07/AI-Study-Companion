"""add extraction_method to document_chunks (hybrid PDF OCR provenance)

Revision ID: 7e1b9c4a2d05
Revises: c4d2e8a1f7b3
Create Date: 2026-09-16

Nullable on purpose: pre-OCR rows keep NULL (= PyMuPDF TEXT era), new rows
carry "TEXT" or "OCR" from the per-page router for source traceability.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e1b9c4a2d05'
down_revision: Union[str, Sequence[str], None] = 'c4d2e8a1f7b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('document_chunks', sa.Column('extraction_method', sa.String(length=8), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('document_chunks', 'extraction_method')
