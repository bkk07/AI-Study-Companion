"""Phase 3 — admin reads: activity, ai-usage, journey, health (real PG)."""

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.models.ai_usage import AIUsage
from app.models.background_job import BackgroundJob
from app.models.learning_event import LearningEvent
from app.models.mastery_evidence import MasteryEvidence
from app.models.concept import Concept
from app.models.project import Project
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User


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
    admin_email = f"adm3-{suffix}@example.com"
    user_email = f"usr3-{suffix}@example.com"
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


def _seed_domain(engine, user_id):
    """Space/project/quiz/attempt/evidence + usage + events + failed job. Returns ids."""
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        space = Space(user_id=user_id, name="S")
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
        concept = Concept(project_id=project.id, subtopic_id=sub.id, title="C", summary="S.")
        db.add(concept)
        db.flush()
        quiz = Quiz(project_id=project.id, mode="practice", question_count=1)
        db.add(quiz)
        db.flush()
        attempt = QuizAttempt(quiz_id=quiz.id, user_id=user_id,
                              started_at=datetime.now(timezone.utc),
                              completed_at=datetime.now(timezone.utc), score=Decimal("80"))
        db.add(attempt)
        db.flush()
        db.add(MasteryEvidence(user_id=user_id, project_id=project.id, concept_id=concept.id,
                               evidence_type="mcq", source="practice", raw_score=Decimal("80")))
        for i in range(2):
            db.add(AIUsage(user_id=user_id, project_id=project.id, feature="quiz_generation",
                           provider="groq", model="openai/gpt-oss-20b",
                           prompt_tokens=100, completion_tokens=50, tokens_estimated=False,
                           latency_ms=200 + i * 100, success=True,
                           cost_usd=Decimal("0.000023"), meta={}))
        db.add(AIUsage(user_id=user_id, project_id=project.id, feature="tutor_answer",
                       provider="groq", model="openai/gpt-oss-20b",
                       latency_ms=900, success=False, error_type="ConnectError",
                       http_status=None, cost_usd=None, meta={}))
        db.add(LearningEvent(user_id=user_id, project_id=project.id, space_id=space.id,
                             event_type="quiz.completed", entity_type="attempt",
                             entity_id=attempt.id, payload={"score": 80},
                             idempotency_key=f"test3:{attempt.id}:completed"))
        db.add(LearningEvent(user_id=user_id, project_id=project.id, space_id=space.id,
                             event_type="quiz.started", entity_type="attempt",
                             entity_id=attempt.id, payload={},
                             idempotency_key=f"test3:{attempt.id}:started"))
        job = BackgroundJob(job_type="process_pdf", status="failed",
                            material_id=None, error="boom"[:1000])
        db.add(job)
        db.commit()
        return space.id, project.id, attempt.id
    finally:
        db.close()


def _cleanup(engine, user_id, project_id):
    """Remove everything _seed_domain created (tracking rows included)."""
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        uid, pid = str(user_id), str(project_id)
        db.execute(text("DELETE FROM learning_events WHERE project_id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM ai_usage WHERE project_id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM background_jobs WHERE id IN "
                        "(SELECT id FROM background_jobs WHERE material_id IS NULL AND error = 'boom')"))
        db.execute(text("DELETE FROM quiz_answers WHERE attempt_id IN "
                        "(SELECT id FROM quiz_attempts WHERE user_id = :uid)"), {"uid": uid})
        db.execute(text("DELETE FROM quiz_attempts WHERE user_id = :uid"), {"uid": uid})
        db.execute(text("DELETE FROM mastery_evidence WHERE project_id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM quizzes WHERE project_id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM concepts WHERE project_id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM subtopics WHERE project_id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM topics WHERE project_id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM spaces WHERE user_id = :uid"), {"uid": uid})
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": uid})
        db.commit()
    finally:
        db.close()


def test_non_admin_refused_on_all_new_endpoints():
    client, engine = _setup()
    try:
        ha, hu, _, plain_id = _users(client, engine)
        assert client.get("/api/v1/admin/activity").status_code == 401
        for url in ("/api/v1/admin/activity", "/api/v1/admin/ai-usage",
                    f"/api/v1/admin/users/{plain_id}/journey", "/api/v1/admin/health"):
            assert client.get(url, headers=hu).status_code == 403, url
            assert client.get(url, headers=ha).status_code == 200, url
    finally:
        _teardown(engine)


