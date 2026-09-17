"""Phase 2 — learning events: idempotency, never-break, emits, no-PII (real PG)."""

import os
import uuid
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.chunk import DocumentChunk
from app.models.concept import Concept
from app.models.learning_event import LearningEvent
from app.models.material import Material
from app.models.project import Project
from app.models.quiz import Quiz, QuizQuestion
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.services import activity_service


def _engine():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    get_settings.cache_clear()
    return engine


def _seed_minimal(db, suffix):
    user = User(email=f"le-{suffix}@example.com", hashed_password=hash_password("supersecret123"))
    db.add(user)
    db.flush()
    space = Space(user_id=user.id, name="S")
    db.add(space)
    db.flush()
    project = Project(space_id=space.id, name="P")
    db.add(project)
    db.flush()
    db.commit()
    return user, space, project


def _cleanup_project(engine, user_id, project_id):
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        db.execute(
            text("DELETE FROM learning_events WHERE project_id = :pid"),
            {"pid": str(project_id)},
        )
        db.execute(text("DELETE FROM quiz_answers WHERE attempt_id IN (SELECT id FROM quiz_attempts WHERE user_id = :uid)"), {"uid": str(user_id)})
        db.execute(text("DELETE FROM quiz_attempts WHERE user_id = :uid"), {"uid": str(user_id)})
        db.execute(text("DELETE FROM quiz_questions WHERE quiz_id IN (SELECT id FROM quizzes WHERE project_id = :pid)"), {"pid": str(project_id)})
        db.execute(text("DELETE FROM quizzes WHERE project_id = :pid"), {"pid": str(project_id)})
        db.execute(text("DELETE FROM mastery_evidence WHERE project_id = :pid"), {"pid": str(project_id)})
        db.execute(text("DELETE FROM recommendations WHERE project_id = :pid"), {"pid": str(project_id)})
        db.execute(text("DELETE FROM document_chunks WHERE project_id = :pid"), {"pid": str(project_id)})
        db.execute(text("DELETE FROM materials WHERE project_id = :pid"), {"pid": str(project_id)})
        db.execute(text("DELETE FROM concepts WHERE project_id = :pid"), {"pid": str(project_id)})
        db.execute(text("DELETE FROM subtopics WHERE project_id = :pid"), {"pid": str(project_id)})
        db.execute(text("DELETE FROM topics WHERE project_id = :pid"), {"pid": str(project_id)})
        db.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": str(project_id)})
        db.execute(text("DELETE FROM spaces WHERE user_id = :uid"), {"uid": str(user_id)})
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user_id)})
        db.commit()
    finally:
        db.close()


def test_double_emit_same_key_yields_one_row():
    engine = _engine()
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        suffix = uuid.uuid4().hex[:8]
        user, space, project = _seed_minimal(db, suffix)
        uid, pid = user.id, project.id
        key = f"test:{uuid.uuid4().hex}:dedup"
        assert activity_service.record_event_committed(
            db, user_id=user.id, project_id=project.id, space_id=space.id,
            event_type=activity_service.EVENT_QUIZ_COMPLETED,
            entity_type="attempt", entity_id=uuid.uuid4(),
            payload={"score": 80}, idempotency_key=key,
        ) is True
        assert activity_service.record_event_committed(
            db, user_id=user.id, project_id=project.id, space_id=space.id,
            event_type=activity_service.EVENT_QUIZ_COMPLETED,
            entity_type="attempt", entity_id=uuid.uuid4(),
            payload={"score": 80}, idempotency_key=key,
        ) is True  # duplicate is a no-op success
        assert db.query(LearningEvent).filter(LearningEvent.idempotency_key == key).count() == 1
    finally:
        db.close()
        _cleanup_project(engine, uid, pid)
        engine.dispose()
        get_settings.cache_clear()


def test_unknown_type_and_empty_key_rejected_without_row():
    engine = _engine()
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        suffix = uuid.uuid4().hex[:8]
        user, space, project = _seed_minimal(db, suffix)
        uid, pid = user.id, project.id
        before = db.query(LearningEvent).filter(LearningEvent.project_id == project.id).count()
        assert activity_service.record_event(
            db, user_id=user.id, project_id=project.id, space_id=space.id,
            event_type="hacker.made_up", entity_type="x", entity_id=None,
            payload={}, idempotency_key=f"test:{uuid.uuid4().hex}",
        ) is False
        assert activity_service.record_event(
            db, user_id=user.id, project_id=project.id, space_id=space.id,
            event_type=activity_service.EVENT_QUIZ_COMPLETED,
            entity_type="x", entity_id=None, payload={}, idempotency_key="  ",
        ) is False
        db.rollback()  # nothing pending; keeps session clean
        assert db.query(LearningEvent).filter(LearningEvent.project_id == project.id).count() == before
    finally:
        db.close()
        _cleanup_project(engine, uid, pid)
        engine.dispose()
        get_settings.cache_clear()


