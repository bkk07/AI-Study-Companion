"""Phase C — knowledge tree/search/detail, rollups, quiz CORE-gate + context."""

import os
import uuid

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
from app.models.concept_relationship import ConceptRelationship
from app.models.mastery_evidence import MasteryEvidence
from app.models.material import Material
from app.models.project import Project
from app.models.quiz import Quiz, QuizQuestion
from app.models.quiz_attempt import QuizAnswer, QuizAttempt
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.services.quiz_generation_service import QuizGenerationError, generate_quiz
from app.services.rollup_service import (
    display_mastery,
    rollup_for_project,
    rollup_for_subtopic,
    rollup_for_topic,
)


def _session():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    get_settings.cache_clear()
    return sessionmaker(bind=engine)()


def _scaffold(db, tag):
    user = User(email=f"kn-{tag}@example.com", hashed_password=hash_password("supersecret123"))
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
    return user, project, topic, sub


def _concept(db, project, sub, title, importance="CORE", lo_type="CONCEPT", **over):
    c = Concept(project_id=project.id, subtopic_id=sub.id, title=title,
                summary=f"{title}.", importance=importance, type=lo_type, **over)
    db.add(c)
    db.flush()
    return c


def _evidence(db, user, project, concept, score, etype="mcq"):
    db.add(MasteryEvidence(user_id=user.id, project_id=project.id, concept_id=concept.id,
                           evidence_type=etype, raw_score=score))
    db.flush()


# --- rollups ---------------------------------------------------------------


def test_rollup_practiced_only_mean_and_coverage():
    db = _session()
    try:
        user, project, _, sub = _scaffold(db, uuid.uuid4().hex[:8])
        a = _concept(db, project, sub, "A")
        b = _concept(db, project, sub, "B")
        _concept(db, project, sub, "Fresh")  # unpracticed: excluded, never 0
        _concept(db, project, sub, "Supp", importance="SUPPORTING")
        db.commit()
        _evidence(db, user, project, a, 20)
        _evidence(db, user, project, b, 80)
        db.commit()
        roll = rollup_for_subtopic(db, user_id=user.id, project_id=project.id, subtopic_id=sub.id)
        assert roll.mastery == pytest.approx(50.0)  # mean of practiced only
        assert (roll.practiced, roll.total) == (2, 3)  # supporting out of denominator
    finally:
        db.close()


def test_rollup_null_on_empty_and_obsolete_excluded():
    db = _session()
    try:
        user, project, _, sub = _scaffold(db, uuid.uuid4().hex[:8])
        fresh = _concept(db, project, sub, "Fresh")
        gone = _concept(db, project, sub, "Gone")
        db.commit()
        _evidence(db, user, project, gone, 90)  # evidence on an obsolete row: ignored
        gone.meta = {"status": "obsolete"}
        db.commit()
        roll = rollup_for_subtopic(db, user_id=user.id, project_id=project.id, subtopic_id=sub.id)
        assert roll.mastery is None and (roll.practiced, roll.total) == (0, 1)
        assert fresh.meta == {}
        # topic + project scopes compose on the same rule
        topic = db.query(Topic).filter(Topic.project_id == project.id).one()
        troll = rollup_for_topic(db, user_id=user.id, project_id=project.id, topic_id=topic.id)
        assert troll.mastery is None and (troll.practiced, troll.total) == (0, 1)
        proll = rollup_for_project(db, user_id=user.id, project_id=project.id)
        assert proll.mastery is None and proll.total == 1
    finally:
        db.close()


# --- tree / search / detail APIs --------------------------------------------


def _client():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion")
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    HostSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override():
        db = HostSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app), engine


