"""Phase 39 — open-ended grading: validated score+feedback, deterministic verdict (real PG)."""

import os
import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.chunk import DocumentChunk
from app.models.concept import Concept
from app.models.material import Material
from app.models.project import Project
from app.models.quiz import Quiz
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.services.open_ended_assessment_service import (
    OpenEndedAssessmentError,
    grade_open_ended,
    verdict_for,
)


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
    user = User(email=f"oea-{suffix}@example.com", hashed_password=hash_password("supersecret123"))
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
        db.add(DocumentChunk(project_id=project.id, material_id=mat.id, concept_id=concept.id,
                             chunk_index=0, content="Slope is rise over run in linear equations.",
                             page_number=1, source_name="d.pdf"))
    db.commit()
    return user, project, concept


def test_pass_partial_fail_verdicts():
    db = _session()
    try:
        _, project, concept = _seed(db, uuid.uuid4().hex[:8])
        for score, verdict in ((92, "pass"), (65, "partial"), (20, "fail")):
            stub = StubClient([{"score": score, "feedback": "Good effort, review slope."}])
            grade = grade_open_ended(db, project_id=project.id, concept_id=concept.id,
                                     answer_text="Slope is rise over run.", client=stub)
            assert len(stub.calls) == 1
            system, user_prompt = stub.calls[0]
            assert "score" in system and "feedback" in system
            assert "Slope is rise over run in linear equations." in user_prompt  # chunks ground grading
            assert "Slope" in user_prompt and "Slope is rise over run." in user_prompt  # concept + answer
            assert (grade.score, grade.verdict, grade.feedback) == (score, verdict, "Good effort, review slope.")
    finally:
        db.close()


def test_verdict_boundaries():
    assert [verdict_for(s) for s in (100, 80, 79, 50, 49, 0)] == ["pass", "pass", "partial", "partial", "fail", "fail"]


def test_flaky_then_valid_grades_once():
    db = _session()
    try:
        _, project, concept = _seed(db, uuid.uuid4().hex[:8])
        stub = StubClient([{"score": "high", "feedback": "x"}, {"score": 81, "feedback": "Solid."}])
        grade = grade_open_ended(db, project_id=project.id, concept_id=concept.id,
                                 answer_text="An answer.", client=stub)
        assert len(stub.calls) == 2
        assert (grade.score, grade.verdict) == (81, "pass")
    finally:
        db.close()


def test_bad_twice_rejected_exactly_two_calls():
    db = _session()
    try:
        _, project, concept = _seed(db, uuid.uuid4().hex[:8])
        bad = {"score": 500, "feedback": "x"}
        stub = StubClient([bad, bad])
        with pytest.raises(OpenEndedAssessmentError):
            grade_open_ended(db, project_id=project.id, concept_id=concept.id,
                             answer_text="An answer.", client=stub)
        assert len(stub.calls) == 2
    finally:
        db.close()


def test_grading_writes_nothing():
    db = _session()
    try:
        _, project, concept = _seed(db, uuid.uuid4().hex[:8])
        stub = StubClient([{"score": 70, "feedback": "Partial."}])
        before = (db.query(Quiz).filter(Quiz.project_id == project.id).count(), concept.summary)
        grade = grade_open_ended(db, project_id=project.id, concept_id=concept.id,
                                   answer_text="An answer.", client=stub)
        db.refresh(concept)
        assert grade.verdict == "partial"
        assert db.query(Quiz).filter(Quiz.project_id == project.id).count() == before[0]
        assert concept.summary == before[1]  # grading never mutates domain rows
    finally:
        db.close()


def test_chunkless_concept_grades_from_summary():
    db = _session()
    try:
        _, project, concept = _seed(db, uuid.uuid4().hex[:8], with_chunks=False)
        stub = StubClient([{"score": 55, "feedback": "On the right track."}])
        grade = grade_open_ended(db, project_id=project.id, concept_id=concept.id,
                                 answer_text="Rise over run?", client=stub)
        assert len(stub.calls) == 1
        assert "Rise over run." in stub.calls[0][1]  # summary anchors grading
        assert grade.verdict == "partial"
    finally:
        db.close()


