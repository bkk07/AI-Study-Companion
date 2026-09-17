"""Mastery Plan A — five activity streams with weighted final (user-confirmed 2026-09-17).

Streams and weights: quiz 0.35 / open_ended 0.25 / practice 0.20 /
flashcard 0.15 / tutor 0.05. Missing streams renormalize (never zero).
Tutor-only finals cap at 40. Legacy rows (source NULL) route by
evidence_type so pre-Plan-A history is preserved verbatim.
"""

import dataclasses
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.concept import Concept
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project
from app.models.quiz import Quiz, QuizQuestion
from app.models.space import Space
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.models.user import User
from app.services import quiz_attempt_service
from app.services.mastery_levels import status_for
from app.services.mastery_service import (
    EVIDENCE_LOW,
    EVIDENCE_NONE,
    EVIDENCE_OK,
    FORMATIVE_ONLY_CAP,
    STREAM_WEIGHTS,
    TUTOR_ONLY_CAP,
    TUTOR_WEIGHT,
    EvidenceInput,
    compute_final,
    compute_mastery,
    mastery_for_concept,
    record_tutor_evidence,
    stream_for,
)
from app.services.mismatch_service import ConceptState, detect_mismatches

T0 = datetime(2026, 2, 1, tzinfo=timezone.utc)


def _pt(score, source, etype="mcq", at=None, difficulty=None):
    return EvidenceInput(evidence_type=etype, score=score, difficulty=difficulty, at=at, source=source)


# --- stream isolation -------------------------------------------------------

def test_quiz_evidence_updates_only_quiz_mastery():
    scores = compute_mastery([_pt(80, "quiz"), _pt(100, "quiz", difficulty="hard")])
    assert scores.quiz.value == pytest.approx(80 + 0.4 * 20)
    assert scores.quiz.count == 2
    for stream in (scores.open_ended, scores.practice, scores.flashcard, scores.tutor):
        assert stream.value is None and stream.count == 0


def test_practice_evidence_updates_only_practice_mastery():
    scores = compute_mastery([_pt(60, "practice"), _pt(80, "practice", difficulty="easy")])
    assert scores.practice.value == pytest.approx(60 + 0.2 * 20)
    assert scores.quiz.value is None and scores.open_ended.value is None
    assert scores.flashcard.value is None and scores.tutor.value is None


def test_open_ended_evidence_updates_only_open_ended_mastery():
    scores = compute_mastery([
        _pt(20, "open_ended", etype="open_ended"),
        _pt(30, "open_ended", etype="explain_back"),
    ])
    assert scores.open_ended.value == pytest.approx(20 + 0.3 * 10)
    assert scores.open_ended.count == 2
    assert scores.quiz.value is None and scores.practice.value is None
    assert scores.flashcard.value is None and scores.tutor.value is None


def test_flashcard_evidence_updates_only_flashcard_mastery():
    scores = compute_mastery([_pt(80, "flashcard", etype="flashcard")])
    assert scores.flashcard.value == pytest.approx(80.0)
    assert scores.quiz.value is None and scores.practice.value is None
    assert scores.open_ended.value is None and scores.tutor.value is None


def test_tutor_evidence_updates_only_tutor_mastery():
    scores = compute_mastery([_pt(100, "tutor", etype="tutor")])
    assert scores.tutor.value == pytest.approx(100.0)
    assert scores.quiz.value is None and scores.practice.value is None
    assert scores.open_ended.value is None and scores.flashcard.value is None


# --- final mastery ----------------------------------------------------------

def test_weighted_final_renormalizes_missing_streams():
    # Spec example: Quiz=80, Practice=60, Tutor=100, others missing.
    scores = compute_mastery([_pt(80, "quiz"), _pt(60, "practice"), _pt(100, "tutor", etype="tutor")])
    assert scores.final == pytest.approx((0.35 * 80 + 0.20 * 60 + 0.05 * 100) / 0.60)


def test_single_stream_final_equals_stream_value():
    # thin evidence caps the headline final (streams keep raw values)
    assert compute_mastery([_pt(73, "quiz")]).final == pytest.approx(60.0)
    assert compute_mastery([_pt(42, "practice")]).final == pytest.approx(42.0)
    assert compute_mastery([_pt(73, "quiz"), _pt(73, "quiz")]).final == pytest.approx(73.0)
    assert compute_mastery([_pt(73, "quiz"), _pt(73, "quiz"), _pt(73, "quiz")]).final == pytest.approx(73.0)


