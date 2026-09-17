"""Tutor quiz-plan: recent prompts mapped to quiz concepts (real PG, stubbed LLM)."""

import os
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.concept import Concept
from app.models.project import Project
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.services.tutor_service import TutorProviderError, plan_quiz


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


def _seed(db, suffix: str):
    user = User(email=f"qplan-{suffix}@example.com", hashed_password=hash_password("supersecret123"))
    db.add(user)
    db.flush()
    space = Space(user_id=user.id, name="S")
    db.add(space)
    db.flush()
    project = Project(space_id=space.id, name="P")
    db.add(project)
    db.flush()
    topic = Topic(project_id=project.id, title="Machine Learning")
    db.add(topic)
    db.flush()
    sub = Subtopic(project_id=project.id, topic_id=topic.id, title="Regression")
    db.add(sub)
    db.flush()
    c1 = Concept(project_id=project.id, subtopic_id=sub.id, title="Linear Regression", summary="Fit a line.")
    c2 = Concept(project_id=project.id, subtopic_id=sub.id, title="Logistic Regression", summary="Sigmoid.")
    db.add_all([c1, c2])
    db.commit()
    return project, c1, c2


def test_plan_maps_questions_and_drops_unknown_ids():
    db = _session()
    try:
        project, c1, c2 = _seed(db, uuid.uuid4().hex[:8])
        stub = StubClient([{
            "concept_ids": [str(c1.id), str(uuid.uuid4()), str(c1.id)],
            "label": "Regression Basics",
        }])
        plan = plan_quiz(db, project_id=project.id, questions=["What is regression?", "Explain fitting."], client=stub)
        assert len(stub.calls) == 1
        assert "Machine Learning" in stub.calls[0][1]  # catalog grounds mapping
        assert plan.concept_ids == (c1.id,)
        assert plan.label == "Regression Basics"
        assert c2.id not in plan.concept_ids
    finally:
        db.close()


def test_plan_guards_never_call_client():
    db = _session()
    try:
        project, c1, _ = _seed(db, uuid.uuid4().hex[:8])
        stub = StubClient([{"concept_ids": [str(c1.id)], "label": "x"}])
        for bad in ([], ["   "], ["q"] * 6, ["x" * 2001]):
            try:
                plan_quiz(db, project_id=project.id, questions=bad, client=stub)
            except ValueError:
                pass
            else:
                raise AssertionError(f"expected ValueError for {bad!r:.30}")
        try:
            plan_quiz(db, project_id=uuid.uuid4(), questions=["q"], client=stub)
        except LookupError:
            pass
        else:
            raise AssertionError("expected LookupError")
        assert stub.calls == []
    finally:
        db.close()


def test_plan_bad_model_output_twice_raises():
    db = _session()
    try:
        project, _, _ = _seed(db, uuid.uuid4().hex[:8])
        bad = {"concept_ids": "not-a-list", "label": 42}
        stub = StubClient([bad, bad])
        try:
            plan_quiz(db, project_id=project.id, questions=["q"], client=stub)
        except TutorProviderError:
            pass
        else:
            raise AssertionError("expected TutorProviderError")
        assert len(stub.calls) == 2
    finally:
        db.close()


def _setup_api():
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


def _teardown_api(engine):
    app.dependency_overrides.clear()
    engine.dispose()
    get_settings.cache_clear()


def test_api_quiz_plan_wiring_and_isolation():
    client, engine = _setup_api()
    try:
        suffix = uuid.uuid4().hex[:8]
        headers = {}
        for who in ("a", "b"):
            email = f"qpapi-{who}-{suffix}@example.com"
            client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
            resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
            headers[who] = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers["a"])
        resp = client.post(f"/api/v1/spaces/{resp.json()['id']}/projects", json={"name": "P"}, headers=headers["a"])
        pid = resp.json()["id"]
        url = f"/api/v1/projects/{pid}/tutor/quiz-plan"
        with patch("app.api.v1.tutor.tutor_service") as svc:
            from app.services.tutor_service import QuizPlan
            cid = uuid.uuid4()
            svc.plan_quiz.return_value = QuizPlan(concept_ids=(cid,), label="Regression")
            resp = client.post(url, json={"questions": ["What is regression?"]}, headers=headers["a"])
            assert resp.status_code == 201 or resp.status_code == 200, resp.text
            body = resp.json()
            assert body["label"] == "Regression" and body["concept_ids"] == [str(cid)]
            assert client.post(url, json={"questions": []}, headers=headers["a"]).status_code == 422
        assert client.post(url, json={"questions": ["q"]}, headers=headers["b"]).status_code == 404
        assert client.post(url, json={"questions": ["q"]}).status_code in (401, 403)
    finally:
        _teardown_api(engine)
