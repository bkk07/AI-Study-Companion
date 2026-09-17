"""Flashcards v1 — deck building, SM-2 review, mastery evidence."""

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.concept import Concept
from app.models.flashcard import Flashcard
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.services import flashcard_service as svc
from app.services.flashcard_service import front_back_for
from app.services.mastery_service import mastery_for_concept


def _session():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    get_settings.cache_clear()
    return sessionmaker(bind=engine)()


def _scaffold(db, tag):
    user = User(email=f"fc-{tag}@example.com", hashed_password=hash_password("supersecret123"))
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


def _concept(db, project, sub, title, lo_type="CONCEPT", importance="CORE"):
    c = Concept(project_id=project.id, subtopic_id=sub.id, title=title,
                summary=f"{title} summary.", type=lo_type, importance=importance)
    db.add(c)
    db.flush()
    return c


# --- fronts -----------------------------------------------------------------


def test_front_back_templates_by_type():
    assert front_back_for("Noun", "TERM", "A word.") == ("Noun", "A word.")
    assert front_back_for("F = ma", "FORMULA", "Force.") == ("F = ma — state the formula", "Force.")
    assert front_back_for("Mitosis", "CONCEPT", "Division.")[0] == "What is Mitosis?"
    assert front_back_for("Pipeline", "PROCESS", "Steps.")[0].startswith("Describe")
    assert front_back_for("Soldering", "SKILL", "Joining.")[0].startswith("How do you")


# --- deck building ------------------------------------------------------------


def test_build_deck_core_only_idempotent():
    db = _session()
    try:
        _, project, topic, sub = _scaffold(db, uuid.uuid4().hex[:8])
        _concept(db, project, sub, "Alpha")
        _concept(db, project, sub, "Beta", lo_type="TERM")
        _concept(db, project, sub, "Gamma", importance="SUPPORTING")
        db.commit()
        first = svc.build_deck(db, project_id=project.id, subtopic_id=sub.id)
        assert first == {"created": 2, "total": 2}
        fronts = {c.front for c in db.query(Flashcard).all()
                  if c.project_id == project.id}
        assert fronts == {"What is Alpha?", "Beta"}
        second = svc.build_deck(db, project_id=project.id, topic_id=topic.id)
        assert second == {"created": 0, "total": 2}  # idempotent across scopes
        with pytest.raises(ValueError):
            svc.build_deck(db, project_id=project.id, subtopic_id=sub.id, topic_id=topic.id)
        with pytest.raises(LookupError):
            svc.build_deck(db, project_id=uuid.uuid4())
        with pytest.raises(LookupError):
            svc.build_deck(db, project_id=project.id, subtopic_id=uuid.uuid4())
    finally:
        db.close()


# --- SM-2 review ----------------------------------------------------------------


def test_sm2_intervals_lapse_and_floor():
    db = _session()
    try:
        user, project, _, sub = _scaffold(db, uuid.uuid4().hex[:8])
        c = _concept(db, project, sub, "Alpha")
        db.commit()
        svc.build_deck(db, project_id=project.id)
        card = db.query(Flashcard).filter(Flashcard.project_id == project.id).one()
        t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        card = svc.review_card(db, project_id=project.id, user_id=user.id,
                               card_id=card.id, grade="good", now=t0)
        assert (card.repetitions, card.interval_days) == (1, 1)
        assert card.next_review_at == t0 + timedelta(days=1)
        card = svc.review_card(db, project_id=project.id, user_id=user.id,
                               card_id=card.id, grade="good", now=t0)
        assert (card.repetitions, card.interval_days) == (2, 6)
        card = svc.review_card(db, project_id=project.id, user_id=user.id,
                               card_id=card.id, grade="easy", now=t0)
        assert card.repetitions == 3 and card.interval_days >= 6
        # lapse resets repetitions, counts a lapse, still reschedules
        card = svc.review_card(db, project_id=project.id, user_id=user.id,
                               card_id=card.id, grade="again", now=t0)
        assert (card.repetitions, card.interval_days, card.lapses) == (0, 1, 1)
        assert card.total_reviews == 4 and card.correct_reviews == 3
        assert float(card.efactor) >= 1.30
    finally:
        db.close()


def test_review_banks_flashcard_evidence_and_moves_applied_mastery():
    db = _session()
    try:
        user, project, _, sub = _scaffold(db, uuid.uuid4().hex[:8])
        c = _concept(db, project, sub, "Alpha")
        db.commit()
        svc.build_deck(db, project_id=project.id)
        card = db.query(Flashcard).filter(Flashcard.project_id == project.id).one()
        svc.review_card(db, project_id=project.id, user_id=user.id,
                        card_id=card.id, grade="good")
        rows = db.query(MasteryEvidence).filter(
            MasteryEvidence.user_id == user.id,
            MasteryEvidence.concept_id == c.id).all()
        assert len(rows) == 1
        assert rows[0].evidence_type == "flashcard" and float(rows[0].raw_score) == 80.0
        scores = mastery_for_concept(db, user_id=user.id, project_id=project.id,
                                     concept_id=c.id)
        assert scores.applied.value == pytest.approx(80.0) and scores.mcq.value is None
        with pytest.raises(ValueError):
            svc.review_card(db, project_id=project.id, user_id=user.id,
                            card_id=card.id, grade="bogus")
        with pytest.raises(LookupError):
            svc.review_card(db, project_id=project.id, user_id=user.id,
                            card_id=uuid.uuid4(), grade="good")
    finally:
        db.close()


