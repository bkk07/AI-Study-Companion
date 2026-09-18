"""Phase 14 — admin AI evaluation: tutor/retrieval/assessment/rec quality (real PG).

Self-cleaning: every test deletes everything it seeds (scoped by project_id /
user ids). Exact-math assertions run inside fixed windows (2021 / 2099) so
rows from other suites (seeded at real now) can never pollute the numbers.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.models.ai_usage import AIUsage
from app.models.concept import Concept
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project
from app.models.quiz import Quiz, QuizQuestion
from app.models.quiz_attempt import QuizAnswer, QuizAttempt
from app.models.recommendation import Recommendation
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.tutor_conversation import TutorConversation, TutorMessage
from app.models.user import User

# Fixed windows far from real now: other suites seed at real now, so these
# windows contain only rows seeded here.
T0 = datetime(2021, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
T0_SINCE = "2021-03-10T00:00:00+00:00"
T0_UNTIL = "2021-03-10T23:59:59+00:00"
EMPTY_SINCE = "2099-01-01T00:00:00+00:00"
EMPTY_UNTIL = "2099-12-31T23:59:59+00:00"


def _setup():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    from app.core.config import get_settings as gs

    engine = create_engine(gs().database_url, pool_pre_ping=True, future=True)
    HostSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override():
        db = HostSessionLocal()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app), engine


def _teardown(engine):
    app.dependency_overrides.clear()
    engine.dispose()
    get_settings.cache_clear()


def _login(client, email):
    client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _users(client, engine):
    suffix = uuid.uuid4().hex[:8]
    admin_email = f"adme-{suffix}@example.com"
    user_email = f"usee-{suffix}@example.com"
    ha, hu = _login(client, admin_email), _login(client, user_email)
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        user = db.query(User).filter(User.email == admin_email).one()
        user.is_admin = True
        db.add(Space(user_id=user.id, name="admin-space"))
        db.commit()
        admin_id = user.id
        plain_id = db.query(User).filter(User.email == user_email).one().id
    finally:
        db.close()
    return ha, hu, admin_id, plain_id


def _domain(engine, user_id, at):
    """Space/project/topic/subtopic/concept/conversation chain stamped at `at`."""
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        space = Space(user_id=user_id, name="S", created_at=at)
        db.add(space)
        db.flush()
        project = Project(space_id=space.id, name="P", created_at=at)
        db.add(project)
        db.flush()
        topic = Topic(project_id=project.id, title="T", created_at=at)
        db.add(topic)
        db.flush()
        sub = Subtopic(project_id=project.id, topic_id=topic.id, title="ST", created_at=at)
        db.add(sub)
        db.flush()
        concept = Concept(project_id=project.id, subtopic_id=sub.id, title="C",
                          summary="S.", created_at=at)
        db.add(concept)
        db.flush()
        convo = TutorConversation(project_id=project.id, user_id=user_id,
                                  title="chat", created_at=at)
        db.add(convo)
        db.flush()
        db.commit()
        return project.id, concept.id, convo.id
    finally:
        db.close()


def _cleanup(engine, admin_id, plain_id, project_id):
    """Remove everything seeded here (children first)."""
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        pid, auid, puid = str(project_id), str(admin_id), str(plain_id)
        db.execute(text("DELETE FROM tutor_messages WHERE conversation_id IN "
                        "(SELECT id FROM tutor_conversations WHERE project_id = :pid)"),
                   {"pid": pid})
        db.execute(text("DELETE FROM tutor_conversations WHERE project_id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM quiz_answers WHERE attempt_id IN "
                        "(SELECT id FROM quiz_attempts WHERE user_id = :uid)"), {"uid": puid})
        db.execute(text("DELETE FROM quiz_attempts WHERE user_id = :uid"), {"uid": puid})
        db.execute(text("DELETE FROM quiz_questions WHERE quiz_id IN "
                        "(SELECT id FROM quizzes WHERE project_id = :pid)"), {"pid": pid})
        db.execute(text("DELETE FROM quizzes WHERE project_id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM mastery_evidence WHERE project_id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM recommendations WHERE project_id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM ai_usage WHERE project_id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM concepts WHERE project_id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM subtopics WHERE project_id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM topics WHERE project_id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM spaces WHERE user_id = :uid"), {"uid": puid})
        db.execute(text("DELETE FROM spaces WHERE user_id = :uid"), {"uid": auid})
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": puid})
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": auid})
        db.commit()
    finally:
        db.close()


def _ai_usage_count(engine):
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        return db.query(AIUsage).count()
    finally:
        db.close()


def test_eval_auth_refused():
    client, engine = _setup()
    try:
        ha, hu, admin_id, plain_id = _users(client, engine)
        try:
            assert client.get("/api/v1/admin/ai-evaluation").status_code == 401
            assert client.get("/api/v1/admin/ai-evaluation", headers=hu).status_code == 403
            assert client.get("/api/v1/admin/ai-evaluation", headers=ha).status_code == 200
        finally:
            _cleanup(engine, admin_id, plain_id, uuid.uuid4())
    finally:
        _teardown(engine)


def _seed_math(engine, user_id, project_id, concept_id, convo_id):
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        # Tutor: 4 assistant answers (2 supported / 2 unsupported), citations 1+2+0+1.
        db.add_all([
            TutorMessage(conversation_id=convo_id, role="assistant", content="a1",
                         supported=True, citations=[{"i": 1}], created_at=T0),
            TutorMessage(conversation_id=convo_id, role="assistant", content="a2",
                         supported=True, citations=[{"i": 1}, {"i": 2}], created_at=T0),
            TutorMessage(conversation_id=convo_id, role="assistant", content="a3",
                         supported=False, citations=[], created_at=T0),
            TutorMessage(conversation_id=convo_id, role="assistant", content="a4",
                         supported=False, citations=[{"i": 1}], created_at=T0),
            TutorMessage(conversation_id=convo_id, role="user", content="q",
                         supported=None, citations=[], created_at=T0),
        ])
        # Retrieval: 3 tutor_answer rows (A: 5+0 chunks, B: 3 chunks) + 1 other feature.
        db.add_all([
            AIUsage(user_id=user_id, project_id=project_id, feature="tutor_answer",
                    provider="groq", model="model-A", latency_ms=100, success=True,
                    meta={"chunks": 5, "min_distance": 0.2}, created_at=T0),
            AIUsage(user_id=user_id, project_id=project_id, feature="tutor_answer",
                    provider="groq", model="model-A", latency_ms=100, success=True,
                    meta={"chunks": 0, "min_distance": 0.9}, created_at=T0),
            AIUsage(user_id=user_id, project_id=project_id, feature="tutor_answer",
                    provider="groq", model="model-B", latency_ms=100, success=True,
                    meta={"chunks": 3, "min_distance": 0.5}, created_at=T0),
            AIUsage(user_id=user_id, project_id=project_id, feature="quiz_generation",
                    provider="groq", model="model-A", latency_ms=100, success=True,
                    meta={"chunks": 99, "min_distance": 0.01}, created_at=T0),
        ])
        # Assessment: 2 completed attempts (80, 60) + 1 incomplete (ignored).
        quiz = Quiz(project_id=project_id, mode="practice", question_count=3, created_at=T0)
        db.add(quiz)
        db.flush()
        qs = [
            QuizQuestion(quiz_id=quiz.id, concept_id=concept_id, question_text=f"Q{d}?",
                         options=["a", "b"], correct_index=0, difficulty=d, created_at=T0)
            for d in ("easy", "medium", "hard")
        ]
        db.add_all(qs)
        db.flush()
        a1 = QuizAttempt(quiz_id=quiz.id, user_id=user_id, started_at=T0,
                         completed_at=T0, score=Decimal("80"), created_at=T0)
        a2 = QuizAttempt(quiz_id=quiz.id, user_id=user_id, started_at=T0,
                         completed_at=T0 + timedelta(hours=1), score=Decimal("60"),
                         created_at=T0)
        a3 = QuizAttempt(quiz_id=quiz.id, user_id=user_id, started_at=T0,
                         completed_at=None, score=None, created_at=T0)
        db.add_all([a1, a2, a3])
        db.flush()
        db.add_all([
            QuizAnswer(attempt_id=a1.id, question_id=qs[0].id, selected_index=0,
                       is_correct=True),
            QuizAnswer(attempt_id=a1.id, question_id=qs[1].id, selected_index=1,
                       is_correct=False),
            QuizAnswer(attempt_id=a1.id, question_id=qs[2].id, selected_index=0,
                       is_correct=True),
            QuizAnswer(attempt_id=a2.id, question_id=qs[0].id, selected_index=0,
                       is_correct=True),
            QuizAnswer(attempt_id=a2.id, question_id=qs[1].id, selected_index=0,
                       is_correct=True),
            QuizAnswer(attempt_id=a2.id, question_id=qs[2].id, selected_index=1,
                       is_correct=False),
            QuizAnswer(attempt_id=a3.id, question_id=qs[0].id, selected_index=0,
                       is_correct=True),
        ])
        # Open-ended evidence: 90/85 pass, 60 partial, 30 fail + 1 mcq (ignored).
        db.add_all([
            MasteryEvidence(user_id=user_id, project_id=project_id, concept_id=concept_id,
                            evidence_type="explain_back", raw_score=Decimal("90"),
                            created_at=T0),
            MasteryEvidence(user_id=user_id, project_id=project_id, concept_id=concept_id,
                            evidence_type="explain_back", raw_score=Decimal("60"),
                            created_at=T0),
            MasteryEvidence(user_id=user_id, project_id=project_id, concept_id=concept_id,
                            evidence_type="explain_back", raw_score=Decimal("30"),
                            created_at=T0),
            MasteryEvidence(user_id=user_id, project_id=project_id, concept_id=concept_id,
                            evidence_type="open_ended", raw_score=Decimal("85"),
                            created_at=T0),
            MasteryEvidence(user_id=user_id, project_id=project_id, concept_id=concept_id,
                            evidence_type="mcq", raw_score=Decimal("100"), created_at=T0),
        ])
        # Recommendations: 1 active / 2 accepted / 1 dismissed / 1 expired.
        for i, st in enumerate(("active", "accepted", "accepted", "dismissed", "expired")):
            db.add(Recommendation(user_id=user_id, project_id=project_id,
                                  concept_id=concept_id, action_type="explain_back",
                                  score=Decimal("80"), reasoning=f"r{i}", status=st,
                                  created_at=T0))
        db.commit()
    finally:
        db.close()


def test_eval_math_exact():
    client, engine = _setup()
    baseline_usage = _ai_usage_count(engine)
    ha, _, admin_id, plain_id = _users(client, engine)
    pid, cid, convoid = _domain(engine, plain_id, T0)
    _seed_math(engine, plain_id, pid, cid, convoid)
    try:
        r = client.get("/api/v1/admin/ai-evaluation",
                       params={"since": T0_SINCE, "until": T0_UNTIL}, headers=ha)
        assert r.status_code == 200, r.text
        body = r.json()

        tutor = body["tutor"]
        assert tutor["answers"] == 4
        assert tutor["supported"] == 2
        assert tutor["unsupported"] == 2
        assert tutor["supported_rate"] == pytest.approx(0.5)
        assert tutor["citation_coverage"] == pytest.approx(0.75)
        assert tutor["avg_citations"] == pytest.approx(1.0)

        ret = body["retrieval"]
        assert ret["calls"] == 3
        assert ret["avg_chunks"] == pytest.approx(8 / 3)
        assert ret["avg_top_distance"] == pytest.approx(1.6 / 3)
        assert ret["zero_context_rate"] == pytest.approx(1 / 3)
        by_model = {m["model"]: m for m in ret["by_model"]}
        assert set(by_model) == {"model-A", "model-B"}
        assert by_model["model-A"]["calls"] == 2
        assert by_model["model-A"]["avg_chunks"] == pytest.approx(2.5)
        assert by_model["model-A"]["avg_top_distance"] == pytest.approx(0.55)
        assert by_model["model-B"]["calls"] == 1
        assert by_model["model-B"]["avg_chunks"] == pytest.approx(3.0)
        assert by_model["model-B"]["avg_top_distance"] == pytest.approx(0.5)

        assess = body["assessment"]
        assert assess["mcq_attempts"] == 2
        assert assess["mcq_avg_score"] == pytest.approx(70.0)
        diff = {d["difficulty"]: d for d in assess["accuracy_by_difficulty"]}
        assert set(diff) == {"easy", "medium", "hard"}
        assert (diff["easy"]["answered"], diff["easy"]["correct"]) == (2, 2)
        assert diff["easy"]["accuracy"] == pytest.approx(1.0)
        assert (diff["medium"]["answered"], diff["medium"]["correct"]) == (2, 1)
        assert diff["medium"]["accuracy"] == pytest.approx(0.5)
        assert (diff["hard"]["answered"], diff["hard"]["correct"]) == (2, 1)
        assert diff["hard"]["accuracy"] == pytest.approx(0.5)
        assert assess["open_ended_grades"] == 4
        assert assess["open_ended_avg_score"] == pytest.approx(66.25)
        assert assess["verdict_bands"] == {"pass": 2, "partial": 1, "fail": 1}

        recs = body["recommendations"]
        assert (recs["total"], recs["active"], recs["accepted"],
                recs["dismissed"], recs["expired"]) == (5, 1, 2, 1, 1)
        assert recs["accept_rate"] == pytest.approx(2 / 3)
        assert recs["dismiss_rate"] == pytest.approx(1 / 3)

        assert len(body["trends"]) == 8
    finally:
        _cleanup(engine, admin_id, plain_id, pid)
    assert _ai_usage_count(engine) == baseline_usage
    _teardown(engine)


def _monday_this_week():
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)


def test_eval_weekly_trends():
    client, engine = _setup()
    ha, _, admin_id, plain_id = _users(client, engine)
    now = datetime.now(timezone.utc)
    pid, cid, convoid = _domain(engine, plain_id, now)
    monday = _monday_this_week()
    week_a = monday - timedelta(weeks=2)
    week_b = monday - timedelta(weeks=1)
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        db.add_all([
            TutorMessage(conversation_id=convoid, role="assistant", content="a",
                         supported=True, citations=[{"i": 1}],
                         created_at=week_a + timedelta(days=2)),
            TutorMessage(conversation_id=convoid, role="assistant", content="b",
                         supported=False, citations=[],
                         created_at=week_a + timedelta(days=3)),
            TutorMessage(conversation_id=convoid, role="assistant", content="c",
                         supported=False, citations=[],
                         created_at=week_b + timedelta(days=2)),
        ])
        quiz = Quiz(project_id=pid, mode="practice", question_count=1, created_at=now)
        db.add(quiz)
        db.flush()
        db.add(QuizAttempt(quiz_id=quiz.id, user_id=plain_id, started_at=week_a,
                           completed_at=week_a + timedelta(days=1),
                           score=Decimal("90"), created_at=week_a))
        db.commit()
    finally:
        db.close()
    try:
        r = client.get("/api/v1/admin/ai-evaluation", headers=ha)
        assert r.status_code == 200, r.text
        trends = {t["week"]: t for t in r.json()["trends"]}
        assert len(trends) == 8
        expected_weeks = [(monday - timedelta(weeks=i)).date().isoformat() for i in range(8, 0, -1)]
        assert [t["week"] for t in r.json()["trends"]] == expected_weeks
        bucket_a = trends[week_a.date().isoformat()]
        assert bucket_a["supported_rate"] == pytest.approx(0.5)
        assert bucket_a["mcq_avg_score"] == pytest.approx(90.0)
        bucket_b = trends[week_b.date().isoformat()]
        assert bucket_b["supported_rate"] == pytest.approx(0.0)
        assert bucket_b["mcq_avg_score"] is None
        for w in expected_weeks:
            if w in (week_a.date().isoformat(), week_b.date().isoformat()):
                continue
            assert trends[w]["supported_rate"] is None, w
            assert trends[w]["mcq_avg_score"] is None, w
    finally:
        _cleanup(engine, admin_id, plain_id, pid)
        _teardown(engine)


def test_eval_empty_window():
    client, engine = _setup()
    try:
        ha, _, admin_id, plain_id = _users(client, engine)
        try:
            r = client.get("/api/v1/admin/ai-evaluation",
                           params={"since": EMPTY_SINCE, "until": EMPTY_UNTIL}, headers=ha)
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["tutor"]["answers"] == 0
            assert body["tutor"]["supported_rate"] is None
            assert body["tutor"]["citation_coverage"] is None
            assert body["tutor"]["avg_citations"] is None
            assert body["retrieval"]["calls"] == 0
            assert body["retrieval"]["avg_chunks"] is None
            assert body["retrieval"]["avg_top_distance"] is None
            assert body["retrieval"]["zero_context_rate"] is None
            assert body["retrieval"]["by_model"] == []
            assert body["assessment"]["mcq_attempts"] == 0
            assert body["assessment"]["mcq_avg_score"] is None
            assert body["assessment"]["accuracy_by_difficulty"] == []
            assert body["assessment"]["open_ended_grades"] == 0
            assert body["assessment"]["open_ended_avg_score"] is None
            assert body["assessment"]["verdict_bands"] == {"pass": 0, "partial": 0, "fail": 0}
            assert body["recommendations"]["total"] == 0
            assert body["recommendations"]["accept_rate"] is None
            assert body["recommendations"]["dismiss_rate"] is None
            # Trends ignore the filter window: still 8 Monday buckets.
            assert len(body["trends"]) == 8
        finally:
            _cleanup(engine, admin_id, plain_id, uuid.uuid4())
    finally:
        _teardown(engine)
