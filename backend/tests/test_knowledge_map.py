"""Phase B — two-pass extraction, identity-preserving persist, relationships.

Pure/schema tests run without a DB. DB-backed tests use the dev database
(same pattern as test_mastery) with uuid-suffixed titles for isolation.
"""

import os
import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.concept import Concept
from app.models.concept_relationship import ConceptRelationship
from app.models.mastery_evidence import MasteryEvidence
from app.models.material import Material
from app.models.project import Project
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.schemas.structure import (
    LearningObjectOutline,
    TopicLearningObjects,
    TopicMapOutline,
)
from app.services import structure_extraction_service as svc
from app.services.relationship_service import get_related
from app.services.structure_extraction_service import (
    StructureExtractionError,
    build_page_tagged_text,
    extract_learning_objects,
    extract_topic_map,
    slice_topic_source,
)
from app.services.structure_persistence_service import persist_knowledge_map

MAP1 = {"topics": [{"title": "Algebra", "page_start": 1, "page_end": 4,
                    "subtopics": [{"title": "Linear", "page_start": 1, "page_end": 2},
                                  {"title": "Quadratics", "page_start": 3, "page_end": 4}]}]}

LO1 = {"name": "Slope", "subtopic": "Linear", "type": "concept",
       "importance": "core", "summary": "Rise over run.",
       "page_start": 1, "page_end": 1, "section": "Basics",
       "relationships": [{"to_name": "Intercept", "relation": "related_to",
                          "evidence_span": "slope and intercept define the line"}]}


# --- schemas --------------------------------------------------------------


def test_topic_map_schema_accepts_spans():
    out = TopicMapOutline.model_validate(MAP1)
    assert out.topics[0].subtopics[1].page_end == 4


def test_lo_schema_normalizes_case_and_requires_pages():
    out = LearningObjectOutline.model_validate(LO1)
    assert (out.type, out.importance, out.relationships[0].relation) == (
        "CONCEPT", "CORE", "RELATED_TO")
    assert out.section == "Basics"
    with pytest.raises(ValidationError):
        LearningObjectOutline.model_validate({**LO1, "type": "ALGORITHM"})  # not v1
    with pytest.raises(ValidationError):
        LearningObjectOutline.model_validate({**LO1, "importance": "CRITICAL"})
    no_pages = dict(LO1)
    del no_pages["page_start"]
    with pytest.raises(ValidationError):
        LearningObjectOutline.model_validate(no_pages)
    with pytest.raises(ValidationError):
        LearningObjectOutline.model_validate(
            {**LO1, "relationships": [{"to_name": "X", "relation": "RELATED_TO",
                                       "evidence_span": ""}]})  # no evidence, no edge
    with pytest.raises(ValidationError):
        LearningObjectOutline.model_validate(
            {**LO1, "relationships": [
                {"to_name": f"O{i}", "relation": "RELATED_TO", "evidence_span": "e"}
                for i in range(6)]})  # over the 5-edge cap


def test_other_is_accepted_fallback():
    # Ambiguity rule lives in the prompt; the schema's job is to accept OTHER
    # and reject anything outside the v1 set (so drift fails loudly).
    assert LearningObjectOutline.model_validate({**LO1, "type": "OTHER"}).type == "OTHER"
    with pytest.raises(ValidationError):
        LearningObjectOutline.model_validate({**LO1, "type": "wobbly-thing"})


# --- page tagging ----------------------------------------------------------


def test_page_tagged_text_preserves_numbering():
    pages = [{"page_number": 1, "text": "  alpha  "},
             {"page_number": 2, "text": ""},
             {"page_number": 3, "text": "gamma"}]
    tagged, count = build_page_tagged_text(pages)
    assert "[p1]\nalpha" in tagged and "[p3]\ngamma" in tagged
    assert "[p2]" not in tagged and count == 3


def test_slice_topic_source_selects_range():
    pages = [{"page_number": i, "text": f"content-{i}"} for i in (1, 2, 3, 4)]
    out = slice_topic_source(pages, 2, 3)
    assert "[p2]" in out and "[p3]" in out and "[p1]" not in out and "[p4]" not in out


# --- pass 1 ----------------------------------------------------------------