def _auth_project(client):
    email = f"kn_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
    token = client.post("/api/v1/auth/login",
                        json={"email": email, "password": "supersecret123"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    sid = client.post("/api/v1/spaces", json={"name": "S"}, headers=h).json()["id"]
    pid = client.post(f"/api/v1/spaces/{sid}/projects", json={"name": "P"}, headers=h).json()["id"]
    return email, h, pid


def _seed_tree(engine, email, pid, tag):
    Sess = sessionmaker(bind=engine)
    db = Sess()
    user = db.query(User).filter(User.email == email).one()
    project = db.get(Project, uuid.UUID(pid))
    topic = Topic(project_id=project.id, title=f"Algebra-{tag}")
    db.add(topic)
    db.flush()
    sub = Subtopic(project_id=project.id, topic_id=topic.id, title=f"Linear-{tag}")
    db.add(sub)
    db.flush()
    core = Concept(project_id=project.id, subtopic_id=sub.id, title=f"Slope-{tag}",
                   summary="Rise over run.", importance="CORE", type="CONCEPT",
                   page_start=2, page_end=3)
    supp = Concept(project_id=project.id, subtopic_id=sub.id, title=f"Vocab-{tag}",
                   summary="Background term.", importance="SUPPORTING", type="TERM")
    gone = Concept(project_id=project.id, subtopic_id=sub.id, title=f"Gone-{tag}",
                   summary="Old.", importance="CORE", type="CONCEPT",
                   meta={"status": "obsolete"})
    db.add_all([core, supp, gone])
    db.flush()
    db.add(MasteryEvidence(user_id=user.id, project_id=project.id, concept_id=core.id,
                           evidence_type="mcq", raw_score=40))
    db.commit()
    ids = {"core": str(core.id), "supp": str(supp.id), "gone": str(gone.id)}
    db.close()
    return ids


def test_tree_lists_core_only_with_mastery_coverage():
    client, engine = _client()
    try:
        email, h, pid = _auth_project(client)
        tag = uuid.uuid4().hex[:8]
        _seed_tree(engine, email, pid, tag)
        resp = client.get(f"/api/v1/projects/{pid}/knowledge/tree", headers=h)
        assert resp.status_code == 200, resp.text
        topics = resp.json()["topics"]
        assert len(topics) == 1
        topic = topics[0]
        assert topic["coverage"]["total"] == 1 and topic["coverage"]["practiced"] == 1
        assert topic["coverage"]["mastery"] == pytest.approx(40.0)
        leaves = topic["subtopics"][0]["concepts"]
        assert len(leaves) == 1  # SUPPORTING + obsolete excluded
        assert leaves[0]["title"] == f"Slope-{tag}"
        assert leaves[0]["mastery"] == pytest.approx(40.0)
        overall = resp.json()["overall"]
        assert overall == {"mastery": pytest.approx(40.0), "practiced": 1, "total": 1}
        assert leaves[0]["status"] == "Developing" and leaves[0]["practiced"] is True
        assert leaves[0]["lo_type"] == "CONCEPT"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_search_finds_all_importances_project_scoped():
    client, engine = _client()
    try:
        email_a, h_a, pid_a = _auth_project(client)
        tag = uuid.uuid4().hex[:8]
        _seed_tree(engine, email_a, pid_a, tag)
        _, h_b, pid_b = _auth_project(client)
        resp = client.get(f"/api/v1/projects/{pid_b}/knowledge/search?q=Slope", headers=h_b)
        assert resp.status_code == 200 and resp.json()["hits"] == []  # isolated
        resp = client.get(f"/api/v1/projects/{pid_a}/knowledge/search?q=Slope-{tag}", headers=h_a)
        hits = resp.json()["hits"]
        assert len(hits) == 1 and hits[0]["practicable"] is True
        assert hits[0]["mastery"] == pytest.approx(40.0)
        resp = client.get(f"/api/v1/projects/{pid_a}/knowledge/search?q=Vocab-{tag}", headers=h_a)
        hits = resp.json()["hits"]
        assert len(hits) == 1  # SUPPORTING discoverable
        assert hits[0]["importance"] == "SUPPORTING" and hits[0]["practicable"] is False
        assert hits[0]["mastery"] is None
        resp = client.get(f"/api/v1/projects/{pid_a}/knowledge/search?q=x", headers=h_a)
        assert resp.status_code == 422  # below min length
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_concept_detail_aggregate_and_404():
    client, engine = _client()
    try:
        email, h, pid = _auth_project(client)
        tag = uuid.uuid4().hex[:8]
        ids = _seed_tree(engine, email, pid, tag)
        Sess = sessionmaker(bind=engine)
        db = Sess()
        user = db.query(User).filter(User.email == email).one()
        project = db.get(Project, uuid.UUID(pid))
        core = db.get(Concept, uuid.UUID(ids["core"]))
        supp = db.get(Concept, uuid.UUID(ids["supp"]))
        db.add(ConceptRelationship(from_concept_id=supp.id, to_concept_id=core.id,
                                   relation="PREREQUISITE_OF", created_by="llm",
                                   evidence_span="Vocab underpins Slope."))
        quiz = Quiz(project_id=project.id, mode="practice", question_count=1)
        db.add(quiz)
        db.flush()
        qq = QuizQuestion(quiz_id=quiz.id, concept_id=core.id, question_text="Q?",
                          options=["a", "b"], correct_index=0, difficulty="easy")
        db.add(qq)
        db.flush()
        att = QuizAttempt(quiz_id=quiz.id, user_id=user.id)
        db.add(att)
        db.flush()
        db.add(QuizAnswer(attempt_id=att.id, question_id=qq.id, selected_index=0,
                          is_correct=True, confidence=4))
        db.commit()
        db.close()

        resp = client.get(f"/api/v1/projects/{pid}/knowledge/concepts/{ids['core']}", headers=h)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["title"].startswith("Slope-") and body["lo_type"] == "CONCEPT"
        assert body["mastery"] == pytest.approx(40.0) and body["status"] == "Developing"
        assert body["mcq"] == {"value": 40.0, "count": 1}
        assert body["questions_attempted"] == 1 and body["questions_correct"] == 1
        assert body["last_practiced_at"] is not None
        assert len(body["prerequisites"]) == 1  # supporting row surfaces as prereq
        assert body["page_start"] == 2 and body["page_end"] == 3
        resp = client.get(f"/api/v1/projects/{pid}/knowledge/concepts/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_tree_overall_empty_project_shows_not_started():
    client, engine = _client()
    try:
        _, h, pid = _auth_project(client)
        resp = client.get(f"/api/v1/projects/{pid}/knowledge/tree", headers=h)
        assert resp.status_code == 200, resp.text
        assert resp.json()["overall"] == {"mastery": None, "practiced": 0, "total": 0}
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_dashboard_concept_status_single_sourced():
    client, engine = _client()
    try:
        _, h, pid = _auth_project(client)
        Sess = sessionmaker(bind=engine)
        db = Sess()
        project = db.query(Project).filter(Project.id == uuid.UUID(pid)).one()
        user = db.query(User).join(Space, Space.user_id == User.id).filter(
            Space.id == project.space_id).one()
        topic = Topic(project_id=project.id, title="T")
        db.add(topic)
        db.flush()
        sub = Subtopic(project_id=project.id, topic_id=topic.id, title="ST")
        db.add(sub)
        db.flush()
        weak = Concept(project_id=project.id, subtopic_id=sub.id, title="Weak", summary="w.")
        fresh = Concept(project_id=project.id, subtopic_id=sub.id, title="Fresh", summary="f.")
        db.add_all([weak, fresh])
        db.flush()
        db.add(MasteryEvidence(user_id=user.id, project_id=project.id, concept_id=weak.id,
                               evidence_type="mcq", raw_score=20))
        db.commit()
        db.close()
        resp = client.get(f"/api/v1/projects/{pid}/dashboard", headers=h)
        assert resp.status_code == 200, resp.text
        by_title = {c["title"]: c for c in resp.json()["concepts"]}
        assert by_title["Weak"]["status"] == "Needs Practice"
        assert by_title["Fresh"]["status"] == "Not Started"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


# --- quiz CORE gate + enriched context ---------------------------------------


class _Stub:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def __call__(self, system, user):
        self.calls.append((system, user))
        return self.payloads.pop(0)


_VALID = {"questions": [{"question_text": "Q?", "options": ["a", "b"],
                         "correct_index": 0, "difficulty": "easy"}]}


def test_quiz_rejects_non_core_target():
    db = _session()
    try:
        _, project, _, sub = _scaffold(db, uuid.uuid4().hex[:8])
        supp = _concept(db, project, sub, "Supp", importance="SUPPORTING")
        db.commit()
        with pytest.raises(QuizGenerationError, match="not a practice target"):
            generate_quiz(db, project_id=project.id, concept_id=supp.id,
                          num_questions=1, client=_Stub([_VALID]))
    finally:
        db.close()


def test_quiz_enriched_source_prefers_page_range_and_adds_context():
    db = _session()
    try:
        _, project, _, sub = _scaffold(db, uuid.uuid4().hex[:8])
        mat = Material(project_id=project.id, filename="d.pdf", storage_path="/tmp/d.pdf")
        db.add(mat)
        db.flush()
        core = _concept(db, project, sub, "Target", page_start=2, page_end=2)
        core.material_id = mat.id
        _concept(db, project, sub, "Helper", importance="SUPPORTING")
        for page, text in ((1, "page-one filler"), (2, "page-two gold"), (3, "page-three filler")):
            db.add(DocumentChunk(project_id=project.id, material_id=mat.id, chunk_index=page,
                                 content=text, page_number=page))
        db.commit()
        stub = _Stub([_VALID])
        generate_quiz(db, project_id=project.id, concept_id=core.id,
                      num_questions=1, client=stub)
        _, prompt = stub.calls[0]
        assert "page-two gold" in prompt  # page-range chunk preferred
        assert "page-one filler" not in prompt and "page-three filler" not in prompt
        assert "Helper" in prompt  # supporting context attached
        assert "Target" in prompt and "<<<\n" in prompt
    finally:
        db.close()
