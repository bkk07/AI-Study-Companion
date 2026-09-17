"""Practice multi-select quiz scope + scoped open-ended generation (real PG, stubbed LLM)."""

import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.chunk import DocumentChunk
from app.models.concept import Concept
from app.models.material import Material
from app.models.project import Project
from app.models.quiz import Quiz, QuizQuestion
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.schemas.quiz import QuizGenerateRequest
from app.services.open_ended_assessment_service import (
    OpenEndedAssessmentError,
    generate_open_ended_question,
    grade_open_ended,
)
from app.services.quiz_generation_service import QuizGenerationError, generate_scoped_quiz

VALID_MCQ = {
    "questions": [
        {"question_text": "Q1?", "options": ["a", "b", "c"], "correct_index": 0, "difficulty": "easy"},
        {"question_text": "Q2?", "options": ["a", "b"], "correct_index": 1, "difficulty": "hard"},
    ]
}

VALID_OEQ = {"question_text": "Explain slope in your own words.", "difficulty": "medium"}


class StubClient:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def __call__(self, system, user):
        self.calls.append((system, user))
        return self.payloads[min(len(self.calls) - 1, len(self.payloads) - 1)]


def _session():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    get_settings.cache_clear()
    return sessionmaker(bind=engine)()


def _seed_two_topics(db, suffix: str):
    """Project with T1(ST1: C1, C2) + T2(ST2: C3); chunks for all."""
    user = User(email=f"prac-{suffix}@example.com", hashed_password=hash_password("supersecret123"))
    db.add(user)
    db.flush()
    space = Space(user_id=user.id, name="S")
    db.add(space)
    db.flush()
    project = Project(space_id=space.id, name="P")
    db.add(project)
    db.flush()
    mat = Material(project_id=project.id, filename="d.pdf", storage_path="/tmp/d.pdf", status="ready")
    db.add(mat)
    db.flush()
    out = {}
    for ti, (tname, subs) in enumerate((("T1", (("ST1", ("C1", "C2")),)), ("T2", (("ST2", ("C3",)),)))):
        topic = Topic(project_id=project.id, title=tname)
        db.add(topic)
        db.flush()
        out[tname] = {"id": topic.id, "subs": {}}
        for sname, cnames in subs:
            sub = Subtopic(project_id=project.id, topic_id=topic.id, title=sname)
            db.add(sub)
            db.flush()
            out[tname]["subs"][sname] = {"id": sub.id, "concepts": {}}
            for ci, cname in enumerate(cnames):
                concept = Concept(project_id=project.id, subtopic_id=sub.id,
                                  title=cname, summary=f"{cname} summary.")
                db.add(concept)
                db.flush()
                out[tname]["subs"][sname]["concepts"][cname] = concept.id
                db.add(DocumentChunk(project_id=project.id, material_id=mat.id,
                                     chunk_index=ti * 10 + ci, content=f"{cname} content chunk.",
                                     page_number=ti + 1, source_name="d.pdf"))
    db.commit()
    return project, out


# --- Practice scope ---


def test_practice_union_topic_plus_concept_and_difficulty_passthrough():
    db = _session()
    try:
        project, tree = _seed_two_topics(db, uuid.uuid4().hex[:8])
        t1 = tree["T1"]["id"]
        c3 = tree["T2"]["subs"]["ST2"]["concepts"]["C3"]
        stub = StubClient([VALID_MCQ])
        quiz = generate_scoped_quiz(
            db, project_id=project.id, scope="practice",
            topic_ids=[t1], concept_ids=[c3],
            num_questions=2, difficulty="hard", client=stub,
        )
        assert len(stub.calls) == 1
        assert "hard" in stub.calls[0][1]  # difficulty reaches the prompt
        assert quiz.question_count == 2
        rows = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).all()
        got = {q.concept_id for q in rows}
        c1 = tree["T1"]["subs"]["ST1"]["concepts"]["C1"]
        c2 = tree["T1"]["subs"]["ST1"]["concepts"]["C2"]
        assert got <= {c1, c2, c3} and len(got) == 2  # round-robin over the union
    finally:
        db.close()


def test_practice_dedupes_overlapping_topic_and_subtopic():
    db = _session()
    try:
        project, tree = _seed_two_topics(db, uuid.uuid4().hex[:8])
        t1 = tree["T1"]["id"]
        st1 = tree["T1"]["subs"]["ST1"]["id"]
        c1 = tree["T1"]["subs"]["ST1"]["concepts"]["C1"]
        stub = StubClient([VALID_MCQ])
        quiz = generate_scoped_quiz(
            db, project_id=project.id, scope="practice",
            topic_ids=[t1], subtopic_ids=[st1], concept_ids=[c1],
            num_questions=2, client=stub,
        )
        rows = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).all()
        assert {q.concept_id for q in rows} <= {
            c1, tree["T1"]["subs"]["ST1"]["concepts"]["C2"]}
    finally:
        db.close()


def test_practice_guards_never_call_client():
    db = _session()
    try:
        project, tree = _seed_two_topics(db, uuid.uuid4().hex[:8])
        stub = StubClient([VALID_MCQ])
        with pytest.raises(QuizGenerationError):  # empty selection
            generate_scoped_quiz(db, project_id=project.id, scope="practice", client=stub)
        with pytest.raises(LookupError):  # foreign topic
            generate_scoped_quiz(db, project_id=project.id, scope="practice",
                                 topic_ids=[uuid.uuid4()], client=stub)
        assert stub.calls == []
        assert db.query(Quiz).filter(Quiz.project_id == project.id).count() == 0
    finally:
        db.close()