def test_input_and_scope_guards_never_call_client():
    db = _session()
    try:
        _, project, concept = _seed(db, uuid.uuid4().hex[:8])
        stub = StubClient([{"score": 90, "feedback": "x"}])
        for bad_answer in ("", "   ", "x" * 5001):
            with pytest.raises(ValueError):
                grade_open_ended(db, project_id=project.id, concept_id=concept.id,
                                 answer_text=bad_answer, client=stub)
        with pytest.raises(LookupError):
            grade_open_ended(db, project_id=project.id, concept_id=uuid.uuid4(),
                             answer_text="ok", client=stub)
        with pytest.raises(LookupError):
            grade_open_ended(db, project_id=uuid.uuid4(), concept_id=concept.id,
                             answer_text="ok", client=stub)
        _, other_project, _ = _seed(db, uuid.uuid4().hex[:8])
        with pytest.raises(LookupError):  # concept from another project
            grade_open_ended(db, project_id=other_project.id, concept_id=concept.id,
                             answer_text="ok", client=stub)
        assert stub.calls == []
    finally:
        db.close()


# --- API layer ---


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


def _users(client: TestClient, engine):
    suffix = uuid.uuid4().hex[:8]
    ids = {}
    headers = {}
    for who in ("a", "b"):
        email = f"oeapi-{who}-{suffix}@example.com"
        client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
        resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
        assert resp.status_code == 200, resp.text
        headers[who] = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers["a"])
    assert resp.status_code == 201, resp.text
    resp = client.post(f"/api/v1/spaces/{resp.json()['id']}/projects", json={"name": "P"}, headers=headers["a"])
    assert resp.status_code == 201, resp.text
    ids["pid"] = resp.json()["id"]
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        project = db.get(Project, uuid.UUID(ids["pid"]))
        topic = Topic(project_id=project.id, title="T")
        db.add(topic)
        db.flush()
        sub = Subtopic(project_id=project.id, topic_id=topic.id, title="ST")
        db.add(sub)
        db.flush()
        concept = Concept(project_id=project.id, subtopic_id=sub.id, title="Slope", summary="Rise.")
        db.add(concept)
        db.commit()
        ids["cid"] = str(concept.id)
    finally:
        db.close()
    return ids, headers


def test_api_grades_and_maps_errors():
    client, engine = _setup()
    try:
        ids, headers = _users(client, engine)
        url = f"/api/v1/projects/{ids['pid']}/assessment/open-ended"
        fake = SimpleNamespace(score=88, verdict="pass", feedback="Well explained.")
        with patch("app.api.v1.assessment.open_ended_assessment_service") as svc:
            svc.grade_open_ended.return_value = fake
            resp = client.post(url, json={"concept_id": ids["cid"], "answer_text": "Rise over run."},
                               headers=headers["a"])
            assert resp.status_code == 200, resp.text
            assert resp.json() == {"concept_id": ids["cid"], "score": 88,
                                   "verdict": "pass", "feedback": "Well explained."}
            svc.OpenEndedAssessmentError = OpenEndedAssessmentError
            svc.grade_open_ended.side_effect = OpenEndedAssessmentError("bad output")
            assert client.post(url, json={"concept_id": ids["cid"], "answer_text": "x"},
                               headers=headers["a"]).status_code == 422
            svc.grade_open_ended.side_effect = LookupError("nope")
            assert client.post(url, json={"concept_id": ids["cid"], "answer_text": "x"},
                               headers=headers["a"]).status_code == 404
            svc.grade_open_ended.side_effect = ValueError("empty")
            assert client.post(url, json={"concept_id": ids["cid"], "answer_text": "x"},
                               headers=headers["a"]).status_code == 400
    finally:
        _teardown(engine)


def test_api_isolation_and_auth():
    client, engine = _setup()
    try:
        ids, headers = _users(client, engine)
        url = f"/api/v1/projects/{ids['pid']}/assessment/open-ended"
        body = {"concept_id": ids["cid"], "answer_text": "Rise over run."}
        assert client.post(url, json=body, headers=headers["b"]).status_code == 404
        assert client.post(url, json=body).status_code in (401, 403)
        assert client.post(f"/api/v1/projects/{uuid.uuid4()}/assessment/open-ended",
                           json=body, headers=headers["a"]).status_code == 404
        assert client.post(url, json={"concept_id": ids["cid"], "answer_text": "  "},
                           headers=headers["a"]).status_code == 422  # schema-level empty
    finally:
        _teardown(engine)