def test_all_five_streams_weighted():
    scores = compute_mastery([
        _pt(100, "quiz"), _pt(100, "open_ended", etype="open_ended"),
        _pt(100, "practice"), _pt(100, "flashcard", etype="flashcard"),
        _pt(0, "tutor", etype="tutor"),
    ])
    assert scores.final == pytest.approx(0.35 * 100 + 0.25 * 100 + 0.20 * 100 + 0.15 * 100 + 0.05 * 0)
    assert sum(STREAM_WEIGHTS.values()) == pytest.approx(1.0)


def test_tutor_only_mastery_capped_at_40():
    assert compute_mastery([_pt(100, "tutor", etype="tutor")]).final == pytest.approx(TUTOR_ONLY_CAP)
    assert TUTOR_ONLY_CAP == pytest.approx(40.0)
    low = compute_mastery([_pt(30, "tutor", etype="tutor")])
    assert low.final == pytest.approx(30.0)  # below the cap: untouched


def test_empty_is_none_and_confidence_flags():
    bare = compute_mastery([])
    assert bare.final is None
    assert bare.total_count == 0 and bare.evidence_confidence == EVIDENCE_NONE
    assert status_for(bare.final) == "Not Started"
    assert compute_mastery([_pt(80, "quiz")]).evidence_confidence == EVIDENCE_LOW  # 1 row
    assert compute_mastery([_pt(80, "quiz"), _pt(70, "quiz")]).evidence_confidence == EVIDENCE_LOW  # 2 rows
    full = compute_mastery([_pt(80, "quiz"), _pt(70, "quiz"), _pt(60, "quiz")])
    assert full.evidence_confidence == EVIDENCE_OK and full.total_count == 3


def test_compute_final_unit_edges():
    from app.services.mastery_service import StreamMastery

    assert compute_final({}) is None
    assert compute_final({"quiz": StreamMastery(value=None)}) is None


# --- tutor EMA special-casing ------------------------------------------------

def test_tutor_uses_fixed_weight_regardless_of_difficulty():
    scores = compute_mastery([
        _pt(0, "tutor", etype="tutor", difficulty="hard"),
        _pt(100, "tutor", etype="tutor", difficulty="hard"),
    ])
    assert TUTOR_WEIGHT == pytest.approx(0.15)
    assert scores.tutor.value == pytest.approx(0 + 0.15 * 100)
    third = compute_mastery([
        _pt(0, "tutor", etype="tutor"),
        _pt(100, "tutor", etype="tutor"),
        _pt(100, "tutor", etype="tutor"),
    ])
    assert third.tutor.value == pytest.approx(15 + 0.15 * 85)


def test_tutor_same_day_points_dedupe_to_latest():
    day = T0
    scores = compute_mastery([
        _pt(20, "tutor", etype="tutor", at=day),
        _pt(80, "tutor", etype="tutor", at=day + timedelta(hours=5)),
    ])
    assert scores.tutor.count == 1
    assert scores.tutor.value == pytest.approx(80.0)  # latest of the day wins
    across = compute_mastery([
        _pt(20, "tutor", etype="tutor", at=day),
        _pt(80, "tutor", etype="tutor", at=day + timedelta(days=1)),
    ])
    assert across.tutor.count == 2
    assert across.tutor.value == pytest.approx(20 + 0.15 * 60)


# --- backward compatibility --------------------------------------------------

def test_legacy_mcq_routes_to_quiz_with_identical_values():
    legacy = compute_mastery([
        EvidenceInput(evidence_type="mcq", score=50),
        EvidenceInput(evidence_type="mcq", score=100, difficulty="medium"),
    ])
    assert legacy.quiz.value == pytest.approx(50 + 0.3 * 50)
    assert legacy.quiz.count == 2
    assert legacy.mcq.value == pytest.approx(legacy.quiz.value)  # aggregate replays legacy formula
    assert legacy.practice.value is None


def test_legacy_explain_back_and_flashcard_routing():
    legacy = compute_mastery([
        EvidenceInput(evidence_type="explain_back", score=40),
        EvidenceInput(evidence_type="explain_back", score=80),
    ])
    assert legacy.open_ended.value == pytest.approx(40 + 0.3 * 40)
    assert legacy.applied.value == pytest.approx(legacy.open_ended.value)
    flash = compute_mastery([EvidenceInput(evidence_type="flashcard", score=80)])
    assert flash.flashcard.value == pytest.approx(80.0)
    assert flash.applied.value == pytest.approx(80.0) and flash.mcq.value is None