def test_practice_request_schema_requires_ids():
    with pytest.raises(Exception):
        QuizGenerateRequest(scope="practice", num_questions=5)
    req = QuizGenerateRequest(scope="practice", topic_ids=[uuid.uuid4()], num_questions=5)
    assert req.topic_ids is not None and len(req.topic_ids) == 1


# --- Open-ended generation ---


def test_open_ended_generate_scoped_question_and_anchor():
    db = _session()
    try:
        project, tree = _seed_two_topics(db, uuid.uuid4().hex[:8])
        stub = StubClient([VALID_OEQ])
        q = generate_open_ended_question(
            db, project_id=project.id, scope="topic",
            topic_id=tree["T1"]["id"], client=stub,
        )
        assert len(stub.calls) == 1
        assert q.question_text == "Explain slope in your own words."
        assert q.difficulty == "medium"
        assert q.concept_id in {tree["T1"]["subs"]["ST1"]["concepts"]["C1"],
                                tree["T1"]["subs"]["ST1"]["concepts"]["C2"]}
        assert "T1" in q.scope_label
    finally:
        db.close()


def test_open_ended_generate_guards_never_call_client():
    db = _session()
    try:
        project, tree = _seed_two_topics(db, uuid.uuid4().hex[:8])
        stub = StubClient([VALID_OEQ])
        with pytest.raises(ValueError):
            generate_open_ended_question(db, project_id=project.id, scope="topic",
                                         topic_id=None, client=stub)
        with pytest.raises(LookupError):
            generate_open_ended_question(db, project_id=project.id, scope="topic",
                                         topic_id=uuid.uuid4(), client=stub)
        with pytest.raises(ValueError):
            generate_open_ended_question(db, project_id=project.id, scope="concept",
                                         concept_id=tree["T1"]["subs"]["ST1"]["concepts"]["C1"],
                                         difficulty="extreme", client=stub)
        bad = {"question_text": "", "difficulty": "medium"}
        with pytest.raises(OpenEndedAssessmentError):
            generate_open_ended_question(
                db, project_id=project.id, scope="project", client=StubClient([bad, bad]))
        assert stub.calls == []
    finally:
        db.close()


def test_grade_includes_question_when_provided():
    db = _session()
    try:
        project, tree = _seed_two_topics(db, uuid.uuid4().hex[:8])
        c1 = tree["T1"]["subs"]["ST1"]["concepts"]["C1"]
        stub = StubClient([{"score": 90, "feedback": "Great."}])
        grade = grade_open_ended(db, project_id=project.id, concept_id=c1,
                                 answer_text="C1 content explained.",
                                 question_text="What is C1?", client=stub)
        assert grade.verdict == "pass"
        assert "What is C1?" in stub.calls[0][1]  # question-aware prompt
        stub2 = StubClient([{"score": 90, "feedback": "Great."}])
        grade_open_ended(db, project_id=project.id, concept_id=c1,
                         answer_text="C1 content explained.", client=stub2)
        assert "GENERATED QUESTION" not in stub2.calls[0][1]  # legacy path unchanged
    finally:
        db.close()


def test_open_ended_generate_practice_scope_union():
    db = _session()
    try:
        project, tree = _seed_two_topics(db, uuid.uuid4().hex[:8])
        stub = StubClient([VALID_OEQ])
        q = generate_open_ended_question(
            db, project_id=project.id, scope="practice",
            topic_ids=[tree["T1"]["id"]],
            concept_ids=[tree["T2"]["subs"]["ST2"]["concepts"]["C3"]],
            client=stub,
        )
        assert len(stub.calls) == 1
        assert q.question_text == "Explain slope in your own words."
        assert "Practice selection" in q.scope_label
        with pytest.raises(ValueError):
            generate_open_ended_question(db, project_id=project.id, scope="practice", client=stub)
    finally:
        db.close()


def test_grade_returns_structured_sections_and_legacy_stubs_still_validate():
    db = _session()
    try:
        project, tree = _seed_two_topics(db, uuid.uuid4().hex[:8])
        c1 = tree["T1"]["subs"]["ST1"]["concepts"]["C1"]
        stub = StubClient([{"score": 70, "feedback": "Partial.",
                            "strengths": ["Correct definition"],
                            "missing_points": ["No example given"],
                            "suggestions": ["Add a worked example"]}])
        grade = grade_open_ended(db, project_id=project.id, concept_id=c1,
                                 answer_text="C1 content explained.", client=stub)
        assert grade.verdict == "partial"
        assert list(grade.strengths) == ["Correct definition"]
        assert list(grade.missing_points) == ["No example given"]
        assert list(grade.suggestions) == ["Add a worked example"]
        # legacy payloads without the new keys still validate (defaults)
        stub2 = StubClient([{"score": 90, "feedback": "Great."}])
        grade2 = grade_open_ended(db, project_id=project.id, concept_id=c1,
                                  answer_text="C1 content explained.", client=stub2)
        assert list(grade2.strengths) == [] and list(grade2.missing_points) == []
    finally:
        db.close()

