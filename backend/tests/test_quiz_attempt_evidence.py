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
from app.models.learning_event import LearningEvent
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project
from app.models.quiz import Quiz, QuizQuestion
from app.models.recommendation import Recommendation
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


def test_complete_persists_recommendation_synchronously():
    """H1: quiz completed -> mastery updated -> recommendation row, no broker.

    refresh_best_effort is a no-op under pytest, so any active row observed
    here must come from the synchronous inline recompute in complete_attempt.
    """
    db = _session()
    try:
        user, project, quiz, concepts, questions = _scaffold(db, uuid.uuid4().hex[:8])
        attempt = svc.start_attempt(db, quiz_id=quiz.id, project_id=project.id, user_id=user.id)
        _answer_all(db, project, user, attempt, questions, [True, False])
        svc.complete_attempt(db, attempt_id=attempt.id, project_id=project.id,
                             user_id=user.id)
        rows = db.query(Recommendation).filter(
            Recommendation.user_id == user.id,
            Recommendation.project_id == project.id,
            Recommendation.status == "active").all()
        assert len(rows) == 1
        assert rows[0].concept_id in {c.id for c in concepts}
        assert rows[0].reasoning
    finally:
        db.close()


def test_second_completion_supersedes_recommendation():
    """Repeated completions keep exactly one active recommendation row."""
    db = _session()
    try:
        user, project, quiz, concepts, questions = _scaffold(db, uuid.uuid4().hex[:8])
        for mask in ([True, False], [False, False]):
            attempt = svc.start_attempt(db, quiz_id=quiz.id, project_id=project.id,
                                        user_id=user.id)
            _answer_all(db, project, user, attempt, questions, mask)
            svc.complete_attempt(db, attempt_id=attempt.id, project_id=project.id,
                                 user_id=user.id)
        active = db.query(Recommendation).filter(
            Recommendation.user_id == user.id,
            Recommendation.project_id == project.id,
            Recommendation.status == "active").all()
        assert len(active) == 1
        total = db.query(Recommendation).filter(
            Recommendation.user_id == user.id,
            Recommendation.project_id == project.id).count()
        assert total == 2
    finally:
        db.close()


def _scaffold_single_concept(db, tag, n_questions=3):
    """One concept with several questions — repeated-mistake harness."""
    user = User(email=f"rm-{tag}@example.com", hashed_password=hash_password("supersecret123"))
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
    concept = Concept(project_id=project.id, subtopic_id=sub.id, title=f"C-{tag}",
                      summary="s.")
    db.add(concept)
    db.flush()
    quiz = Quiz(project_id=project.id, mode="practice", question_count=n_questions)
    db.add(quiz)
    db.flush()
    questions = []
    for i in range(n_questions):
        q = QuizQuestion(quiz_id=quiz.id, concept_id=concept.id, question_text=f"Q{i}?",
                         options=["a", "b"], correct_index=0, difficulty="easy")
        db.add(q)
        db.flush()
        questions.append(q)
    db.commit()
    return user, project, quiz, concept, questions


def _scaffold_pattern(db, tag):
    """Two concepts: A (3 misses + 3 hits, mid mastery) and B (1 miss, weakest).

    B always wins the score engine (weakness 100), so the repeated-mistake
    override for A must fire deterministically — no UUID-ordering luck.
    """
    user = User(email=f"rm-{tag}@example.com", hashed_password=hash_password("supersecret123"))
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
    concept_a = Concept(project_id=project.id, subtopic_id=sub.id, title=f"A-{tag}",
                        summary="s.")
    concept_b = Concept(project_id=project.id, subtopic_id=sub.id, title=f"B-{tag}",
                        summary="s.")
    db.add(concept_a)
    db.add(concept_b)
    db.flush()
    quiz = Quiz(project_id=project.id, mode="practice", question_count=7)
    db.add(quiz)
    db.flush()
    questions_a, questions_b = [], []
    for i in range(6):
        q = QuizQuestion(quiz_id=quiz.id, concept_id=concept_a.id, question_text=f"QA{i}?",
                         options=["a", "b"], correct_index=0, difficulty="easy")
        db.add(q)
        db.flush()
        questions_a.append(q)
    q = QuizQuestion(quiz_id=quiz.id, concept_id=concept_b.id, question_text="QB?",
                     options=["a", "b"], correct_index=0, difficulty="easy")
    db.add(q)
    db.flush()
    questions_b.append(q)
    db.commit()
    return user, project, quiz, concept_a, concept_b, questions_a, questions_b


def test_repeated_mistake_gets_targeted_recommendation():
    """H4: 3 misses on A (B scores weaker) -> override targets A explain_back."""
    db = _session()
    try:
        tag = uuid.uuid4().hex[:8]
        user, project, quiz, concept_a, concept_b, qs_a, qs_b = _scaffold_pattern(db, tag)
        attempt = svc.start_attempt(db, quiz_id=quiz.id, project_id=project.id, user_id=user.id)
        _answer_all(db, project, user, attempt, qs_a, [False, False, False, True, True, True])
        _answer_all(db, project, user, attempt, qs_b, [False])
        svc.complete_attempt(db, attempt_id=attempt.id, project_id=project.id,
                             user_id=user.id)
        active = db.query(Recommendation).filter(
            Recommendation.user_id == user.id,
            Recommendation.project_id == project.id,
            Recommendation.status == "active").all()
        assert len(active) == 1
        assert active[0].concept_id == concept_a.id
        assert active[0].action_type == "explain_back"
        assert "Missed 3 questions" in active[0].reasoning
        event = db.query(LearningEvent).filter(
            LearningEvent.event_type == "mistake.pattern_detected",
            LearningEvent.project_id == project.id).one()
        assert event.payload["wrong_count"] == 3
        assert str(event.entity_id) == str(concept_a.id)
    finally:
        db.close()


def test_repeated_mistake_stays_targeted_without_runaway():
    """H4: override corrects the engine when repetition-penalty picks a quiz."""
    db = _session()
    try:
        user, project, quiz, concept, questions = _scaffold_single_concept(db, uuid.uuid4().hex[:8])
        for _ in range(2):
            attempt = svc.start_attempt(db, quiz_id=quiz.id, project_id=project.id,
                                        user_id=user.id)
            _answer_all(db, project, user, attempt, questions, [False, False, False])
            svc.complete_attempt(db, attempt_id=attempt.id, project_id=project.id,
                                 user_id=user.id)
        active = db.query(Recommendation).filter(
            Recommendation.user_id == user.id,
            Recommendation.project_id == project.id,
            Recommendation.status == "active").all()
        assert len(active) == 1
        assert active[0].concept_id == concept.id
        assert active[0].action_type == "explain_back"
        total = db.query(Recommendation).filter(
            Recommendation.user_id == user.id,
            Recommendation.project_id == project.id).count()
        # Completion 1: engine picks explain_back (no override row). Completion 2:
        # the 7-day repetition penalty flips the engine to targeted_quiz, and the
        # override corrects it back to explain_back. Exactly 3 rows, no runaway.
        assert total == 3
    finally:
        db.close()