def test_pass1_valid_and_span_checked():
    seen = {}

    def fake(system, user):
        seen["user"] = user
        return MAP1

    out = extract_topic_map([{"page_number": 1, "text": "algebra text"}], 4, client=fake)
    assert out.topics[0].title == "Algebra"
    assert "[p1]" in seen["user"] and "4 pages" in seen["user"]

    with pytest.raises(StructureExtractionError):
        extract_topic_map([{"page_number": 1, "text": "x"}], 4,
                          client=lambda s, u: {"topics": [
                              {"title": "T", "page_start": 9, "page_end": 9,
                               "subtopics": [{"title": "S", "page_start": 9,
                                              "page_end": 9}]}]})
    with pytest.raises(ValueError):
        extract_topic_map([{"page_number": 1, "text": "   "}], 2, client=fake)


def test_pass1_retry_then_gives_up():
    calls = []

    def flaky(system, user):
        calls.append(1)
        return {"wrong": True} if len(calls) == 1 else MAP1

    assert extract_topic_map([{"page_number": 1, "text": "x"}], 4, client=flaky).topics
    assert len(calls) == 2
    with pytest.raises(StructureExtractionError):
        extract_topic_map([{"page_number": 1, "text": "x"}], 4,
                          client=lambda s, u: {"wrong": True})


# --- pass 2 -----------------------------------------------------------------


def test_pass2_valid_and_empty_source_rejected():
    seen = {}

    def fake(system, user):
        seen["system"] = system
        seen["user"] = user
        return {"objects": [LO1]}

    out = extract_learning_objects("Algebra", ["Linear"], "[p1]\nline stuff", 1, 2, client=fake)
    assert out.objects[0].name == "Slope"
    assert "CONCEPT" in seen["system"] and "OTHER" in seen["system"]
    assert '"Linear"' in seen["user"]
    with pytest.raises(ValueError):
        extract_learning_objects("T", [], "   ", 1, 1, client=fake)


# --- DB-backed persist -------------------------------------------------------


def _session():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    get_settings.cache_clear()
    return sessionmaker(bind=engine)()


def _scaffold(db, tag):
    user = User(email=f"km-{tag}@example.com", hashed_password=hash_password("supersecret123"))
    db.add(user)
    db.flush()
    space = Space(user_id=user.id, name="S")
    db.add(space)
    db.flush()
    project = Project(space_id=space.id, name="P")
    db.add(project)
    db.flush()
    mat = Material(project_id=project.id, filename="d.pdf", storage_path="/tmp/d.pdf")
    db.add(mat)
    db.flush()
    return user, project, mat


def _persist(db, project, mat, topics, los_by_topic):
    topic_map = TopicMapOutline.model_validate({"topics": topics})
    pairs = []
    for title, los in los_by_topic:
        span = next(t for t in topic_map.topics if t.title == title)
        pairs.append((span, TopicLearningObjects.model_validate({"objects": los})
                      if los is not None else None))
    return persist_knowledge_map(db, project_id=project.id, material_id=mat.id,
                                 topic_map=topic_map, topic_results=pairs)


def _lo(name, sub="Linear", **over):
    base = {"name": name, "subtopic": sub, "type": "CONCEPT", "importance": "CORE",
            "summary": f"About {name}.", "page_start": 1, "page_end": 1}
    base.update(over)
    return base


def test_persist_stores_classification_provenance_material():
    db = _session()
    try:
        _, project, mat = _scaffold(db, uuid.uuid4().hex[:8])
        topics = [{"title": "Algebra", "page_start": 1, "page_end": 2,
                   "subtopics": [{"title": "Linear", "page_start": 1, "page_end": 2}]}]
        res = _persist(db, project, mat, topics,
                       [("Algebra", [_lo("Slope", type="TERM", importance="SUPPORTING",
                                           page_start=1, page_end=2, section="Basics")])])
        assert res["concepts"] >= 1 and res["relationships"] == 0 and res["obsoleted"] == 0
        row = db.query(Concept).filter(Concept.project_id == project.id).one()
        assert (row.type, row.importance) == ("TERM", "SUPPORTING")
        assert (row.page_start, row.page_end) == (1, 2)
        assert row.material_id == mat.id
        assert row.meta["source_section"] == "Basics" and row.meta["extraction_pass"] == 2
        db.commit()
    finally:
        db.close()