def test_stream_for_explicit_source_wins_and_rejects_bad_input():
    assert stream_for("mcq", "practice") == "practice"
    assert stream_for("explain_back", "open_ended") == "open_ended"
    assert stream_for("mcq", None) == "quiz"
    assert stream_for("open_ended", None) == "open_ended"
    assert stream_for("explain_back", None) == "open_ended"
    assert stream_for("flashcard", None) == "flashcard"
    with pytest.raises(ValueError):
        stream_for("mcq", "vibes")
    with pytest.raises(ValueError):
        EvidenceInput(evidence_type="mcq", score=50, source="vibes")
    with pytest.raises(ValueError):
        EvidenceInput(evidence_type="vibes", score=50)


# --- levels / confidence / mismatch ------------------------------------------

def test_mastery_levels_unchanged():
    assert status_for(None) == "Not Started"
    assert status_for(0) == "Needs Practice" and status_for(33.9) == "Needs Practice"
    assert status_for(34) == "Developing" and status_for(66) == "Developing"
    assert status_for(67) == "Strong" and status_for(84.9) == "Strong"
    assert status_for(85) == "Mastered" and status_for(100) == "Mastered"


def test_confidence_structurally_excluded():
    assert "confidence" not in {f.name for f in dataclasses.fields(EvidenceInput)}
    assert compute_mastery([_pt(40, "quiz"), _pt(80, "quiz")]) == compute_mastery(
        [_pt(40, "quiz"), _pt(80, "quiz")])


def test_mismatch_legacy_rule_still_fires():
    state = ConceptState(concept_id=uuid.uuid4(), mcq_mastery=92.0, applied_mastery=54.0,
                         mcq_count=5, applied_count=2)
    found = detect_mismatches([state])
    assert len(found) == 1 and found[0].mismatch_type == "mcq_high_applied_low"


def test_mismatch_quiz_high_open_low_rule():
    state = ConceptState(
        concept_id=uuid.uuid4(),
        mcq_mastery=55.0, applied_mastery=50.0, mcq_count=5, applied_count=2,  # legacy rule: no flag
        quiz_mastery=90.0, open_ended_mastery=40.0, quiz_count=3, open_ended_count=1,
    )
    found = detect_mismatches([state])
    assert len(found) == 1 and found[0].mismatch_type == "mcq_high_applied_low"
    assert "90.0" in found[0].reason and "40.0" in found[0].reason
    thin = ConceptState(
        concept_id=uuid.uuid4(), mcq_mastery=90.0, applied_mastery=40.0,
        mcq_count=5, applied_count=2,
        quiz_mastery=90.0, open_ended_mastery=40.0, quiz_count=2, open_ended_count=1,  # thin quiz
    )
    # Legacy aggregate rule still fires (quiz evidence joins the mcq aggregate).
    assert detect_mismatches([thin])[0].mismatch_type == "mcq_high_applied_low"
    thin_both = ConceptState(
        concept_id=uuid.uuid4(), mcq_mastery=None, applied_mastery=None,
        quiz_mastery=90.0, open_ended_mastery=40.0, quiz_count=2, open_ended_count=1,
    )
    assert detect_mismatches([thin_both]) == []  # thin quiz stream data never flags


def test_normal_tutor_chat_code_cannot_write_evidence():
    import pathlib

    path = pathlib.Path("app/services/tutor_conversation_service.py")
    text = path.read_text()
    assert "MasteryEvidence" not in text
    assert "record_tutor_evidence" not in text


# --- DB-backed behavior ------------------------------------------------------

def _session():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    get_settings.cache_clear()
    return sessionmaker(bind=engine)()


def _scaffold(db, tag, n_concepts=1):
    user = User(email=f"pa-{tag}@example.com", hashed_password=hash_password("supersecret123"))
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
        c = Concept(project_id=project.id, subtopic_id=sub.id, title=f"C{i}-{tag}", summary="S.")
        db.add(c)
        db.flush()
        concepts.append(c)
    db.commit()
    return user, project, concepts