def test_failed_event_never_poisons_caller_transaction():
    engine = _engine()
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        suffix = uuid.uuid4().hex[:8]
        user, space, project = _seed_minimal(db, suffix)
        uid, pid = user.id, project.id
        # Pending domain write + failing event (bad FK) → domain must survive.
        project.name = "Renamed-by-caller"
        db.add(project)
        ok = activity_service.record_event(
            db, user_id=uuid.uuid4(), project_id=project.id, space_id=space.id,
            event_type=activity_service.EVENT_QUIZ_COMPLETED,
            entity_type="attempt", entity_id=uuid.uuid4(),
            payload={}, idempotency_key=f"test:{uuid.uuid4().hex}",
        )
        assert ok is False  # bad user FK swallowed
        db.commit()  # caller commit still works — txn not poisoned
        db.refresh(project)
        assert project.name == "Renamed-by-caller"
    finally:
        db.close()
        _cleanup_project(engine, uid, pid)
        engine.dispose()
        get_settings.cache_clear()


def test_event_table_has_no_full_text_columns():
    cols = {c.name for c in LearningEvent.__table__.columns}
    for forbidden in ("prompt", "response", "content", "answer_text", "question_text", "extracted_text"):
        assert forbidden not in cols, forbidden
    assert "payload" in cols and "idempotency_key" in cols


def test_project_create_emits_event():
    from app.services.project_service import create_project

    engine = _engine()
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        suffix = uuid.uuid4().hex[:8]
        user = User(email=f"le-pc-{suffix}@example.com", hashed_password=hash_password("supersecret123"))
        db.add(user)
        db.flush()
        space = Space(user_id=user.id, name="S")
        db.add(space)
        db.flush()
        db.commit()
        uid, sid = user.id, space.id
        project = create_project(db, user_id=uid, space_id=sid, name="Journey")
        row = db.query(LearningEvent).filter(
            LearningEvent.idempotency_key == f"project:{project.id}:created"
        ).one()
        assert row.event_type == "project.created"
        assert row.user_id == uid and row.project_id == project.id and row.space_id == sid
        assert row.payload == {}
    finally:
        db.close()
        _cleanup_project(engine, uid, project.id)
        engine.dispose()
        get_settings.cache_clear()


def _seed_quiz_harness(db, suffix):
    from app.models.quiz import Quiz

    user = User(email=f"le-q-{suffix}@example.com", hashed_password=hash_password("supersecret123"))
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
    quiz = Quiz(project_id=project.id, mode="practice", question_count=1)
    db.add(quiz)
    db.flush()
    question = QuizQuestion(
        quiz_id=quiz.id, concept_id=concept.id, question_text="What is slope?",
        options=["a", "b"], correct_index=0, difficulty="easy",
    )
    db.add(question)
    db.flush()
    db.commit()
    return user, space, project, quiz, question, concept


def test_quiz_lifecycle_emits_started_answered_completed_and_mastery():
    from app.services import quiz_attempt_service

    engine = _engine()
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        suffix = uuid.uuid4().hex[:8]
        user, space, project, quiz, question, concept = _seed_quiz_harness(db, suffix)
        uid, pid = user.id, project.id
        attempt = quiz_attempt_service.start_attempt(db, quiz_id=quiz.id, project_id=pid, user_id=uid)
        assert db.query(LearningEvent).filter(
            LearningEvent.idempotency_key == f"attempt:{attempt.id}:started").count() == 1
        answer, _ = quiz_attempt_service.submit_answer(
            db, attempt_id=attempt.id, project_id=pid, user_id=uid,
            question_id=question.id, selected_index=0, confidence=4)
        row = db.query(LearningEvent).filter(
            LearningEvent.idempotency_key == f"answer:{answer.id}").one()
        assert row.event_type == "question.answered"
        assert row.payload["is_correct"] is True
        assert "selected" not in str(row.payload) and "slope" not in str(row.payload).lower()
        done = quiz_attempt_service.complete_attempt(db, attempt_id=attempt.id, project_id=pid, user_id=uid)
        assert float(done.score) == 100.0
        completed = db.query(LearningEvent).filter(
            LearningEvent.idempotency_key == f"quiz:{attempt.id}:completed").one()
        assert completed.event_type == "quiz.completed"
        assert completed.payload["score"] == 100.0
        mastery = db.query(LearningEvent).filter(
            LearningEvent.idempotency_key == f"attempt:{attempt.id}:mastery").one()
        assert mastery.event_type == "mastery.updated"
        assert mastery.payload["evidence_rows"] == 1
    finally:
        db.close()
        _cleanup_project(engine, uid, pid)
        engine.dispose()
        get_settings.cache_clear()


