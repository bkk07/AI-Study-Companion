"""Tutor -> Mastery Evidence closure: graded tutor check banks `tutor` evidence (real PG).

Production path: grounded tutor answer (persisted) -> student explanation ->
shared open-ended grade -> mastery_service.record_tutor_evidence -> mastery
engine. Plain chat (send_message) stays evidence-free; ONLY the explicit
graded check writes. Covers the six required behaviors plus Flow A
(Tutor -> response -> evidence -> mastery).
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.concept import Concept
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.tutor_conversation import TutorConversation, TutorMessage
from app.models.user import User
from app.services import tutor_conversation_service as tcs
from app.services.mastery_service import mastery_for_concept
from app.services.tutor_service import TutorAskResponse


def _session():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    get_settings.cache_clear()
    return sessionmaker(bind=engine)()


def _scaffold(db, tag, n_concepts=1):
    user = User(email=f"te-{tag}@example.com", hashed_password=hash_password("supersecret123"))
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
        c = Concept(project_id=project.id, subtopic_id=sub.id, title=f"C{i}-{tag}", summary="Slope is rise over run.")
        db.add(c)
        db.flush()
        concepts.append(c)
    db.commit()
    return user, project, concepts


def _grounded_exchange(db, user, project, question="What is slope?"):
    """Persist one grounded Q&A pair; returns (convo, assistant_msg)."""
    convo = tcs.create_conversation(db, project=project, user=user)

    def _fake_ask(db_, *, project_id, question, concept_id=None):
        return TutorAskResponse(
            answer="Slope is rise over run.",
            supported=True,
            citations=[],
            follow_ups=[],
        )

    with patch("app.services.tutor_service.ask_question", _fake_ask):
        _, assistant_msg, _ = tcs.send_message(db, convo=convo, question=question)
    # Simulate retrieval grounding: a cited answer (gate requires citations).
    assistant_msg.citations = [{"chunk_id": str(uuid.uuid4()), "material_id": str(uuid.uuid4())}]
    assistant_msg.supported = True
    db.commit()
    db.refresh(assistant_msg)
    return convo, assistant_msg


def _grade_payload(score=85):
    return {
        "score": score,
        "feedback": "Solid explanation.",
        "strengths": ["definition"],
        "missing_points": [],
        "suggestions": [],
    }


class _StubClient:
    def __init__(self, payload):
        self.payload = payload

    def __call__(self, system, user):
        return dict(self.payload)


# --- 1. tutor interaction creates tutor evidence, correctly attributed --------

def test_tutor_check_banks_evidence_with_correct_attribution():
    db = _session()
    try:
        user, project, (concept,) = _scaffold(db, uuid.uuid4().hex[:8])
        convo, assistant_msg = _grounded_exchange(db, user, project)
        evidence, grade = tcs.submit_tutor_check(
            db, convo=convo, assistant_message_id=assistant_msg.id,
            concept_id=concept.id,
            explanation_text="Slope is rise over run; steeper means bigger slope.",
            client=_StubClient(_grade_payload(85)),
        )
        assert evidence.evidence_type == "tutor" and evidence.source == "tutor"
        assert float(evidence.raw_score) == pytest.approx(85.0)
        assert evidence.user_id == user.id
        assert evidence.project_id == project.id
        assert evidence.concept_id == concept.id
        assert grade.score == 85
    finally:
        db.close()


def test_flow_a_evidence_feeds_mastery():
    """Flow A: Tutor -> response -> evidence -> mastery (tutor stream moves)."""
    db = _session()
    try:
        user, project, (concept,) = _scaffold(db, uuid.uuid4().hex[:8])
        assert mastery_for_concept(db, user_id=user.id, project_id=project.id,
                                   concept_id=concept.id).final is None
        convo, assistant_msg = _grounded_exchange(db, user, project)
        tcs.submit_tutor_check(
            db, convo=convo, assistant_message_id=assistant_msg.id,
            concept_id=concept.id, explanation_text="Slope is rise over run, explained in my own words here.",
            client=_StubClient(_grade_payload(90)),
        )
        scores = mastery_for_concept(db, user_id=user.id, project_id=project.id, concept_id=concept.id)
        assert scores.tutor.value == pytest.approx(90.0)
        assert scores.tutor.count == 1
        assert scores.final is not None
    finally:
        db.close()


# --- 3. append-only ------------------------------------------------------------

def test_tutor_evidence_append_only_and_daily_cap():
    db = _session()
    try:
        user, project, (concept,) = _scaffold(db, uuid.uuid4().hex[:8])
        convo, assistant_msg = _grounded_exchange(db, user, project)
        before = db.query(MasteryEvidence).filter(
            MasteryEvidence.user_id == user.id, MasteryEvidence.concept_id == concept.id).all()
        assert before == []
        tcs.submit_tutor_check(
            db, convo=convo, assistant_message_id=assistant_msg.id,
            concept_id=concept.id, explanation_text="First explanation with enough words here.",
            client=_StubClient(_grade_payload(70)),
        )
        first_id = db.query(MasteryEvidence).filter(
            MasteryEvidence.concept_id == concept.id).one().id
        # Same UTC day: writer rejects (no second row, first untouched).
        with pytest.raises(ValueError, match="at most 1 tutor evidence per day"):
            tcs.submit_tutor_check(
                db, convo=convo, assistant_message_id=assistant_msg.id,
                concept_id=concept.id, explanation_text="Second explanation same day here.",
                client=_StubClient(_grade_payload(95)),
            )
        rows = db.query(MasteryEvidence).filter(MasteryEvidence.concept_id == concept.id).all()
        assert len(rows) == 1 and rows[0].id == first_id
        assert float(rows[0].raw_score) == pytest.approx(70.0)  # history never mutated
    finally:
        db.close()


# --- 4. authorization ----------------------------------------------------------

def test_tutor_check_respects_project_isolation():
    db = _session()
    try:
        user, project, (concept,) = _scaffold(db, uuid.uuid4().hex[:8])
        other_user, other_project, (other_concept,) = _scaffold(db, uuid.uuid4().hex[:8])
        convo, assistant_msg = _grounded_exchange(db, user, project)
        # Foreign concept (other project) rejected.
        with pytest.raises(LookupError):
            tcs.submit_tutor_check(
                db, convo=convo, assistant_message_id=assistant_msg.id,
                concept_id=other_concept.id, explanation_text="Explanation with enough words here.",
                client=_StubClient(_grade_payload(80)),
            )
        # Foreign assistant message rejected.
        other_convo, other_msg = _grounded_exchange(db, other_user, other_project)
        with pytest.raises(LookupError):
            tcs.submit_tutor_check(
                db, convo=convo, assistant_message_id=other_msg.id,
                concept_id=concept.id, explanation_text="Explanation with enough words here.",
                client=_StubClient(_grade_payload(80)),
            )
        assert db.query(MasteryEvidence).filter(MasteryEvidence.user_id == user.id).count() == 0
        # Unknown concept rejected.
        with pytest.raises(LookupError):
            tcs.submit_tutor_check(
                db, convo=convo, assistant_message_id=assistant_msg.id,
                concept_id=uuid.uuid4(), explanation_text="Explanation with enough words here.",
                client=_StubClient(_grade_payload(80)),
            )
    finally:
        db.close()


# --- 5. failure creates no invalid evidence ------------------------------------

def test_tutor_failure_creates_no_evidence():
    db = _session()
    try:
        user, project, (concept,) = _scaffold(db, uuid.uuid4().hex[:8])
        convo = tcs.create_conversation(db, project=project, user=user)
        # Unsupported answer (no citations) cannot seed a check.
        user_msg = TutorMessage(conversation_id=convo.id, role="user", content="Quantum?")
        db.add(user_msg)
        db.flush()
        unsupported = TutorMessage(
            conversation_id=convo.id, role="assistant", content="Not covered.",
            supported=False, citations=[], follow_ups=[],
        )
        db.add(unsupported)
        db.commit()
        with pytest.raises(ValueError, match="grounded answer"):
            tcs.submit_tutor_check(
                db, convo=convo, assistant_message_id=unsupported.id,
                concept_id=concept.id, explanation_text="Some explanation with words here.",
                client=_StubClient(_grade_payload(80)),
            )
        # Greeting-style cited-less answer likewise rejected.
        bare = TutorMessage(
            conversation_id=convo.id, role="assistant", content="Hello!",
            supported=True, citations=[], follow_ups=[],
        )
        db.add(bare)
        db.commit()
        with pytest.raises(ValueError, match="grounded answer"):
            tcs.submit_tutor_check(
                db, convo=convo, assistant_message_id=bare.id,
                concept_id=concept.id, explanation_text="Some explanation with words here.",
                client=_StubClient(_grade_payload(80)),
            )
        # Grading failure persists nothing.
        _, grounded = _grounded_exchange(db, user, project, question="What is intercept?")
        convo2 = db.get(TutorConversation, grounded.conversation_id)

        class _Failing:
            def __call__(self, system, user):
                raise ValueError("bad payload")

        with pytest.raises(Exception):
            tcs.submit_tutor_check(
                db, convo=convo2, assistant_message_id=grounded.id,
                concept_id=concept.id, explanation_text="Explanation with enough words here.",
                client=_Failing(),
            )
        assert db.query(MasteryEvidence).filter(MasteryEvidence.user_id == user.id).count() == 0
        # Empty explanation rejected before any write.
        with pytest.raises(ValueError):
            tcs.submit_tutor_check(
                db, convo=convo2, assistant_message_id=grounded.id,
                concept_id=concept.id, explanation_text="   ",
                client=_StubClient(_grade_payload(80)),
            )
    finally:
        db.close()


# --- 6. existing tutor behavior intact ------------------------------------------

def test_plain_chat_still_writes_no_evidence():
    db = _session()
    try:
        user, project, (concept,) = _scaffold(db, uuid.uuid4().hex[:8])
        convo = tcs.create_conversation(db, project=project, user=user)

        def _fake_ask(db_, *, project_id, question, concept_id=None):
            return TutorAskResponse(answer="Slope is rise over run.", supported=True,
                                    citations=[], follow_ups=[])

        with patch("app.services.tutor_service.ask_question", _fake_ask):
            tcs.send_message(db, convo=convo, question="What is slope?")
            tcs.send_message(db, convo=convo, question="And intercept?")
        assert db.query(MasteryEvidence).filter(
            MasteryEvidence.user_id == user.id,
            MasteryEvidence.project_id == project.id).count() == 0
        assert mastery_for_concept(db, user_id=user.id, project_id=project.id,
                                   concept_id=concept.id).final is None
    finally:
        db.close()


# --- API: production caller -----------------------------------------------------

def _api_setup():
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


def _api_teardown(engine):
    app.dependency_overrides.clear()
    engine.dispose()
    get_settings.cache_clear()


def _register_login(client, email):
    client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_api_check_endpoint_end_to_end_and_isolation():
    from app.schemas.rag import RagChunk, RagContext

    client, engine = _api_setup()
    try:
        suffix = uuid.uuid4().hex[:8]
        ha = _register_login(client, f"teapi-a-{suffix}@example.com")
        hb = _register_login(client, f"teapi-b-{suffix}@example.com")
        resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=ha)
        pid = client.post(f"/api/v1/spaces/{resp.json()['id']}/projects",
                          json={"name": "P"}, headers=ha).json()["id"]
        Sess = sessionmaker(bind=engine)
        db = Sess()
        try:
            from app.models.user import User as U
            me = db.query(U).filter(U.email == f"teapi-a-{suffix}@example.com").one()
            project = db.get(Project, uuid.UUID(pid))
            topic = Topic(project_id=project.id, title="T")
            db.add(topic)
            db.flush()
            sub = Subtopic(project_id=project.id, topic_id=topic.id, title="ST")
            db.add(sub)
            db.flush()
            concept = Concept(project_id=project.id, subtopic_id=sub.id, title="Slope",
                              summary="Slope is rise over run.")
            db.add(concept)
            db.commit()
            cid = str(concept.id)
        finally:
            db.close()

        base = f"/api/v1/projects/{pid}/tutor"
        cid_convo = client.post(f"{base}/conversations", json={}, headers=ha).json()["id"]
        chunk = RagChunk(chunk_id=uuid.uuid4(), material_id=uuid.uuid4(), content="Slope is rise over run.",
                         page_number=1, source_name="doc.pdf", chunk_index=0, score=0.05)
        ctx = RagContext(query="What is slope?", scope_project_id=uuid.UUID(pid),
                         chunks=[chunk], total_chars=24, truncated=False)
        with (
            patch("app.services.tutor_service.rag_service") as rag,
            patch("app.services.tutor_service.groq_client") as groq,
        ):
            rag.assemble_context.return_value = ctx
            groq.chat_json.return_value = {"answer": "Slope is rise over run.", "follow_ups": []}
            msg = client.post(f"{base}/conversations/{cid_convo}/messages",
                              json={"question": "What is slope?"}, headers=ha)
        assert msg.status_code == 200, msg.text
        assistant_id = msg.json()["assistant_message_id"]
        assert msg.json()["citations"]  # grounded prerequisite

        with patch("app.services.open_ended_assessment_service.groq_client") as grade_groq:
            grade_groq.chat_json.return_value = _grade_payload(82)
            check = client.post(
                f"{base}/conversations/{cid_convo}/checks",
                json={"assistant_message_id": assistant_id, "concept_id": cid,
                      "explanation_text": "Slope is rise over run; steeper lines have bigger slope values."},
                headers=ha,
            )
        assert check.status_code == 201, check.text
        body = check.json()
        assert body["concept_id"] == cid and body["score"] == 82

        # Mastery now reflects the tutor stream (Flow A through the real API).
        Sess2 = sessionmaker(bind=engine)
        db2 = Sess2()
        try:
            from app.models.user import User as U2
            me2 = db2.query(U2).filter(U2.email == f"teapi-a-{suffix}@example.com").one()
            rows = db2.query(MasteryEvidence).filter(
                MasteryEvidence.user_id == me2.id,
                MasteryEvidence.concept_id == uuid.UUID(cid)).all()
            assert len(rows) == 1 and rows[0].evidence_type == "tutor"
        finally:
            db2.close()

        # Isolation: other user cannot use this thread; bad concept 404s.
        assert client.post(f"{base}/conversations/{cid_convo}/checks",
                           json={"assistant_message_id": assistant_id, "concept_id": cid,
                                 "explanation_text": "Enough words in this explanation here."},
                           headers=hb).status_code == 404
        with patch("app.services.open_ended_assessment_service.groq_client") as grade_groq:
            grade_groq.chat_json.return_value = _grade_payload(82)
            assert client.post(f"{base}/conversations/{cid_convo}/checks",
                               json={"assistant_message_id": assistant_id,
                                     "concept_id": str(uuid.uuid4()),
                                     "explanation_text": "Enough words in this explanation here."},
                               headers=ha).status_code == 404
            # Empty explanation rejected, provider-shaped 400.
            assert client.post(f"{base}/conversations/{cid_convo}/checks",
                               json={"assistant_message_id": assistant_id, "concept_id": cid,
                                     "explanation_text": "   "},
                               headers=ha).status_code in (400, 422)
    finally:
        _api_teardown(engine)
