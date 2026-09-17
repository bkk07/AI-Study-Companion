"""Personalized Home read-model: continue, projects, stats, attention, actions (real PG)."""

import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.concept import Concept
from app.models.flashcard import Flashcard
from app.models.learning_event import LearningEvent
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project
from app.models.recommendation import Recommendation
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


def _concept(db, project, suffix, title="Slope"):
    topic = Topic(project_id=project.id, title=f"T-{suffix}")
    db.add(topic)
    db.flush()
    sub = Subtopic(project_id=project.id, topic_id=topic.id, title=f"ST-{suffix}")
    db.add(sub)
    db.flush()
    concept = Concept(project_id=project.id, subtopic_id=sub.id, title=title,
                      summary="S.", type="CONCEPT", importance="CORE")
    db.add(concept)
    db.flush()
    return concept


def _seed(engine, email):
    """Two projects: P1 rich (evidence gap + due card + active rec + events), P2 quiet."""
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        suffix = uuid.uuid4().hex[:8]
        user = db.query(User).filter(User.email == email).one()
        space = Space(user_id=user.id, name="S")
        db.add(space)
        db.flush()
        p1 = Project(space_id=space.id, name="P1")
        p2 = Project(space_id=space.id, name="P2")
        db.add_all([p1, p2])
        db.flush()
        c1 = _concept(db, p1, suffix)
        c2 = _concept(db, p2, suffix, title="Intercept")
        now = datetime.now(timezone.utc)
        for _ in range(3):
            db.add(MasteryEvidence(user_id=user.id, project_id=p1.id, concept_id=c1.id,
                                   evidence_type="mcq", source="practice",
                                   raw_score=Decimal("90"), created_at=now - timedelta(days=1)))
        db.add(MasteryEvidence(user_id=user.id, project_id=p1.id, concept_id=c1.id,
                               evidence_type="open_ended", source="open_ended",
                               raw_score=Decimal("40"), created_at=now - timedelta(days=1)))
        db.add(Flashcard(project_id=p1.id, concept_id=c1.id, front="Q?", back="A.",
                         next_review_at=now - timedelta(hours=1)))
        db.add(Recommendation(user_id=user.id, project_id=p1.id, concept_id=c1.id,
                              action_type="explain_back", score=Decimal("80"),
                              reasoning="Weak applied.", status="active"))
        db.add(LearningEvent(user_id=user.id, project_id=p1.id, space_id=space.id,
                             event_type="quiz.completed", entity_type="attempt",
                             entity_id=uuid.uuid4(), payload={"score": 80},
                             idempotency_key=f"home:{suffix}:qdone",
                             created_at=now - timedelta(hours=2)))
        db.add(LearningEvent(user_id=user.id, project_id=p2.id, space_id=space.id,
                             event_type="tutor.message", entity_type="message",
                             entity_id=uuid.uuid4(), payload={},
                             idempotency_key=f"home:{suffix}:tutor",
                             created_at=now - timedelta(days=3)))
        db.commit()
        return user.id, p1.id, p2.id, c1.id
    finally:
        db.close()


def _cleanup(engine, user_id, project_ids):
    from sqlalchemy import text

    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        uid = str(user_id)
        pids = [str(p) for p in project_ids]
        db.execute(text("DELETE FROM learning_events WHERE user_id = :uid"), {"uid": uid})
        db.execute(text("DELETE FROM mastery_evidence WHERE user_id = :uid"), {"uid": uid})
        db.execute(text("DELETE FROM recommendations WHERE user_id = :uid"), {"uid": uid})
        for pid in pids:
            db.execute(text("DELETE FROM flashcards WHERE project_id = :pid"), {"pid": pid})
            db.execute(text("DELETE FROM concepts WHERE project_id = :pid"), {"pid": pid})
            db.execute(text("DELETE FROM subtopics WHERE project_id = :pid"), {"pid": pid})
            db.execute(text("DELETE FROM topics WHERE project_id = :pid"), {"pid": pid})
            db.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": pid})
        db.execute(text("DELETE FROM spaces WHERE user_id = :uid"), {"uid": uid})
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": uid})
        db.commit()
    finally:
        db.close()


def test_home_requires_auth():
    client, engine = _setup()
    try:
        assert client.get("/api/v1/me/home").status_code == 401
    finally:
        _teardown(engine)


def test_home_empty_user():
    client, engine = _setup()
    try:
        suffix = uuid.uuid4().hex[:8]
        email = f"home-empty-{suffix}@example.com"
        h = _login(client, email)
        r = client.get("/api/v1/me/home", headers=h)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["continue"] is None
        assert body["recent_projects"] == []
        assert body["attention"] == [] and body["next_actions"] == []
        assert body["stats"] == {"streak_days": 0, "due_total": 0, "events_week": 0, "evidence_total": 0}
        assert len(body["week_activity"]) == 7
        assert sum(d["events"] for d in body["week_activity"]) == 0
        Sess = sessionmaker(bind=engine)
        db = Sess()
        try:
            uid = db.query(User).filter(User.email == email).one().id
        finally:
            db.close()
        _cleanup(engine, uid, [])
    finally:
        _teardown(engine)


def test_home_personalized_and_isolated():
    client, engine = _setup()
    try:
        suffix = uuid.uuid4().hex[:8]
        email_a = f"home-a-{suffix}@example.com"
        email_b = f"home-b-{suffix}@example.com"
        ha, hb = _login(client, email_a), _login(client, email_b)
        Sess = sessionmaker(bind=engine)
        db = Sess()
        try:
            uid_a = db.query(User).filter(User.email == email_a).one().id
            uid_b = db.query(User).filter(User.email == email_b).one().id
        finally:
            db.close()
        _, p1, p2, c1 = _seed(engine, email_a)

        r = client.get("/api/v1/me/home", headers=ha)
        assert r.status_code == 200, r.text
        body = r.json()

        # Continue = latest touch (P1 quiz 2h ago beats P2 tutor 3d ago).
        assert body["continue"]["project_id"] == str(p1)
        assert body["continue"]["tab"] == "quiz"

        # Recent first, progress computed, due + attention on P1.
        assert [p["id"] for p in body["recent_projects"]] == [str(p1), str(p2)]
        proj1 = body["recent_projects"][0]
        assert proj1["due_count"] == 1 and proj1["attention_count"] == 1
        assert proj1["progress_pct"] is not None

        # Attention names the gap; action is the active recommendation.
        assert any(a["mismatch_type"] == "mcq_high_applied_low" and a["concept_id"] == str(c1)
                   for a in body["attention"])
        assert any(a["action_type"] == "explain_back" and a["project_id"] == str(p1)
                   for a in body["next_actions"])
        assert all("space_id" in a for a in body["attention"] + body["next_actions"])

        # Stats + week roll-up.
        assert body["stats"]["due_total"] == 1
        assert body["stats"]["evidence_total"] == 4
        assert body["stats"]["events_week"] == 2
        assert sum(d["events"] for d in body["week_activity"]) == 2

        # Isolation: user B sees a blank home.
        rb = client.get("/api/v1/me/home", headers=hb)
        assert rb.json()["continue"] is None
        assert rb.json()["recent_projects"] == []
        assert rb.json()["stats"]["evidence_total"] == 0

        _cleanup(engine, uid_a, [p1, p2])
        _cleanup(engine, uid_b, [])
    finally:
        _teardown(engine)