def test_explain_back_emits_assessment_and_mastery_without_text():
    from app.services.explain_it_back_service import submit_explanation

    engine = _engine()
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        suffix = uuid.uuid4().hex[:8]
        user = User(email=f"le-e-{suffix}@example.com", hashed_password=hash_password("supersecret123"))
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
        concept = Concept(project_id=project.id, subtopic_id=sub.id, title="C", summary="Sum.")
        db.add(concept)
        db.flush()
        mat = Material(project_id=project.id, filename="d.pdf", storage_path="/tmp/d.pdf", status="ready")
        db.add(mat)
        db.flush()
        db.add(DocumentChunk(project_id=project.id, material_id=mat.id, concept_id=concept.id,
                             chunk_index=0, content="Content here.", page_number=1, source_name="d.pdf"))
        db.commit()
        uid, pid, cid = user.id, project.id, concept.id

        def fake_client(system, user_prompt):
            return {"score": 85, "feedback": "Good.", "strengths": [], "missing_points": [], "suggestions": []}

        evidence, grade = submit_explanation(
            db, project_id=pid, concept_id=cid, user_id=uid,
            explanation_text="My explanation.", client=fake_client)
        assess = db.query(LearningEvent).filter(
            LearningEvent.idempotency_key == f"evidence:{evidence.id}:assessment").one()
        assert assess.event_type == "assessment.completed"
        assert assess.payload["score"] == 85
        assert "explanation" not in str(assess.payload).lower()
        mastery = db.query(LearningEvent).filter(
            LearningEvent.idempotency_key == f"evidence:{evidence.id}:mastery").one()
        assert mastery.event_type == "mastery.updated"
    finally:
        db.close()
        _cleanup_project(engine, uid, pid)
        engine.dispose()
        get_settings.cache_clear()


def test_recommendation_emit_uses_row_id_key():
    from app.services.recommendation_service import ConceptSignal, recommend

    engine = _engine()
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        suffix = uuid.uuid4().hex[:8]
        user = User(email=f"le-r-{suffix}@example.com", hashed_password=hash_password("supersecret123"))
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
        concept = Concept(project_id=project.id, subtopic_id=sub.id, title="Slope", summary="S.")
        db.add(concept)
        db.flush()
        db.commit()
        uid, pid = user.id, project.id
        row = recommend(db, user_id=uid, project_id=pid,
                        signals=[ConceptSignal(concept_id=concept.id, name="Slope", mcq=40.0, applied=40.0)])
        assert row is not None
        got = db.query(LearningEvent).filter(
            LearningEvent.idempotency_key == f"recommendation:{row.id}").one()
        assert got.event_type == "recommendation.generated"
        assert got.payload["action"] == row.action_type
    finally:
        db.close()
        _cleanup_project(engine, uid, pid)
        engine.dispose()
        get_settings.cache_clear()


def test_check_constraint_rejects_unknown_type_at_db_level():
    engine = _engine()
    Sess = sessionmaker(bind=engine)
    db = Sess()
    in_txn = False
    try:
        suffix = uuid.uuid4().hex[:8]
        user, space, project = _seed_minimal(db, suffix)
        uid, pid, sid = user.id, project.id, space.id
        db.execute(
            text("INSERT INTO learning_events (id, user_id, project_id, space_id, event_type, payload, idempotency_key)"
                 " VALUES (gen_random_uuid(), :uid, :pid, :sid, 'bogus.type', '{}', :key)"),
            {"uid": str(uid), "pid": str(pid), "sid": str(sid), "key": f"test:{suffix}:bogus"},
        )
        db.flush()
        in_txn = True
        raise AssertionError("expected check-constraint violation")
    except AssertionError:
        raise
    except Exception:
        pass
    finally:
        try:
            db.rollback()
        except Exception:
            pass
        db.close()
        _cleanup_project(engine, uid, pid)
        engine.dispose()
        get_settings.cache_clear()