def test_record_tutor_evidence_enforces_one_per_day():
    db = _session()
    try:
        user, project, (concept,) = _scaffold(db, uuid.uuid4().hex[:8])
        row = record_tutor_evidence(db, user_id=user.id, project_id=project.id,
                                    concept_id=concept.id, score=80, feedback="Good.")
        assert row.evidence_type == "tutor" and row.source == "tutor"
        with pytest.raises(ValueError, match="at most 1 tutor evidence per day"):
            record_tutor_evidence(db, user_id=user.id, project_id=project.id,
                                  concept_id=concept.id, score=90)
        # A later UTC day is a new budget.
        record_tutor_evidence(db, user_id=user.id, project_id=project.id,
                              concept_id=concept.id, score=90,
                              now=datetime.now(timezone.utc) + timedelta(days=1))
        scores = mastery_for_concept(db, user_id=user.id, project_id=project.id,
                                     concept_id=concept.id)
        assert scores.tutor.count == 1  # same-day DB rows collapse in the stream
        assert scores.final == pytest.approx(min(scores.tutor.value, 40.0))
    finally:
        db.close()


def test_record_tutor_evidence_guards():
    db = _session()
    try:
        user, project, (concept,) = _scaffold(db, uuid.uuid4().hex[:8])
        for bad in (-1, 101, True):
            with pytest.raises(ValueError):
                record_tutor_evidence(db, user_id=user.id, project_id=project.id,
                                      concept_id=concept.id, score=bad)
        with pytest.raises(LookupError):
            record_tutor_evidence(db, user_id=user.id, project_id=project.id,
                                  concept_id=uuid.uuid4(), score=50)
    finally:
        db.close()


def _quiz_with_questions(db, project, concepts, mode):
    quiz = Quiz(project_id=project.id, mode=mode, question_count=len(concepts))
    db.add(quiz)
    db.flush()
    questions = []
    for i, c in enumerate(concepts):
        q = QuizQuestion(quiz_id=quiz.id, concept_id=c.id, question_text=f"Q{i}?",
                         options=["a", "b"], correct_index=0, difficulty="easy")
        db.add(q)
        db.flush()
        questions.append(q)
    db.commit()
    return quiz, questions


def test_quiz_mode_routes_practice_vs_quiz_streams():
    db = _session()
    try:
        user, project, concepts = _scaffold(db, uuid.uuid4().hex[:8], n_concepts=2)
        exam, exam_qs = _quiz_with_questions(db, project, [concepts[0]], "exam")
        attempt = quiz_attempt_service.start_attempt(db, quiz_id=exam.id, project_id=project.id,
                                                     user_id=user.id)
        quiz_attempt_service.submit_answer(db, attempt_id=attempt.id, project_id=project.id,
                                           user_id=user.id, question_id=exam_qs[0].id,
                                           selected_index=0, confidence=4)
        quiz_attempt_service.complete_attempt(db, attempt_id=attempt.id, project_id=project.id,
                                              user_id=user.id)
        practice, prac_qs = _quiz_with_questions(db, project, [concepts[1]], "practice")
        attempt2 = quiz_attempt_service.start_attempt(db, quiz_id=practice.id, project_id=project.id,
                                                      user_id=user.id)
        quiz_attempt_service.submit_answer(db, attempt_id=attempt2.id, project_id=project.id,
                                           user_id=user.id, question_id=prac_qs[0].id,
                                           selected_index=0, confidence=4)
        quiz_attempt_service.complete_attempt(db, attempt_id=attempt2.id, project_id=project.id,
                                              user_id=user.id)
        rows = db.query(MasteryEvidence).filter(
            MasteryEvidence.user_id == user.id,
            MasteryEvidence.project_id == project.id).all()
        by_concept = {r.concept_id: r.source for r in rows}
        assert by_concept[concepts[0].id] == "quiz"
        assert by_concept[concepts[1].id] == "practice"
        exam_scores = mastery_for_concept(db, user_id=user.id, project_id=project.id,
                                          concept_id=concepts[0].id)
        assert exam_scores.quiz.value == pytest.approx(100.0)
        # single row seeds the stream at 100 but the headline final caps at 60
        assert exam_scores.practice.value is None and exam_scores.final == pytest.approx(60.0)
        prac_scores = mastery_for_concept(db, user_id=user.id, project_id=project.id,
                                          concept_id=concepts[1].id)
        assert prac_scores.practice.value == pytest.approx(100.0)
        assert prac_scores.quiz.value is None
    finally:
        db.close()