def test_reprocess_preserves_ids_and_history():
    db = _session()
    try:
        user, project, mat = _scaffold(db, uuid.uuid4().hex[:8])
        topics = [{"title": "Algebra", "page_start": 1, "page_end": 2,
                   "subtopics": [{"title": "Linear", "page_start": 1, "page_end": 2}]}]
        _persist(db, project, mat, topics, [("Algebra", [_lo("Slope")])])
        row = db.query(Concept).filter(Concept.project_id == project.id).one()
        first_id = row.id
        db.add(MasteryEvidence(user_id=user.id, project_id=project.id, concept_id=row.id,
                               evidence_type="mcq", raw_score=80))
        db.commit()
        # reprocess with richer classification of the same object
        res = _persist(db, project, mat, topics,
                       [("Algebra", [_lo("slope", type="TERM", importance="CORE",
                                         summary="Updated summary.")])])
        assert res["obsoleted"] == 0
        again = db.query(Concept).filter(Concept.project_id == project.id).one()
        assert again.id == first_id  # same row → history intact
        assert (again.type, again.summary) == ("TERM", "Updated summary.")
        assert db.query(MasteryEvidence).filter(
            MasteryEvidence.concept_id == first_id).count() == 1
        db.commit()
    finally:
        db.close()


def test_moved_subtopic_keeps_id_and_removed_obsoletes():
    db = _session()
    try:
        _, project, mat = _scaffold(db, uuid.uuid4().hex[:8])
        topics = [{"title": "Algebra", "page_start": 1, "page_end": 4,
                   "subtopics": [{"title": "Linear", "page_start": 1, "page_end": 2},
                                 {"title": "Quadratics", "page_start": 3, "page_end": 4}]}]
        _persist(db, project, mat, topics,
                 [("Algebra", [_lo("Slope", sub="Linear"), _lo("Vertex", sub="Quadratics")])])
        by_name = {c.title: c for c in db.query(Concept).filter(Concept.project_id == project.id)}
        slope_id = by_name["Slope"].id
        # Slope moves subtopics; Vertex disappears
        res = _persist(db, project, mat, topics,
                       [("Algebra", [_lo("Slope", sub="Quadratics")])])
        assert res["obsoleted"] == 1 and res["obsoleted_titles"] == ["Vertex"]
        slope = db.get(Concept, slope_id)
        my_topic = db.query(Topic).filter(
            Topic.project_id == project.id, Topic.title == "Algebra").one()
        quad = db.query(Subtopic).filter(
            Subtopic.topic_id == my_topic.id, Subtopic.title == "Quadratics").one()
        assert slope.subtopic_id == quad.id  # moved, same id
        vertex = db.query(Concept).filter(
            Concept.project_id == project.id, Concept.title == "Vertex").one()
        assert vertex.meta["status"] == "obsolete" and "obsolete_at" in vertex.meta
        assert db.query(Concept).filter(Concept.project_id == project.id).count() == 2
        db.commit()
    finally:
        db.close()


def test_alnum_merge_keeps_most_evidenced_id():
    db = _session()
    try:
        user, project, mat = _scaffold(db, uuid.uuid4().hex[:8])
        topic = Topic(project_id=project.id, title="ML")
        db.add(topic)
        db.flush()
        sub = Subtopic(project_id=project.id, topic_id=topic.id, title="NN")
        db.add(sub)
        db.flush()
        # two near-duplicate legacy rows, only one evidenced ("k-NN" vs
        # "K.N.N.": same alnum fold, different normalized titles → exact
        # matching must NOT fire, the merge rule decides on evidence)
        evidenced = Concept(project_id=project.id, subtopic_id=sub.id,
                            title="k-NN", summary="near neighbours.")
        plain = Concept(project_id=project.id, subtopic_id=sub.id,
                        title="K.N.N.", summary="dup.")
        db.add_all([evidenced, plain])
        db.flush()
        db.add(MasteryEvidence(user_id=user.id, project_id=project.id,
                               concept_id=evidenced.id, evidence_type="mcq",
                               raw_score=90))
        db.commit()
        topics = [{"title": "ML", "page_start": 1, "page_end": 2,
                   "subtopics": [{"title": "NN", "page_start": 1, "page_end": 2}]}]
        _persist(db, project, mat, topics, [("ML", [_lo("kNN", sub="NN")])])
        rows = db.query(Concept).filter(Concept.project_id == project.id).all()
        active = [c for c in rows if c.meta.get("status") != "obsolete"]
        assert len(active) == 1 and active[0].id == evidenced.id  # history wins
        assert active[0].title == "kNN"  # winner takes the new casing
        loser = [c for c in rows if c.meta.get("status") == "obsolete"]
        assert len(loser) == 1 and loser[0].meta["merged_into"] == str(evidenced.id)
        # history FKs intact on both rows (nothing deleted)
        assert db.query(MasteryEvidence).filter(
            MasteryEvidence.concept_id == evidenced.id).count() == 1
        db.commit()
    finally:
        db.close()


