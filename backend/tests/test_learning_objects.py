"""Phase A — learning-object schema, gate, and status thresholds.

Unit tests run without a DB. DB-backed tests use the dev database (same
pattern as test_mastery) and require migration 9f3a7c1e5b28 applied.
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.concept import (
    DEFAULT_IMPORTANCE,
    DEFAULT_LO_TYPE,
    LO_IMPORTANCES,
    LO_TYPES,
    Concept,
)
from app.models.concept_relationship import ConceptRelationship, RELATIONS
from app.models.material import Material
from app.models.project import Project
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.services.mastery_levels import (
    DEVELOPING,
    MASTERED,
    NEEDS_PRACTICE,
    NOT_STARTED,
    STATUSES,
    STRONG,
    is_mastery_target,
    status_for,
)


def _concept(**over):
    base = {
        "project_id": uuid.uuid4(),
        "subtopic_id": uuid.uuid4(),
        "title": "Logistic Regression",
        "summary": "A classifier.",
    }
    base.update(over)
    return Concept(**base)


# --- vocabulary -----------------------------------------------------------


def test_v1_type_and_importance_sets():
    assert LO_TYPES == ("CONCEPT", "DEFINITION", "TERM", "FORMULA", "PROCESS", "SKILL", "OTHER")
    assert LO_IMPORTANCES == ("CORE", "SUPPORTING", "REFERENCE")
    assert RELATIONS == ("PREREQUISITE_OF", "RELATED_TO", "EXAMPLE_OF", "USES", "DERIVED_FROM")
    assert (DEFAULT_LO_TYPE, DEFAULT_IMPORTANCE) == ("CONCEPT", "CORE")


# --- gate -----------------------------------------------------------------


def test_gate_core_passes_others_fail():
    assert is_mastery_target(_concept(importance="CORE")) is True
    assert is_mastery_target(_concept(importance="SUPPORTING")) is False
    assert is_mastery_target(_concept(importance="REFERENCE")) is False


def test_gate_legacy_null_importance_reads_as_core():
    assert is_mastery_target(_concept(importance=None)) is True


def test_gate_obsolete_excluded_even_when_core():
    assert is_mastery_target(_concept(meta={"status": "obsolete"})) is False
    assert is_mastery_target(_concept(meta={"status": "active"})) is True
    assert is_mastery_target(_concept()) is True  # meta None → active


# --- statuses -------------------------------------------------------------


def test_statuses_and_boundaries():
    assert STATUSES == ("Not Started", "Needs Practice", "Developing", "Strong", "Mastered")
    assert status_for(None) == NOT_STARTED
    assert status_for(0) == NEEDS_PRACTICE
    assert status_for(33.9) == NEEDS_PRACTICE
    assert status_for(34) == DEVELOPING  # aligned with adaptive bands
    assert status_for(66) == DEVELOPING
    assert status_for(66.1) == STRONG
    assert status_for(84.9) == STRONG
    assert status_for(85) == MASTERED
    assert status_for(100) == MASTERED
    for bad in (-1, 101, True, "50"):
        with pytest.raises(ValueError):
            status_for(bad)


# --- DB-backed ------------------------------------------------------------


def _session():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    get_settings.cache_clear()
    return sessionmaker(bind=engine)()


def _scaffold(db):
    user = User(email=f"lo-{uuid.uuid4().hex[:8]}@example.com",
                hashed_password=hash_password("supersecret123"))
    db.add(user)
    db.flush()
    space = Space(user_id=user.id, name="S")
    db.add(space)
    db.flush()
    project = Project(space_id=space.id, name="P")
    db.add(project)
    db.flush()
    topic = Topic(project_id=project.id, title="T")
    db.add(topic)
    db.flush()
    sub = Subtopic(project_id=project.id, topic_id=topic.id, title="ST")
    db.add(sub)
    db.flush()
    return project, sub


def test_db_round_trip_and_legacy_defaults():
    db = _session()
    try:
        project, sub = _scaffold(db)
        full = Concept(project_id=project.id, subtopic_id=sub.id, title="F = ma",
                       summary="Newton's second law.", type="FORMULA",
                       importance="CORE", page_start=6, page_end=7,
                       meta={"source_section": "Dynamics"})
        db.add(full)
        db.flush()
        legacy = Concept(project_id=project.id, subtopic_id=sub.id,
                         title="Legacy", summary="Old row.")
        db.add(legacy)
        db.flush()
        db.commit()
        db.refresh(full)
        db.refresh(legacy)
        assert (full.type, full.importance) == ("FORMULA", "CORE")
        assert (full.page_start, full.page_end) == (6, 7)
        assert full.meta == {"source_section": "Dynamics"}
        # legacy-style insert gets Python-side defaults + backfill-compatible values
        assert (legacy.type, legacy.importance) == ("CONCEPT", "CORE")
        assert legacy.meta == {}
        assert is_mastery_target(legacy) is True
    finally:
        db.close()


def test_db_check_constraints_reject_junk():
    db = _session()
    try:
        project, sub = _scaffold(db)
        db.add(Concept(project_id=project.id, subtopic_id=sub.id, title="Bad",
                       summary="x", type="ALGORITHM"))  # v1 has no ALGORITHM
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
        db.add(Concept(project_id=project.id, subtopic_id=sub.id, title="Bad2",
                       summary="x", importance="BOGUS"))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
    finally:
        db.close()


def test_db_relationship_rules():
    db = _session()
    try:
        project, sub = _scaffold(db)
        a = Concept(project_id=project.id, subtopic_id=sub.id, title="A", summary="a")
        b = Concept(project_id=project.id, subtopic_id=sub.id, title="B", summary="b")
        db.add_all([a, b])
        db.flush()
        db.add(ConceptRelationship(from_concept_id=a.id, to_concept_id=b.id,
                                   relation="PREREQUISITE_OF", created_by="llm",
                                   evidence_span="B builds on A (p.2)."))
        db.flush()
        # duplicate triple rejected
        db.add(ConceptRelationship(from_concept_id=a.id, to_concept_id=b.id,
                                   relation="PREREQUISITE_OF", created_by="structure"))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
        # self-edge rejected
        db.add(ConceptRelationship(from_concept_id=a.id, to_concept_id=a.id,
                                   relation="RELATED_TO", created_by="structure"))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
        # llm edge without evidence rejected ("no evidence → no edge")
        db.add(ConceptRelationship(from_concept_id=a.id, to_concept_id=b.id,
                                   relation="RELATED_TO", created_by="llm"))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
        db.commit()
    finally:
        db.close()


def test_db_material_delete_nulls_link_keeps_concept():
    db = _session()
    try:
        project, sub = _scaffold(db)
        mat = Material(project_id=project.id, filename="doc.pdf",
                       storage_path="/data/uploads/doc.pdf")
        db.add(mat)
        db.flush()
        c = Concept(project_id=project.id, subtopic_id=sub.id, title="Linked",
                    summary="has material", material_id=mat.id)
        db.add(c)
        db.flush()
        db.delete(mat)
        db.flush()
        db.refresh(c)
        assert c.material_id is None  # SET NULL — history survives the PDF
        assert c.title == "Linked"
        db.commit()
    finally:
        db.close()