def test_legacy_rows_without_source_still_derive():
    db = _session()
    try:
        user, project, (concept,) = _scaffold(db, uuid.uuid4().hex[:8])
        db.add(MasteryEvidence(user_id=user.id, project_id=project.id, concept_id=concept.id,
                               evidence_type="mcq", raw_score=90, created_at=T0))
        db.add(MasteryEvidence(user_id=user.id, project_id=project.id, concept_id=concept.id,
                               evidence_type="explain_back", raw_score=50, feedback="OK.",
                               created_at=T0 + timedelta(days=1)))
        db.commit()
        scores = mastery_for_concept(db, user_id=user.id, project_id=project.id,
                                     concept_id=concept.id)
        assert scores.quiz.value == pytest.approx(90.0)
        assert scores.open_ended.value == pytest.approx(50.0)
        assert scores.mcq.value == pytest.approx(90.0)
        assert scores.applied.value == pytest.approx(50.0)
        assert scores.final == pytest.approx((0.35 * 90 + 0.25 * 50) / 0.60)
        assert scores.evidence_confidence == EVIDENCE_LOW
        with pytest.raises(LookupError):
            mastery_for_concept(db, user_id=user.id, project_id=project.id,
                                concept_id=uuid.uuid4())
    finally:
        db.close()


def test_producer_rows_carry_source_and_feed_final():
    from app.services import explain_it_back_service, flashcard_service

    class StubClient:
        def __init__(self, payloads):
            self.payloads = list(payloads)

        def __call__(self, system, user):
            return self.payloads.pop(0)

    db = _session()
    try:
        user, project, (concept,) = _scaffold(db, uuid.uuid4().hex[:8])
        stub = StubClient([{"score": 70, "feedback": "Decent."}])
        evidence, _ = explain_it_back_service.submit_explanation(
            db, project_id=project.id, concept_id=concept.id, user_id=user.id,
            explanation_text="Rise over run and then some more detail here.", client=stub)
        assert evidence.source == "open_ended"
        built = flashcard_service.build_deck(db, project_id=project.id, concept_id=concept.id)
        assert built["total"] >= 1
        card = flashcard_service.list_cards(db, project_id=project.id, concept_id=concept.id)[0]
        flashcard_service.review_card(db, project_id=project.id, user_id=user.id,
                                      card_id=card.id, grade="good")
        rows = {r.evidence_type: r.source for r in db.query(MasteryEvidence).filter(
            MasteryEvidence.user_id == user.id, MasteryEvidence.concept_id == concept.id).all()}
        assert rows == {"explain_back": "open_ended", "flashcard": "flashcard"}
        scores = mastery_for_concept(db, user_id=user.id, project_id=project.id,
                                     concept_id=concept.id)
        assert scores.open_ended.value == pytest.approx(70.0)
        assert scores.flashcard.value == pytest.approx(80.0)
        assert scores.final == pytest.approx((0.25 * 70 + 0.15 * 80) / 0.40)
    finally:
        db.close()


def test_plain_tutor_messages_never_touch_mastery(monkeypatch):
    from app.models.tutor_conversation import TutorConversation
    from app.services import tutor_conversation_service
    from app.services.tutor_service import TutorAskResponse

    db = _session()
    try:
        user, project, (concept,) = _scaffold(db, uuid.uuid4().hex[:8])
        convo = tutor_conversation_service.create_conversation(db, project=project, user=user)

        def _fake_ask(db_, *, project_id, question, concept_id=None):
            return TutorAskResponse(answer="Slope is rise over run.", supported=True,
                                    citations=[], follow_ups=["What is intercept?"])

        monkeypatch.setattr("app.services.tutor_service.ask_question", _fake_ask)
        tutor_conversation_service.send_message(db, convo=convo, question="What is slope?")
        tutor_conversation_service.send_message(db, convo=convo, question="And intercept?")
        assert db.query(MasteryEvidence).filter(
            MasteryEvidence.user_id == user.id,
            MasteryEvidence.project_id == project.id).count() == 0
        assert mastery_for_concept(db, user_id=user.id, project_id=project.id,
                                   concept_id=concept.id).final is None
    finally:
        db.close()


