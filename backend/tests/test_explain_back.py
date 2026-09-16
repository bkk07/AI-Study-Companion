"""Phase 40 — Explain-It-Back: graded explanation persisted as append-only evidence (real PG)."""

import os
import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.chunk import DocumentChunk
from app.models.concept import Concept
from app.models.mastery_evidence import MasteryEvidence
from app.models.material import Material
from app.models.project import Project
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.services.explain_it_back_service import submit_explanation
from app.services.open_ended_assessment_service import OpenEndedAssessmentError


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
    user = User(email=f"eib-{suffix}@example.com", hashed_password=hash_password("supersecret123"))
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
    mat = Material(project_id=project.id, filename="d.pdf", storage_path="/tmp/d.pdf", status="ready")
    db.add(mat)
    db.flush()
    db.add(DocumentChunk(project_id=project.id, material_id=mat.id, concept_id=concept.id,
                         chunk_index=0, content="Slope is rise over run in linear equations.",
                         page_number=1, source_name="d.pdf"))
    db.commit()
    return user, project, concept


def _rows(db, **filters):
    return db.query(MasteryEvidence).filter_by(**filters).order_by(MasteryEvidence.created_at.asc()).all()


def test_valid_explanation_persists_evidence():
    db = _session()
    try:
        user, project, concept = _seed(db, uuid.uuid4().hex[:8])
        stub = StubClient([{"score": 85, "feedback": "Clear explanation."}])
        evidence, grade = submit_explanation(db, project_id=project.id, concept_id=concept.id,
                                             user_id=user.id, explanation_text="Slope means rise over run.",
                                             client=stub)
        assert len(stub.calls) == 1
        assert (grade.score, grade.verdict) == (85, "pass")
        assert evidence.evidence_type == "explain_back"
        assert (evidence.user_id, evidence.project_id, evidence.concept_id) == (user.id, project.id, concept.id)
        assert evidence.raw_score == Decimal("85") and evidence.feedback == "Clear explanation."
    finally:
        db.close()


def test_evidence_is_append_only():
    db = _session()
    try:
        user, project, concept = _seed(db, uuid.uuid4().hex[:8])
        stub = StubClient([{"score": 40, "feedback": "Too vague."}, {"score": 75, "feedback": "Better."}])
        first, _ = submit_explanation(db, project_id=project.id, concept_id=concept.id,
                                      user_id=user.id, explanation_text="Something.", client=stub)
        second, grade = submit_explanation(db, project_id=project.id, concept_id=concept.id,
                                           user_id=user.id, explanation_text="Rise over run.", client=stub)
        assert first.id != second.id and grade.verdict == "partial"
        rows = _rows(db, concept_id=concept.id)
        assert [r.raw_score for r in rows] == [Decimal("40"), Decimal("75")]  # both preserved, ordered
    finally:
        db.close()


def test_flaky_then_valid_persists_one_row():
    db = _session()
    try:
        user, project, concept = _seed(db, uuid.uuid4().hex[:8])
        stub = StubClient([{"score": "great", "feedback": "x"}, {"score": 60, "feedback": "OK."}])
        evidence, grade = submit_explanation(db, project_id=project.id, concept_id=concept.id,
                                             user_id=user.id, explanation_text="An explanation.", client=stub)
        assert len(stub.calls) == 2
        assert grade.verdict == "partial"
        assert _rows(db, concept_id=concept.id) == [evidence]
    finally:
        db.close()


def test_bad_twice_rejected_with_no_rows():
    db = _session()
    try:
        user, project, concept = _seed(db, uuid.uuid4().hex[:8])
        bad = {"score": 101, "feedback": "x"}
        stub = StubClient([bad, bad])
        with pytest.raises(OpenEndedAssessmentError):
            submit_explanation(db, project_id=project.id, concept_id=concept.id,
                               user_id=user.id, explanation_text="An explanation.", client=stub)
        assert len(stub.calls) == 2
        assert _rows(db, concept_id=concept.id) == []
    finally:
        db.close()


