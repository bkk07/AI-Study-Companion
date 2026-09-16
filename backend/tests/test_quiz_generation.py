"""Phase 35 — quiz generation: validate-before-persist with one retry (real PG)."""

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
from app.services.quiz_generation_service import QuizGenerationError, generate_quiz

VALID = {
    "questions": [
        {"question_text": "Slope of y=2x?", "options": ["1", "2", "3", "4"], "correct_index": 1, "difficulty": "easy"},
        {"question_text": "Intercept of y=2x+5?", "options": ["0", "2", "5"], "correct_index": 2, "difficulty": "medium"},
    ]
}


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


def _seed(db, suffix: str, with_chunks: bool = True):
    user = User(email=f"qgen-{suffix}@example.com", hashed_password=hash_password("supersecret123"))
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
    concept = Concept(project_id=project.id, subtopic_id=sub.id, title="Slope", summary="Rise over run.")
    db.add(concept)
    db.flush()
    if with_chunks:
        mat = Material(project_id=project.id, filename="d.pdf", storage_path="/tmp/d.pdf", status="ready")
        db.add(mat)
        db.flush()
        for i, text in enumerate(["Slope is rise over run in linear equations.", "The intercept crosses the y axis."]):
            db.add(DocumentChunk(project_id=project.id, material_id=mat.id, concept_id=concept.id,
                                 chunk_index=i, content=text, page_number=i + 1, source_name="d.pdf"))
    db.commit()
    return user, project, concept


def _quiz_count(db, project_id):
    return db.query(Quiz).filter(Quiz.project_id == project_id).count()


def test_valid_generation_persists_quiz_and_questions():
    db = _session()
    try:
        _, project, concept = _seed(db, uuid.uuid4().hex[:8])
        stub = StubClient([VALID])
        quiz = generate_quiz(db, project_id=project.id, concept_id=concept.id, num_questions=2, client=stub)
        assert len(stub.calls) == 1
        system, user_prompt = stub.calls[0]
        assert "correct_index" in system
        assert "Slope is rise over run" in user_prompt  # concept chunks ground the prompt
        assert quiz.mode == "practice" and quiz.question_count == 2 and quiz.project_id == project.id
        questions = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).order_by(QuizQuestion.created_at).all()
        assert [(q.question_text, q.correct_index, q.difficulty, q.concept_id) for q in questions] == [
            ("Slope of y=2x?", 1, "easy", concept.id),
            ("Intercept of y=2x+5?", 2, "medium", concept.id),
        ]
        assert questions[0].options == ["1", "2", "3", "4"]
    finally:
        db.close()


def test_flaky_then_valid_persists_once():
    db = _session()
    try:
        _, project, concept = _seed(db, uuid.uuid4().hex[:8])
        stub = StubClient([{"questions": []}, VALID])
        quiz = generate_quiz(db, project_id=project.id, concept_id=concept.id, num_questions=2, client=stub)
        assert len(stub.calls) == 2
        assert db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).count() == 2
        assert db.query(Quiz).filter(Quiz.project_id == project.id).count() == 1
    finally:
        db.close()


def test_bad_twice_rejected_with_no_rows():
    db = _session()
    try:
        _, project, concept = _seed(db, uuid.uuid4().hex[:8])
        bad = {"questions": [
            {"question_text": "Q?", "options": ["a", "b"], "correct_index": 5, "difficulty": "easy"}]}
        stub = StubClient([bad, bad])
        with pytest.raises(QuizGenerationError):
            generate_quiz(db, project_id=project.id, concept_id=concept.id, client=stub)
        assert len(stub.calls) == 2
        assert _quiz_count(db, project.id) == 0
        assert db.query(QuizQuestion).filter(QuizQuestion.concept_id == concept.id).count() == 0
    finally:
        db.close()


def test_empty_source_and_missing_or_foreign_concept_never_call_client():
    db = _session()
    try:
        _, project, concept = _seed(db, uuid.uuid4().hex[:8], with_chunks=False)
        stub = StubClient([VALID])
        with pytest.raises(QuizGenerationError):
            generate_quiz(db, project_id=project.id, concept_id=concept.id, client=stub)
        with pytest.raises(LookupError):
            generate_quiz(db, project_id=project.id, concept_id=uuid.uuid4(), client=stub)
        with pytest.raises(LookupError):
            generate_quiz(db, project_id=uuid.uuid4(), concept_id=concept.id, client=stub)
        _, other_project, _ = _seed(db, uuid.uuid4().hex[:8])
        with pytest.raises(LookupError):  # concept from another project
            generate_quiz(db, project_id=other_project.id, concept_id=concept.id, client=stub)
        assert stub.calls == []
        assert _quiz_count(db, project.id) == 0
    finally:
        db.close()


def test_invalid_input_rejected_before_client():
    db = _session()
    try:
        _, project, concept = _seed(db, uuid.uuid4().hex[:8])
        stub = StubClient([VALID])
        for kwargs in ({"num_questions": 0}, {"num_questions": 21}, {"mode": "pop"}, {"difficulty": "extreme"}):
            with pytest.raises(ValueError):
                generate_quiz(db, project_id=project.id, concept_id=concept.id, client=stub, **kwargs)
        assert stub.calls == []
        assert _quiz_count(db, project.id) == 0
    finally:
        db.close()