def test_mcq_evidence_carries_question_difficulty_and_weights_mastery():
    db = _session()
    try:
        user, project, concepts = _scaffold(db, uuid.uuid4().hex[:8], n_concepts=2)
        easy_concept, hard_concept = concepts
        for concept, difficulty in ((easy_concept, "easy"), (hard_concept, "hard")):
            quiz = Quiz(project_id=project.id, mode="exam", question_count=2)
            db.add(quiz)
            db.flush()
            questions = []
            for i in range(2):
                q = QuizQuestion(quiz_id=quiz.id, concept_id=concept.id, question_text=f"Q{i}?",
                                 options=["a", "b"], correct_index=0, difficulty=difficulty)
                db.add(q)
                db.flush()
                questions.append(q)
            attempt = quiz_attempt_service.start_attempt(db, quiz_id=quiz.id, project_id=project.id,
                                                         user_id=user.id)
            # wrong first (0), right second (100) on both concepts
            quiz_attempt_service.submit_answer(db, attempt_id=attempt.id, project_id=project.id,
                                               user_id=user.id, question_id=questions[0].id,
                                               selected_index=1, confidence=3)
            quiz_attempt_service.submit_answer(db, attempt_id=attempt.id, project_id=project.id,
                                               user_id=user.id, question_id=questions[1].id,
                                               selected_index=0, confidence=3)
            quiz_attempt_service.complete_attempt(db, attempt_id=attempt.id, project_id=project.id,
                                                  user_id=user.id)
        rows = db.query(MasteryEvidence).filter(
            MasteryEvidence.user_id == user.id,
            MasteryEvidence.project_id == project.id).order_by(MasteryEvidence.created_at.asc()).all()
        assert [r.difficulty for r in rows if r.concept_id == easy_concept.id] == ["easy", "easy"]
        assert [r.difficulty for r in rows if r.concept_id == hard_concept.id] == ["hard", "hard"]
        easy_scores = mastery_for_concept(db, user_id=user.id, project_id=project.id,
                                          concept_id=easy_concept.id)
        hard_scores = mastery_for_concept(db, user_id=user.id, project_id=project.id,
                                          concept_id=hard_concept.id)
        assert easy_scores.quiz.value == pytest.approx(0 + 0.2 * 100)
        assert hard_scores.quiz.value == pytest.approx(0 + 0.4 * 100)
    finally:
        db.close()


def test_legacy_rows_without_difficulty_keep_default_weight():
    db = _session()
    try:
        user, project, (concept,) = _scaffold(db, uuid.uuid4().hex[:8])
        db.add(MasteryEvidence(user_id=user.id, project_id=project.id, concept_id=concept.id,
                               evidence_type="mcq", raw_score=0, created_at=T0))
        db.add(MasteryEvidence(user_id=user.id, project_id=project.id, concept_id=concept.id,
                               evidence_type="mcq", raw_score=100,
                               created_at=T0 + timedelta(days=1)))
        db.commit()
        rows = db.query(MasteryEvidence).filter(
            MasteryEvidence.concept_id == concept.id).all()
        assert all(r.difficulty is None for r in rows)
        scores = mastery_for_concept(db, user_id=user.id, project_id=project.id,
                                     concept_id=concept.id)
        assert scores.quiz.value == pytest.approx(0 + 0.3 * 100)
    finally:
        db.close()


def test_formative_only_final_capped_no_summative():
    assert FORMATIVE_ONLY_CAP == 70.0
    # practice-only perfect history caps instead of mastering
    perfect_practice = compute_mastery([_pt(100, "practice"), _pt(100, "practice"), _pt(100, "practice")])
    assert perfect_practice.practice.value == pytest.approx(100.0)
    assert perfect_practice.final == pytest.approx(70.0)
    # flashcard-only likewise
    perfect_cards = compute_mastery([_pt(100, "flashcard", etype="flashcard"),
                                     _pt(100, "flashcard", etype="flashcard")])
    assert perfect_cards.final == pytest.approx(70.0)
    # below-cap values pass through untouched
    mid = compute_mastery([_pt(60, "practice"), _pt(60, "practice")])
    assert mid.final == pytest.approx(60.0)
    # a summative stream lifts the cap
    with_quiz = compute_mastery([_pt(100, "practice"), _pt(100, "practice"),
                                 _pt(100, "quiz")])
    assert with_quiz.final == pytest.approx(100.0)
    with_open = compute_mastery([_pt(100, "practice"),
                                 _pt(100, "open_ended", etype="open_ended")])
    # open-ended lifts the formative cap, but 2 rows still hit the thin cap
    assert with_open.final == pytest.approx(75.0)
    # tutor-only keeps its stricter cap
    tutor_only = compute_mastery([_pt(100, "tutor", etype="tutor"),
                                  _pt(100, "tutor", etype="tutor")])
    assert tutor_only.final == pytest.approx(40.0)