def test_edges_resolve_drop_unresolvable_and_cap():
    db = _session()
    try:
        _, project, mat = _scaffold(db, uuid.uuid4().hex[:8])
        topics = [{"title": "ML", "page_start": 1, "page_end": 2,
                   "subtopics": [{"title": "Basics", "page_start": 1, "page_end": 2}]}]
        others = [_lo(f"Node{i}", sub="Basics") for i in range(7)]
        hub = _lo("Hub", sub="Basics", relationships=[
            {"to_name": f"Node{i}", "relation": "RELATED_TO",
             "evidence_span": f"hub links node {i}"} for i in range(4)
        ] + [{"to_name": "Ghost", "relation": "RELATED_TO", "evidence_span": "x"}])
        res = _persist(db, project, mat, topics, [("ML", [hub, *others])])
        # 5 proposals (schema max), 4 resolvable + 1 ghost dropped
        assert res["new_relationships"] == 4 and res["dropped_edges"] == 1
        # second pass: 3 more proposals, only 1 slot left under the stored cap
        hub2 = _lo("Hub", sub="Basics", relationships=[
            {"to_name": f"Node{i}", "relation": "RELATED_TO",
             "evidence_span": f"hub links node {i} again"} for i in (4, 5, 6)])
        res2 = _persist(db, project, mat, topics, [("ML", [hub2, *others])])
        assert res2["new_relationships"] == 1 and res2["dropped_edges"] == 2
        hub_row = db.query(Concept).filter(
            Concept.project_id == project.id, Concept.title == "Hub").one()
        rel = get_related(db, hub_row.id)
        assert rel["part_of"]["subtopic"]["title"] == "Basics"
        assert len(rel["outgoing"]) == 5
        assert all(e["evidence_span"] for e in rel["outgoing"])
        db.commit()
    finally:
        db.close()


def test_guideline_notes_are_advisory_only():
    db = _session()
    try:
        _, project, mat = _scaffold(db, uuid.uuid4().hex[:8])
        topics = [{"title": "T", "page_start": 1, "page_end": 2,
                   "subtopics": [{"title": "Thin", "page_start": 1, "page_end": 1},
                                 {"title": "Fine", "page_start": 2, "page_end": 2}]}]
        los = [_lo("Only", sub="Thin"),
               *[_lo(f"Ok{i}", sub="Fine") for i in range(3)]]
        res = _persist(db, project, mat, topics, [("T", los)])
        assert any("Thin" in n and "1 CORE" in n for n in res["guideline_notes"])
        assert not any("Fine" in n for n in res["guideline_notes"])
        # advisory: the object still persisted
        assert db.query(Concept).filter(
            Concept.project_id == project.id, Concept.title == "Only").count() == 1
        db.commit()
    finally:
        db.close()


def test_material_stamp_never_overwritten():
    db = _session()
    try:
        _, project, mat = _scaffold(db, uuid.uuid4().hex[:8])
        other = Material(project_id=project.id, filename="o.pdf", storage_path="/tmp/o.pdf")
        db.add(other)
        db.flush()
        topics = [{"title": "T", "page_start": 1, "page_end": 1,
                   "subtopics": [{"title": "S", "page_start": 1, "page_end": 1}]}]
        _persist(db, project, mat, topics, [("T", [_lo("Shared")])])
        # another material's map claims the same object → id kept, stamp kept
        _persist(db, project, other, topics, [("T", [_lo("Shared")])])
        row = db.query(Concept).filter(
            Concept.project_id == project.id, Concept.title == "Shared").one()
        assert row.material_id == mat.id
        db.commit()
    finally:
        db.close()


def test_reader_unknown_id_raises():
    import uuid as _uuid

    db = _session()
    try:
        with pytest.raises(LookupError):
            get_related(db, _uuid.uuid4())
    finally:
        db.close()