def test_input_and_scope_guards_never_call_client():
    db = _session()
    try:
        user, project, concept = _seed(db, uuid.uuid4().hex[:8])
        stub = StubClient([{"score": 90, "feedback": "x"}])
        for bad_text in ("", "   ", "x" * 5001):
            with pytest.raises(ValueError):
                submit_explanation(db, project_id=project.id, concept_id=concept.id,
                                   user_id=user.id, explanation_text=bad_text, client=stub)
        with pytest.raises(LookupError):
            submit_explanation(db, project_id=project.id, concept_id=uuid.uuid4(),
                               user_id=user.id, explanation_text="ok", client=stub)
        with pytest.raises(LookupError):
            submit_explanation(db, project_id=uuid.uuid4(), concept_id=concept.id,
                               user_id=user.id, explanation_text="ok", client=stub)
        _, other_project, _ = _seed(db, uuid.uuid4().hex[:8])
        with pytest.raises(LookupError):  # concept from another project
            submit_explanation(db, project_id=other_project.id, concept_id=concept.id,
                               user_id=user.id, explanation_text="ok", client=stub)
        assert stub.calls == []
        assert _rows(db, concept_id=concept.id) == []
    finally:
        db.close()


def test_evidence_type_check_rejects_unknown():
    db = _session()
    try:
        user, project, concept = _seed(db, uuid.uuid4().hex[:8])
        db.add(MasteryEvidence(user_id=user.id, project_id=project.id, concept_id=concept.id,
                               evidence_type="vibes", raw_score=Decimal("50")))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        assert _rows(db, concept_id=concept.id) == []
    finally:
        db.close()


def test_rows_attributed_to_submitting_user():
    db = _session()
    try:
        user, project, concept = _seed(db, uuid.uuid4().hex[:8])
        other = User(email=f"eib2-{uuid.uuid4().hex[:8]}@example.com",
                     hashed_password=hash_password("supersecret123"))
        db.add(other)
        db.commit()
        stub = StubClient([{"score": 70, "feedback": "Fine."}])
        mine, _ = submit_explanation(db, project_id=project.id, concept_id=concept.id,
                                     user_id=user.id, explanation_text="Mine.", client=stub)
        theirs, _ = submit_explanation(db, project_id=project.id, concept_id=concept.id,
                                       user_id=other.id, explanation_text="Theirs.", client=stub)
        assert mine.user_id == user.id and theirs.user_id == other.id
        assert len(_rows(db, concept_id=concept.id)) == 2
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
        email = f"eibapi-{who}-{suffix}@example.com"
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


def test_api_submits_and_maps_errors():
    client, engine = _setup()
    try:
        ids, headers = _users(client, engine)
        url = f"/api/v1/projects/{ids['pid']}/assessment/explain-back"
        body = {"concept_id": ids["cid"], "explanation_text": "Slope is rise over run."}
        fake_evidence = SimpleNamespace(id=uuid.uuid4())
        fake_grade = SimpleNamespace(score=82, verdict="pass", feedback="Solid.")
        with patch("app.api.v1.assessment.explain_it_back_service") as svc:
            svc.submit_explanation.return_value = (fake_evidence, fake_grade)
            resp = client.post(url, json=body, headers=headers["a"])
            assert resp.status_code == 201, resp.text
            assert resp.json() == {"evidence_id": str(fake_evidence.id), "concept_id": ids["cid"],
                                   "score": 82, "verdict": "pass", "feedback": "Solid."}
            svc.submit_explanation.side_effect = OpenEndedAssessmentError("bad output")
            assert client.post(url, json=body, headers=headers["a"]).status_code == 422
            svc.submit_explanation.side_effect = LookupError("nope")
            assert client.post(url, json=body, headers=headers["a"]).status_code == 404
            svc.submit_explanation.side_effect = ValueError("empty")
            assert client.post(url, json=body, headers=headers["a"]).status_code == 400
    finally:
        _teardown(engine)


def test_api_isolation_and_auth():
    client, engine = _setup()
    try:
        ids, headers = _users(client, engine)
        url = f"/api/v1/projects/{ids['pid']}/assessment/explain-back"
        body = {"concept_id": ids["cid"], "explanation_text": "Slope is rise over run."}
        assert client.post(url, json=body, headers=headers["b"]).status_code == 404
        assert client.post(url, json=body).status_code in (401, 403)
        assert client.post(f"/api/v1/projects/{uuid.uuid4()}/assessment/explain-back",
                           json=body, headers=headers["a"]).status_code == 404
        assert client.post(url, json={"concept_id": ids["cid"], "explanation_text": "  "},
                           headers=headers["a"]).status_code == 422  # schema-level empty
    finally:
        _teardown(engine)