def test_activity_filters_and_pagination():
    client, engine = _setup()
    try:
        ha, _, _, plain_id = _users(client, engine)
        _, pid, _ = _seed_domain(engine, plain_id)
        r = client.get("/api/v1/admin/activity", headers=ha)
        assert r.status_code == 200
        assert r.json()["total"] >= 2
        r = client.get("/api/v1/admin/activity",
                       params={"user_id": str(plain_id), "type": "quiz.completed"}, headers=ha)
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["event_type"] == "quiz.completed"
        assert body["items"][0]["payload"] == {"score": 80}
        r = client.get("/api/v1/admin/activity",
                       params={"user_id": str(plain_id), "limit": 1, "offset": 0}, headers=ha)
        assert len(r.json()["items"]) == 1 and r.json()["total"] >= 2
        r = client.get("/api/v1/admin/activity",
                       params={"user_id": str(uuid.uuid4())}, headers=ha)
        assert r.json()["total"] == 0 and r.json()["items"] == []
    finally:
        _cleanup(engine, plain_id, pid)
        _teardown(engine)


def test_ai_usage_aggregates():
    client, engine = _setup()
    try:
        ha, _, _, plain_id = _users(client, engine)
        _, pid, _ = _seed_domain(engine, plain_id)
        r = client.get("/api/v1/admin/ai-usage", headers=ha)
        assert r.status_code == 200
        body = r.json()
        assert body["calls"] >= 3
        assert body["prompt_tokens"] >= 200 and body["completion_tokens"] >= 100
        assert body["cost_usd"] and body["cost_usd"] > 0
        assert 0.0 < body["error_rate"] < 1.0
        assert body["latency_p50_ms"] is not None and body["latency_p95_ms"] is not None
        assert body["latency_p50_ms"] <= body["latency_p95_ms"]
        assert any(e["error_type"] == "ConnectError" and e["count"] >= 1 for e in body["top_errors"])
        assert any(row["feature"] == "quiz_generation" and row["calls"] >= 2 for row in body["rows"])
        assert any(row["feature"] == "quiz_generation" and row["provider"] == "groq"
                   for row in body["rows"])
        r = client.get("/api/v1/admin/ai-usage",
                       params={"feature": "quiz_generation"}, headers=ha)
        assert r.json()["error_rate"] == 0.0
        r = client.get("/api/v1/admin/ai-usage",
                       params={"provider": "groq"}, headers=ha)
        assert r.json()["calls"] >= 3
        r = client.get("/api/v1/admin/ai-usage",
                       params={"provider": "inception"}, headers=ha)
        scoped = r.json()
        assert scoped["calls"] <= body["calls"]
        assert all(row["provider"] == "inception" for row in scoped["rows"])
        r = client.get("/api/v1/admin/ai-usage",
                       params={"model": "no-such-model"}, headers=ha)
        assert r.json()["calls"] == 0 and r.json()["rows"] == []
    finally:
        _cleanup(engine, plain_id, pid)
        _teardown(engine)


def test_journey_and_404():
    client, engine = _setup()
    try:
        ha, _, _, plain_id = _users(client, engine)
        _, pid, aid = _seed_domain(engine, plain_id)
        r = client.get(f"/api/v1/admin/users/{plain_id}/journey", headers=ha)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["user_id"] == str(plain_id)
        assert any(p["id"] == str(pid) for p in body["projects"])
        assert any(e["event_type"] == "quiz.completed" for e in body["recent_events"])
        assert any(a["id"] == str(aid) and a["score"] == 80.0 for a in body["recent_attempts"])
        assert body["mastery"]["evidence_rows"] >= 1
        assert body["mastery"]["by_type"].get("mcq") == 1
        assert body["mastery"]["avg_score"] == 80.0
        assert body["spend"]["calls"] >= 3 and body["spend"]["cost_usd"] > 0
        assert client.get(f"/api/v1/admin/users/{uuid.uuid4()}/journey", headers=ha).status_code == 404
    finally:
        _cleanup(engine, plain_id, pid)
        _teardown(engine)


def test_health_surfaces_failures():
    client, engine = _setup()
    try:
        ha, _, _, plain_id = _users(client, engine)
        _, pid, _ = _seed_domain(engine, plain_id)
        r = client.get("/api/v1/admin/health", headers=ha)
        assert r.status_code == 200
        body = r.json()
        assert any(j["status"] == "failed" for j in body["failed_jobs"])
        assert any(c["error_type"] == "ConnectError" for c in body["failed_llm_calls"])
        assert body["failed_job_count_24h"] >= 1
        assert body["failed_llm_count_24h"] >= 1
        assert any(r["status"] == "failed" and r["count"] >= 1 for r in body["jobs_by_status"])
    finally:
        _cleanup(engine, plain_id, pid)
        _teardown(engine)