def test_due_listing_order_and_counts():
    db = _session()
    try:
        user, project, _, sub = _scaffold(db, uuid.uuid4().hex[:8])
        _concept(db, project, sub, "A")
        _concept(db, project, sub, "B")
        db.commit()
        svc.build_deck(db, project_id=project.id)
        assert svc.count_due(db, project_id=project.id) == 2  # new cards are due
        cards = svc.list_cards(db, project_id=project.id, due_only=True)
        assert len(cards) == 2
        svc.review_card(db, project_id=project.id, user_id=user.id,
                        card_id=cards[0].id, grade="good")
        assert svc.count_due(db, project_id=project.id) == 1
        remaining = svc.list_cards(db, project_id=project.id, due_only=True)
        assert [c.id for c in remaining] == [cards[1].id]
    finally:
        db.close()


# --- API ----------------------------------------------------------------------


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


def test_api_build_list_review_scoped():
    client, engine = _client()
    try:
        email = f"fca_{uuid.uuid4().hex[:8]}@example.com"
        client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
        token = client.post("/api/v1/auth/login",
                            json={"email": email, "password": "supersecret123"}).json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        sid = client.post("/api/v1/spaces", json={"name": "S"}, headers=h).json()["id"]
        pid = client.post(f"/api/v1/spaces/{sid}/projects", json={"name": "P"}, headers=h).json()["id"]

        Sess = sessionmaker(bind=engine)
        db = Sess()
        project = db.get(Project, uuid.UUID(pid))
        topic = Topic(project_id=project.id, title="T")
        db.add(topic)
        db.flush()
        sub = Subtopic(project_id=project.id, topic_id=topic.id, title="ST")
        db.add(sub)
        db.flush()
        db.add(Concept(project_id=project.id, subtopic_id=sub.id, title="Alpha", summary="A."))
        db.commit()
        sub_id = str(sub.id)
        db.close()

        resp = client.post(f"/api/v1/projects/{pid}/flashcards/decks",
                           json={"subtopic_id": sub_id}, headers=h)
        assert resp.status_code == 201, resp.text
        assert resp.json() == {"created": 1, "total": 1}
        resp = client.get(f"/api/v1/projects/{pid}/flashcards?due_only=true", headers=h)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["due_count"] == 1 and len(body["cards"]) == 1
        assert body["cards"][0]["due"] is True
        card_id = body["cards"][0]["id"]
        resp = client.post(f"/api/v1/projects/{pid}/flashcards/{card_id}/review",
                           json={"grade": "easy"}, headers=h)
        assert resp.status_code == 200, resp.text
        assert resp.json()["quality"] == 5 and resp.json()["score"] == 100.0
        assert resp.json()["card"]["repetitions"] == 1
        resp = client.get(f"/api/v1/projects/{pid}/flashcards?due_only=true", headers=h)
        assert resp.json()["due_count"] == 0
        resp = client.post(f"/api/v1/projects/{pid}/flashcards/{uuid.uuid4()}/review",
                           json={"grade": "good"}, headers=h)
        assert resp.status_code == 404
        resp = client.post(f"/api/v1/projects/{pid}/flashcards/{card_id}/review",
                           json={"grade": "maybe"}, headers=h)
        assert resp.status_code == 422  # schema pattern rejects before service
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


# --- explicit concept-list scope -------------------------------------------------


def test_build_deck_concept_ids_list_scope():
    db = _session()
    try:
        _, project, _, sub = _scaffold(db, uuid.uuid4().hex[:8])
        a = _concept(db, project, sub, "Alpha")
        b = _concept(db, project, sub, "Beta")
        _concept(db, project, sub, "Gamma", importance="SUPPORTING")
        db.commit()
        first = svc.build_deck(db, project_id=project.id, concept_ids=[a.id, b.id, a.id])
        assert first == {"created": 2, "total": 2}  # deduped, non-target skipped
        fronts = {c.front for c in db.query(Flashcard).all() if c.project_id == project.id}
        assert fronts == {"What is Alpha?", "What is Beta?"}
        again = svc.build_deck(db, project_id=project.id, concept_ids=[a.id])
        assert again == {"created": 0, "total": 2}  # idempotent
        with pytest.raises(ValueError):
            svc.build_deck(db, project_id=project.id, topic_id=sub.topic_id, concept_ids=[a.id])
        with pytest.raises(LookupError):
            svc.build_deck(db, project_id=project.id, concept_ids=[uuid.uuid4()])
        with pytest.raises(ValueError):
            svc.build_deck(db, project_id=project.id, concept_id=a.id, concept_ids=[a.id])
    finally:
        db.close()


def test_list_cards_concept_ids_filter():
    db = _session()
    try:
        _, project, _, sub = _scaffold(db, uuid.uuid4().hex[:8])
        a = _concept(db, project, sub, "Alpha")
        b = _concept(db, project, sub, "Beta")
        db.commit()
        svc.build_deck(db, project_id=project.id, concept_ids=[a.id, b.id])
        got = svc.list_cards(db, project_id=project.id, concept_ids=[b.id])
        assert [c.concept_id for c in got] == [b.id]
        with pytest.raises(LookupError):
            svc.list_cards(db, project_id=project.id, concept_ids=[uuid.uuid4()])
        with pytest.raises(ValueError):
            svc.list_cards(db, project_id=project.id, concept_id=a.id, concept_ids=[a.id])
    finally:
        db.close()
