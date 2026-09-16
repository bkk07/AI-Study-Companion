"""Quiz completion banks mcq mastery evidence (user-reported gap fix)."""

import os
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.concept import Concept
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project
from app.models.quiz import Quiz, QuizQuestion
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.services import quiz_attempt_service as svc
from app.services.mastery_service import mastery_for_concept


def _session():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    get_settings.cache_clear()
    return sessionmaker(bind=engine)()


def _scaffold(db, tag, n_concepts=2):
    user = User(email=f"ev-{tag}@example.com", hashed_password=hash_password("supersecret123"))
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
    concepts = []
    for i in range(n_concepts):
        c = Concept(project_id=project.id, subtopic_id=sub.id, title=f"C{i}-{tag}",
                    summary="s.")
        db.add(c)
        db.flush()
        concepts.append(c)
    quiz = Quiz(project_id=project.id, mode="practice", question_count=n_concepts)
    db.add(quiz)
    db.flush()
    questions = []
    for i, c in enumerate(concepts):
        q = QuizQuestion(quiz_id=quiz.id, concept_id=c.id, question_text=f"Q{i}?",
                         options=["a", "b"], correct_index=0, difficulty="easy")
        db.add(q)
        db.flush()
        questions.append(q)
    db.commit()
    return user, project, quiz, concepts, questions


def _answer_all(db, project, user, attempt, questions, correct_mask):
    for q, ok in zip(questions, correct_mask):
        svc.submit_answer(db, attempt_id=attempt.id, project_id=project.id, user_id=user.id,
                          question_id=q.id, selected_index=0 if ok else 1, confidence=4)


def test_complete_banks_per_answer_mcq_evidence():
    db = _session()
    try:
        user, project, quiz, concepts, questions = _scaffold(db, uuid.uuid4().hex[:8])
        attempt = svc.start_attempt(db, quiz_id=quiz.id, project_id=project.id, user_id=user.id)
        _answer_all(db, project, user, attempt, questions, [True, False])
        done = svc.complete_attempt(db, attempt_id=attempt.id, project_id=project.id,
                                    user_id=user.id)
        assert done.score == Decimal("50")
        rows = db.query(MasteryEvidence).filter(
            MasteryEvidence.user_id == user.id,
            MasteryEvidence.project_id == project.id).order_by(MasteryEvidence.created_at).all()
        assert len(rows) == 2
        assert all(r.evidence_type == "mcq" for r in rows)
        assert {r.concept_id for r in rows} == {c.id for c in concepts}
        assert sorted(float(r.raw_score) for r in rows) == [0.0, 100.0]
    finally:
        db.close()


def test_unanswered_questions_bank_nothing_and_recomplete_rejected():
    db = _session()
    try:
        user, project, quiz, concepts, questions = _scaffold(db, uuid.uuid4().hex[:8])
        attempt = svc.start_attempt(db, quiz_id=quiz.id, project_id=project.id, user_id=user.id)
        _answer_all(db, project, user, attempt, questions[:1], [True])  # 1 of 2 answered
        svc.complete_attempt(db, attempt_id=attempt.id, project_id=project.id, user_id=user.id)
        assert db.query(MasteryEvidence).filter(MasteryEvidence.user_id == user.id).count() == 1
        with pytest.raises(ValueError, match="already completed"):
            svc.complete_attempt(db, attempt_id=attempt.id, project_id=project.id, user_id=user.id)
        assert db.query(MasteryEvidence).filter(MasteryEvidence.user_id == user.id).count() == 1
    finally:
        db.close()


def test_evidence_moves_mastery_and_recommendation_inputs():
    db = _session()
    try:
        user, project, quiz, concepts, questions = _scaffold(db, uuid.uuid4().hex[:8], n_concepts=1)
        attempt = svc.start_attempt(db, quiz_id=quiz.id, project_id=project.id, user_id=user.id)
        _answer_all(db, project, user, attempt, questions, [True])
        svc.complete_attempt(db, attempt_id=attempt.id, project_id=project.id, user_id=user.id)
        scores = mastery_for_concept(db, user_id=user.id, project_id=project.id,
                                     concept_id=concepts[0].id)
        assert scores.mcq.value == pytest.approx(100.0) and scores.mcq.count == 1
    finally:
        db.close()
