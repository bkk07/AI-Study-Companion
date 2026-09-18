"""create material_figures table (figure image store + text twin)

Revision ID: c9f1a2b3d4e5
Revises: e5f6a7b8c9d0
Create Date: 2026-09-18

One row per extracted figure: PNG on the shared volume (storage_path),
thumbnail, vision classification + summary, chart Markdown / table-scan
LaTeX twins, cropped-OCR text. Replaced per material on re-extraction
(unique on material_id + page_number + fig_index), same idempotency as
document_chunks. project_id denormalized for single-clause isolation.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'c9f1a2b3d4e5'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'material_figures',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), nullable=False),
        sa.Column('material_id', UUID(as_uuid=True), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('fig_index', sa.Integer(), nullable=False),
        sa.Column('figure_type', sa.String(length=16), server_default='DIAGRAM', nullable=False),
        sa.Column('storage_path', sa.String(length=512), nullable=False),
        sa.Column('thumb_path', sa.String(length=512), nullable=True),
        sa.Column('image_hash', sa.String(length=64), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('markdown_table', sa.Text(), nullable=True),
        sa.Column('latex_table', sa.Text(), nullable=True),
        sa.Column('ocr_text', sa.Text(), nullable=True),
        sa.Column('vision_model', sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('material_id', 'page_number', 'fig_index', name='uq_figures_material_page_idx'),
    )
    op.create_index('ix_material_figures_material_id', 'material_figures', ['material_id'])
    op.create_index('ix_material_figures_project_id', 'material_figures', ['project_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_material_figures_project_id', table_name='material_figures')
    op.drop_index('ix_material_figures_material_id', table_name='material_figures')
    op.drop_table('material_figures')
