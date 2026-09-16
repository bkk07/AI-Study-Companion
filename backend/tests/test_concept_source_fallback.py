"""Concept source fallback: production chunks are never concept-tagged, so quiz
and assessment generation must fall back to project-wide source (real PG)."""

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
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.services.open_ended_assessment_service import grade_open_ended
from app.services.quiz_generation_service import QuizGenerationError, generate_quiz

VALID_QUIZ = {
    "questions": [
        {"question_text": "What is photosynthesis?", "options": ["A", "B"], "correct_index": 0, "difficulty": "easy"},
    ]
}
VALID_GRADE = {"score": 88, "feedback": "Solid answer."}


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


def _seed(db, suffix, tagged: bool, with_chunks: bool = True):
    user = User(email=f"fb-{suffix}@example.com", hashed_password=hash_password("supersecret123"))
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
    concept = Concept(project_id=project.id, subtopic_id=sub.id, title="Chlorophyll", summary="Green pigment.")
    db.add(concept)
    db.flush()
    if with_chunks:
        mat = Material(project_id=project.id, filename="d.pdf", storage_path="/tmp/d.pdf", status="ready")
        db.add(mat)
        db.flush()
        db.add(DocumentChunk(project_id=project.id, material_id=mat.id,
                             concept_id=concept.id if tagged else None,
                             chunk_index=0, content="Chlorophyll absorbs sunlight.", page_number=1))
    db.commit()
    return project, concept


def test_quiz_falls_back_to_project_chunks():
    db = _session()
    try:
        project, concept = _seed(db, uuid.uuid4().hex[:8], tagged=False)
        stub = StubClient([VALID_QUIZ])
        quiz = generate_quiz(db, project_id=project.id, concept_id=concept.id, num_questions=1, client=stub)
        assert quiz.question_count == 1
        _, prompt = stub.calls[0]
        assert "Chlorophyll absorbs sunlight." in prompt  # project-wide source used
        assert "Chlorophyll" in prompt  # target concept named
        assert "<<<\n" in prompt  # delimiters preserved
    finally:
        db.close()


def test_quiz_prefers_tagged_chunks_when_present():
    db = _session()
    try:
        project, concept = _seed(db, uuid.uuid4().hex[:8], tagged=True)
        stub = StubClient([VALID_QUIZ])
        generate_quiz(db, project_id=project.id, concept_id=concept.id, num_questions=1, client=stub)
        _, prompt = stub.calls[0]
        assert "Chlorophyll absorbs sunlight." in prompt
    finally:
        db.close()


def test_quiz_still_422_when_project_has_no_chunks():
    db = _session()
    try:
        project, concept = _seed(db, uuid.uuid4().hex[:8], tagged=False, with_chunks=False)
        with pytest.raises(QuizGenerationError, match="no source chunks"):
            generate_quiz(db, project_id=project.id, concept_id=concept.id, num_questions=1,
                           client=StubClient([VALID_QUIZ]))
    finally:
        db.close()


def test_assessment_falls_back_to_project_chunks():
    db = _session()
    try:
        project, concept = _seed(db, uuid.uuid4().hex[:8], tagged=False)
        stub = StubClient([VALID_GRADE])
        grade = grade_open_ended(db, project_id=project.id, concept_id=concept.id,
                                 answer_text="Chlorophyll is green and absorbs light.", client=stub)
        assert grade.score == 88
        _, prompt = stub.calls[0]
        assert "Chlorophyll absorbs sunlight." in prompt
    finally:
        db.close()
