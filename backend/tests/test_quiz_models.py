"""Phase 34 — quiz model round-trip, cascade, and CHECK constraints (host PG)."""

import os
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.concept import Concept
from app.models.project import Project
from app.models.quiz import Quiz, QuizQuestion
from app.models.quiz_attempt import QuizAnswer, QuizAttempt
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User


def _session():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    Sess = sessionmaker(bind=engine)
    db = Sess()
    get_settings.cache_clear()
    return db


def _seed_hierarchy(db, suffix: str):
    user = User(email=f"quiz-{suffix}@example.com", hashed_password=hash_password("supersecret123"))
    db.add(user)
    db.flush()
    space = Space(user_id=user.id, name="S")
    db.add(space)
    db.flush()
    project = Project(space_id=space.id, name="P")
    db.add(project)
    db.flush()
    topic = Topic(project_id=project.id, title="Algebra")
    db.add(topic)
    db.flush()
    sub = Subtopic(project_id=project.id, topic_id=topic.id, title="Linear")
    db.add(sub)
    db.flush()
    concept = Concept(project_id=project.id, subtopic_id=sub.id, title="Slope", summary="Rise over run.")
    db.add(concept)
    db.commit()
    return user, project, concept


def test_round_trip_quiz_to_answers():
    db = _session()
    try:
        user, project, concept = _seed_hierarchy(db, uuid.uuid4().hex[:8])
        quiz = Quiz(project_id=project.id, mode="practice", question_count=2, time_limit_seconds=None)
        db.add(quiz)
        db.flush()
        q1 = QuizQuestion(
            quiz_id=quiz.id, concept_id=concept.id, question_text="Slope of y=2x?",
            options=["1", "2", "3", "4"], correct_index=1, difficulty="easy", source_chunk_id=None,
        )
        q2 = QuizQuestion(
            quiz_id=quiz.id, concept_id=concept.id, question_text="Intercept of y=2x+5?",
            options=["0", "2", "5", "7"], correct_index=2, difficulty="medium", source_chunk_id=None,
        )
        db.add_all([q1, q2])
        db.flush()
        attempt = QuizAttempt(quiz_id=quiz.id, user_id=user.id)
        db.add(attempt)
        db.flush()
        a1 = QuizAnswer(attempt_id=attempt.id, question_id=q1.id, selected_index=1, is_correct=True, confidence=4)
        a2 = QuizAnswer(attempt_id=attempt.id, question_id=q2.id, selected_index=0, is_correct=False, confidence=None)
        db.add_all([a1, a2])
        db.commit()

        got = db.query(QuizAnswer).filter(QuizAnswer.attempt_id == attempt.id).order_by(QuizAnswer.created_at).all()
        assert [(a.selected_index, a.is_correct, a.confidence) for a in got] == [(1, True, 4), (0, False, None)]
        assert all(a.answered_at is not None for a in got)
        assert db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).count() == 2
        assert got[0].question_id == q1.id
        # Evidence stays concept-tied:
        assert db.get(QuizQuestion, got[0].question_id).concept_id == concept.id

        attempt.score = Decimal("50.00")
        attempt.completed_at = got[0].answered_at
        db.commit()
        assert db.get(QuizAttempt, attempt.id).score == Decimal("50.00")

        db.delete(user)
        db.commit()
    finally:
        db.close()


def test_cascade_quiz_deletes_questions_attempts_answers():
    db = _session()
    try:
        user, project, concept = _seed_hierarchy(db, uuid.uuid4().hex[:8])
        quiz = Quiz(project_id=project.id, mode="exam", question_count=1, time_limit_seconds=600)
        db.add(quiz)
        db.flush()
        q = QuizQuestion(
            quiz_id=quiz.id, concept_id=concept.id, question_text="Q?",
            options=["a", "b"], correct_index=0, difficulty="hard", source_chunk_id=None,
        )
        db.add(q)
        db.flush()
        attempt = QuizAttempt(quiz_id=quiz.id, user_id=user.id)
        db.add(attempt)
        db.flush()
        db.add(QuizAnswer(attempt_id=attempt.id, question_id=q.id, selected_index=0, is_correct=True, confidence=5))
        db.commit()
        qid, aid = q.id, attempt.id
        anid = db.query(QuizAnswer).filter(QuizAnswer.attempt_id == attempt.id).one().id

        db.delete(quiz)
        db.commit()
        assert db.get(QuizQuestion, qid) is None
        assert db.get(QuizAttempt, aid) is None
        assert db.get(QuizAnswer, anid) is None

        db.delete(user)
        db.commit()
    finally:
        db.close()


def test_bad_mode_difficulty_and_confidence_rejected_and_concept_required():
    db = _session()
    try:
        user, project, concept = _seed_hierarchy(db, uuid.uuid4().hex[:8])
        with pytest.raises(IntegrityError):
            db.add(Quiz(project_id=project.id, mode="pop", question_count=1))
            db.flush()
        db.rollback()

        quiz = Quiz(project_id=project.id, mode="practice", question_count=1)
        db.add(quiz)
        db.commit()
        with pytest.raises(IntegrityError):
            db.add(QuizQuestion(
                quiz_id=quiz.id, concept_id=concept.id, question_text="Q?",
                options=["a", "b"], correct_index=0, difficulty="impossible", source_chunk_id=None))
            db.flush()
        db.rollback()
        q = QuizQuestion(
            quiz_id=quiz.id, concept_id=concept.id, question_text="Q?",
            options=["a", "b"], correct_index=0, difficulty="easy", source_chunk_id=None)
        db.add(q)
        db.flush()
        attempt = QuizAttempt(quiz_id=quiz.id, user_id=user.id)
        db.add(attempt)
        db.commit()
        for bad in (0, 6):
            with pytest.raises(IntegrityError):
                db.add(QuizAnswer(attempt_id=attempt.id, question_id=q.id,
                                  selected_index=0, is_correct=True, confidence=bad))
                db.flush()
            db.rollback()
        with pytest.raises(IntegrityError):
            db.add(QuizQuestion(quiz_id=quiz.id, concept_id=None, question_text="Q?",
                                options=["a"], correct_index=0, difficulty="easy"))
            db.flush()
        db.rollback()
        db.delete(user)
        db.commit()
    finally:
        db.close()
