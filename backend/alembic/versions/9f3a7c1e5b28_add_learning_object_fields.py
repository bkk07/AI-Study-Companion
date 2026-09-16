"""add learning object fields (Phase A — learning model)

Revision ID: 9f3a7c1e5b28
Revises: e7b2d4a1c6f8
Create Date: 2026-09-16

Extends concepts in place (type / importance / page span / material link /
metadata) and adds concept_relationships for semantic edges. No existing
column, FK, or row is touched: all five concepts.id FK holders
(mastery_evidence, quiz_questions, document_chunks, mismatch,
recommendation) keep working untouched, and every pre-existing row backfills
to CONCEPT/CORE so all current behavior is preserved.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '9f3a7c1e5b28'
down_revision: Union[str, Sequence[str], None] = 'e7b2d4a1c6f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LO_TYPES = ('CONCEPT', 'DEFINITION', 'TERM', 'FORMULA', 'PROCESS', 'SKILL', 'OTHER')
LO_IMPORTANCES = ('CORE', 'SUPPORTING', 'REFERENCE')


def upgrade() -> None:
    # 1. New nullable columns (online-safe add; nothing existing is rewritten yet).
    op.add_column('concepts', sa.Column('type', sa.Text(), nullable=True))
    op.add_column('concepts', sa.Column('importance', sa.Text(), nullable=True))
    op.add_column('concepts', sa.Column('page_start', sa.Integer(), nullable=True))
    op.add_column('concepts', sa.Column('page_end', sa.Integer(), nullable=True))
    op.add_column('concepts', sa.Column('material_id', sa.UUID(), nullable=True))
    op.add_column('concepts', sa.Column('metadata', JSONB(), nullable=True))

    # 2. Backfill legacy rows to CONCEPT/CORE (idempotent WHERE guards).
    op.execute("UPDATE concepts SET type = 'CONCEPT' WHERE type IS NULL")
    op.execute("UPDATE concepts SET importance = 'CORE' WHERE importance IS NULL")
    op.execute("UPDATE concepts SET metadata = '{}'::jsonb WHERE metadata IS NULL")

    # 3. Constrain going forward (server defaults keep raw-SQL inserts safe).
    op.alter_column('concepts', 'type',
                    existing_type=sa.Text(), nullable=False, server_default='CONCEPT')
    op.alter_column('concepts', 'importance',
                    existing_type=sa.Text(), nullable=False, server_default='CORE')
    op.alter_column('concepts', 'metadata',
                    existing_type=JSONB(), nullable=False,
                    server_default=sa.text("'{}'::jsonb"))
    op.create_check_constraint(
        'ck_concepts_lo_type', 'concepts',
        "type IN ('CONCEPT', 'DEFINITION', 'TERM', 'FORMULA', 'PROCESS', 'SKILL', 'OTHER')")
    op.create_check_constraint(
        'ck_concepts_importance', 'concepts',
        "importance IN ('CORE', 'SUPPORTING', 'REFERENCE')")
    op.create_foreign_key(
        'fk_concepts_material_id', 'concepts', 'materials',
        ['material_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_concepts_material_id'), 'concepts', ['material_id'], unique=False)
    op.create_index(op.f('ix_concepts_importance'), 'concepts', ['importance'], unique=False)

    # 4. Semantic edges table (hierarchical PART_OF stays derived at read time).
    op.create_table(
        'concept_relationships',
        sa.Column('from_concept_id', sa.UUID(), nullable=False),
        sa.Column('to_concept_id', sa.UUID(), nullable=False),
        sa.Column('relation', sa.Text(), nullable=False),
        sa.Column('evidence_span', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Text(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['from_concept_id'], ['concepts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_concept_id'], ['concepts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('from_concept_id', 'to_concept_id', 'relation',
                            name='uq_concept_relationships_triple'),
        sa.CheckConstraint(
            "relation IN ('PREREQUISITE_OF', 'RELATED_TO', 'EXAMPLE_OF', 'USES', 'DERIVED_FROM')",
            name='ck_concept_relationships_relation'),
        sa.CheckConstraint(
            "created_by IN ('structure', 'llm')",
            name='ck_concept_relationships_created_by'),
        sa.CheckConstraint('from_concept_id <> to_concept_id',
                           name='ck_concept_relationships_no_self_edge'),
        sa.CheckConstraint(
            "(created_by <> 'llm') OR (evidence_span IS NOT NULL AND evidence_span <> '')",
            name='ck_concept_relationships_llm_evidence'),
    )
    op.create_index(op.f('ix_concept_relationships_from'), 'concept_relationships',
                    ['from_concept_id'], unique=False)
    op.create_index(op.f('ix_concept_relationships_to'), 'concept_relationships',
                    ['to_concept_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_concept_relationships_to'), table_name='concept_relationships')
    op.drop_index(op.f('ix_concept_relationships_from'), table_name='concept_relationships')
    op.drop_table('concept_relationships')
    op.drop_index(op.f('ix_concepts_importance'), table_name='concepts')
    op.drop_index(op.f('ix_concepts_material_id'), table_name='concepts')
    op.drop_constraint('fk_concepts_material_id', 'concepts', type_='foreignkey')
    op.drop_constraint('ck_concepts_importance', 'concepts', type_='check')
    op.drop_constraint('ck_concepts_lo_type', 'concepts', type_='check')
    op.drop_column('concepts', 'metadata')
    op.drop_column('concepts', 'material_id')
    op.drop_column('concepts', 'page_end')
    op.drop_column('concepts', 'page_start')
    op.drop_column('concepts', 'importance')
    op.drop_column('concepts', 'type')
