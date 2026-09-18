"""Quiz attempt flow — start/answer/complete with server-side scoring (Phase 37).

Thin bridge over the Phase 34 models: correctness is always computed here from
`correct_index` (never trusted from the client, never revealed before answering).
Scopes are enforced by ID checks — routes supply the authorized project + user.

Answer → Next Question Adaptation (learning-loop closure): each submitted
answer immediately banks one append-only `mcq` evidence row (same 100/0 +
difficulty mapping as completion-time banking, tagged with
``feedback="quiz_answer:<answer_id>"`` so completion dedupes instead of
duplicating), then :func:`select_next_question` deterministically picks the
next unanswered question in this quiz from CURRENT mastery (weakest-first,
difficulty-matched, exposure-balanced via the shared
``adaptive_quiz_service`` engine — never an LLM). Completion-time
:func:`write_mcq_evidence` skips already-evidenced answers, so totals are
unchanged whether evidence landed per-answer or at completion.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.mastery_evidence import MasteryEvidence
from app.models.quiz import Quiz, QuizQuestion
from app.models.quiz_attempt import QuizAnswer, QuizAttempt


def _get_quiz_in_project(db: Session, quiz_id: uuid.UUID, project_id: uuid.UUID) -> Quiz:
    quiz = db.get(Quiz, quiz_id)
    if quiz is None or quiz.project_id != project_id:
        raise LookupError("quiz not found in this project")
    return quiz


def _get_open_attempt(db: Session, attempt_id: uuid.UUID, user_id: uuid.UUID, project_id: uuid.UUID) -> QuizAttempt:
    attempt = db.get(QuizAttempt, attempt_id)
    if attempt is None or attempt.user_id != user_id:
        raise LookupError("attempt not found")
    _get_quiz_in_project(db, attempt.quiz_id, project_id)
    if attempt.completed_at is not None:
        raise ValueError("attempt is already completed")
    return attempt


def start_attempt(db: Session, *, quiz_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID) -> QuizAttempt:
    """Create an attempt and return it (questions served separately, answer-free)."""
    from app.services import activity_service

    quiz = _get_quiz_in_project(db, quiz_id, project_id)
    attempt = QuizAttempt(quiz_id=quiz.id, user_id=user_id, started_at=datetime.now(timezone.utc))
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    # §12: quiz.started — idempotent on retry.
    activity_service.record_event_committed(
        db,
        user_id=user_id,
        project_id=project_id,
        space_id=activity_service.resolve_space_id(db, project_id=project_id),
        event_type=activity_service.EVENT_QUIZ_STARTED,
        entity_type="attempt",
        entity_id=attempt.id,
        payload={"quiz_id": str(quiz.id)},
        idempotency_key=f"attempt:{attempt.id}:started",
    )
    return attempt


def attempt_questions(db: Session, attempt: QuizAttempt) -> list[QuizQuestion]:
    return (
        db.query(QuizQuestion)
        .filter(QuizQuestion.quiz_id == attempt.quiz_id)
        .order_by(QuizQuestion.created_at.asc())
        .all()
    )


def submit_answer(
    db: Session,
    *,
    attempt_id: uuid.UUID,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    question_id: uuid.UUID,
    selected_index: int,
    confidence: int | None,
) -> tuple[QuizAnswer, int]:
    """Record one answer; correctness computed server-side. One answer per question.

    Returns the answer plus the question's correct_index for the reveal.
    """
    attempt = _get_open_attempt(db, attempt_id, user_id, project_id)
    question = db.get(QuizQuestion, question_id)
    if question is None or question.quiz_id != attempt.quiz_id:
        raise LookupError("question not found in this quiz")
    if not 0 <= selected_index < len(question.options):
        raise ValueError("selected_index out of range")
    if confidence is not None and not 1 <= confidence <= 5:
        raise ValueError("confidence must be 1..5")
    existing = (
        db.query(QuizAnswer)
        .filter(QuizAnswer.attempt_id == attempt.id, QuizAnswer.question_id == question.id)
        .first()
    )
    if existing is not None:
        raise ValueError("question already answered in this attempt")
    answer = QuizAnswer(
        attempt_id=attempt.id,
        question_id=question.id,
        selected_index=selected_index,
        is_correct=selected_index == question.correct_index,
        confidence=confidence,
    )
    db.add(answer)
    try:
        db.flush()  # assign answer.id so the evidence row can reference it
        _bank_single_answer_evidence(db, attempt=attempt, answer=answer, question=question)
        db.commit()
    except IntegrityError as e:
        # Lost a concurrent-submits race against uq_quiz_answers_attempt_question.
        db.rollback()
        raise ValueError("question already answered in this attempt") from e
    except Exception:
        db.rollback()
        raise
    db.refresh(answer)
    # §12: question.answered — small outcome payload, never the text.
    from app.services import activity_service

    activity_service.record_event_committed(
        db,
        user_id=user_id,
        project_id=project_id,
        space_id=activity_service.resolve_space_id(db, project_id=project_id),
        event_type=activity_service.EVENT_QUESTION_ANSWERED,
        entity_type="answer",
        entity_id=answer.id,
        payload={
            "is_correct": bool(answer.is_correct),
            "confidence": confidence,
            "attempt_id": str(attempt.id),
        },
        idempotency_key=f"answer:{answer.id}",
    )
    return answer, question.correct_index


def attempt_score(db: Session, attempt_id: uuid.UUID) -> tuple[int, int]:
    """(correct_count, answered_count) for an attempt."""
    answers = db.query(QuizAnswer).filter(QuizAnswer.attempt_id == attempt_id).all()
    return sum(1 for a in answers if a.is_correct), len(answers)


def _evidence_marker(answer_id: uuid.UUID) -> str:
    """Feedback tag linking one evidence row to its quiz answer (dedup key)."""
    return f"quiz_answer:{answer_id}"


def _bank_single_answer_evidence(
    db: Session, *, attempt: QuizAttempt, answer: QuizAnswer, question: QuizQuestion
) -> MasteryEvidence:
    """Append the one `mcq` row for a just-scored answer (no commit).

    Same mapping as completion-time banking (100/0, question difficulty,
    stream by quiz mode). Caller owns the transaction.
    """
    from app.services.mastery_service import PRACTICE_STREAM, QUIZ_STREAM

    quiz = db.get(Quiz, attempt.quiz_id)
    if quiz is None:  # validated upstream by _get_open_attempt; guard for safety
        raise LookupError("quiz not found in this project")
    source = QUIZ_STREAM if quiz.mode == "exam" else PRACTICE_STREAM
    row = MasteryEvidence(
        user_id=attempt.user_id,
        project_id=quiz.project_id,
        concept_id=question.concept_id,
        evidence_type="mcq",
        source=source,
        raw_score=Decimal("100") if answer.is_correct else Decimal("0"),
        difficulty=question.difficulty,
        feedback=_evidence_marker(answer.id),
    )
    db.add(row)
    return row


def write_mcq_evidence(db: Session, attempt: QuizAttempt, project_id: uuid.UUID) -> int:
    """Persist one `mcq` evidence row per answered question of the attempt.

    The Plan A stream follows the quiz mode: `exam` rows feed the `quiz`
    stream, `practice` rows feed the `practice` stream. Score is 100/0 per
    answer on the question's own concept — the model's "one row per graded
    learning action". Returns the row count. Caller commits; on error the
    caller rolls back. Unanswered questions are skipped; re-running for the
    same attempt would duplicate, so callers must gate on completion state
    (complete_attempt rejects re-completion before reaching here).

    Idempotent across the per-answer path: answers already evidenced by
    :func:`submit_answer` (matched via their ``quiz_answer:<id>`` feedback
    marker) are skipped, so moving evidence earlier never double-counts.
    """
    from app.services.mastery_service import PRACTICE_STREAM, QUIZ_STREAM

    quiz = _get_quiz_in_project(db, attempt.quiz_id, project_id)
    source = QUIZ_STREAM if quiz.mode == "exam" else PRACTICE_STREAM
    answers = (
        db.query(QuizAnswer, QuizQuestion)
        .join(QuizQuestion, QuizAnswer.question_id == QuizQuestion.id)
        .filter(QuizAnswer.attempt_id == attempt.id)
        .all()
    )
    if not answers:
        return 0
    markers = {_evidence_marker(a.id) for a, _ in answers}
    existing = {
        r[0]
        for r in db.query(MasteryEvidence.feedback)
        .filter(
            MasteryEvidence.user_id == attempt.user_id,
            MasteryEvidence.project_id == quiz.project_id,
            MasteryEvidence.feedback.in_(list(markers)),
        )
        .all()
    }
    count = 0
    for answer, question in answers:
        if _evidence_marker(answer.id) in existing:
            continue
        db.add(MasteryEvidence(
            user_id=attempt.user_id,
            project_id=quiz.project_id,
            concept_id=question.concept_id,
            evidence_type="mcq",
            source=source,
            raw_score=Decimal("100") if answer.is_correct else Decimal("0"),
            difficulty=question.difficulty,
            feedback=_evidence_marker(answer.id),
        ))
        count += 1
    return count


def select_next_question(
    db: Session, *, attempt_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID
) -> QuizQuestion | None:
    """Deterministically pick the next unanswered question in this attempt.

    Answer-time adaptation over the shared ``adaptive_quiz_service`` engine
    (weakest-first, difficulty-matched to CURRENT mastery, exposure-balanced,
    deterministic ties) — the live path ``select_questions`` previously
    lacked. Inputs are derived only from existing data:

    - candidates: unanswered questions of this quiz (same ``quiz_id`` —
      never outside the selected scope; answered-in-this-attempt excluded,
      so repetition is impossible);
    - mastery: current per-concept display mastery (same definition as quiz
      generation) AFTER the just-banked per-answer evidence — a correct
      answer raises its concept (next may go harder or move to the next
      weakest concept) while an incorrect answer lowers it (next stays on
      the concept at an easier band or reinforces it);
    - exposure: prior answers by this user per candidate question (times
      asked + recency across attempts — no new tables);
    - curriculum order for tie-breaking (Topic → Subtopic → Concept).

    Returns None when nothing remains (attempt complete) or the attempt is
    finished. Raises LookupError/ValueError on scope violations (same
    ownership checks as answering). Pure selection — writes nothing, no LLM.
    """
    from app.services import adaptive_quiz_service as _adaptive
    from app.services import mastery_service as _mastery
    from app.services.rollup_service import display_mastery as _display

    attempt = db.get(QuizAttempt, attempt_id)
    if attempt is None or attempt.user_id != user_id:
        raise LookupError("attempt not found")
    _get_quiz_in_project(db, attempt.quiz_id, project_id)
    if attempt.completed_at is not None:
        return None

    answered_ids = {
        r[0]
        for r in db.query(QuizAnswer.question_id)
        .filter(QuizAnswer.attempt_id == attempt.id)
        .all()
    }
    remaining = (
        db.query(QuizQuestion)
        .filter(QuizQuestion.quiz_id == attempt.quiz_id)
        .order_by(QuizQuestion.created_at.asc())
        .all()
    )
    remaining = [q for q in remaining if q.id not in answered_ids]
    if not remaining:
        return None

    # Current mastery per concept in this quiz's scope (batch, ONE query).
    concept_ids = list({q.concept_id for q in remaining})
    try:
        scores_by_concept = _mastery.mastery_for_concepts(
            db, user_id=user_id, project_id=project_id
        )
    except Exception:
        scores_by_concept = {}
    mastery: dict[str, float] = {}
    for cid in concept_ids:
        scores = scores_by_concept.get(cid)
        if scores is None:
            continue
        try:
            value = _display(scores)
        except Exception:
            value = None
        if value is not None:
            mastery[str(cid)] = float(value)

    # Exposure from existing attempt data (user's prior answers per question).
    prior = (
        db.query(QuizAnswer.question_id, QuizAnswer.answered_at)
        .join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id)
        .filter(QuizAttempt.user_id == user_id)
        .all()
    )
    times: dict[uuid.UUID, int] = {}
    last: dict[uuid.UUID, object] = {}
    for qid, answered_at in prior:
        times[qid] = times.get(qid, 0) + 1
        if qid not in last or (answered_at is not None and answered_at > last[qid]):
            last[qid] = answered_at

    candidates = [
        _adaptive.CandidateQuestion(
            question_id=str(q.id),
            concept_id=str(q.concept_id),
            difficulty=q.difficulty,
            times_asked=times.get(q.id, 0),
            last_asked_at=last.get(q.id),
        )
        for q in remaining
    ]
    curriculum = _curriculum_order_for_project(db, project_id)
    picked = _adaptive.select_questions(candidates, mastery, 1, curriculum)
    if not picked:
        return None
    by_id = {str(q.id): q for q in remaining}
    return by_id.get(picked[0].question_id)


def _curriculum_order_for_project(db: Session, project_id: uuid.UUID) -> dict[str, int]:
    """Concept order index (Topic → Subtopic → Concept creation) keyed by str id."""
    try:
        from app.models.concept import Concept as _Concept
        from app.models.subtopic import Subtopic as _Subtopic
        from app.models.topic import Topic as _Topic

        rows = (
            db.query(_Concept.id)
            .join(_Subtopic, _Concept.subtopic_id == _Subtopic.id)
            .join(_Topic, _Subtopic.topic_id == _Topic.id)
            .filter(_Concept.project_id == project_id)
            .order_by(_Topic.created_at.asc(), _Subtopic.created_at.asc(), _Concept.created_at.asc())
            .all()
        )
        return {str(r[0]): i for i, r in enumerate(rows)}
    except Exception:
        return {}


def complete_attempt(
    db: Session, *, attempt_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID
) -> QuizAttempt:
    """Lock the attempt, stamp the percentage score, and bank mcq evidence."""
    attempt = _get_open_attempt(db, attempt_id, user_id, project_id)
    correct, total = attempt_score(db, attempt.id)
    attempt.completed_at = datetime.now(timezone.utc)
    attempt.score = Decimal(correct * 100) / Decimal(total) if total else Decimal("0")
    try:
        write_mcq_evidence(db, attempt, project_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(attempt)
    # §12: quiz.completed + mastery.updated — the completion banks evidence.
    from app.services import activity_service

    _space = activity_service.resolve_space_id(db, project_id=project_id)
    activity_service.record_event_committed(
        db,
        user_id=user_id,
        project_id=project_id,
        space_id=_space,
        event_type=activity_service.EVENT_QUIZ_COMPLETED,
        entity_type="attempt",
        entity_id=attempt.id,
        payload={"score": float(attempt.score), "answers": total},
        idempotency_key=f"quiz:{attempt.id}:completed",
    )
    activity_service.record_event_committed(
        db,
        user_id=user_id,
        project_id=project_id,
        space_id=_space,
        event_type=activity_service.EVENT_MASTERY_UPDATED,
        entity_type="attempt",
        entity_id=attempt.id,
        # Total rows attributable to this attempt (per-answer banking lands
        # rows at submit time; completion-time write_mcq_evidence only tops
        # up whatever is missing). Keeps the long-standing contract that a
        # completed N-answer attempt reports N evidence rows.
        payload={"evidence_rows": total, "source": "quiz"},
        idempotency_key=f"attempt:{attempt.id}:mastery",
    )
    # Blueprint §16: recommendation recomputes after mastery-affecting
    # events. Synchronous inline recompute first — guaranteed whenever the
    # fresh evidence is scorable, with no broker required and no pytest skip.
    # The Celery task remains only as a fallback when the inline path raises;
    # evidence is already committed above, so completion must not fail here.
    try:
        from app.services import recommendation_service

        recommendation_service.recompute_now(db, user_id=user_id, project_id=project_id)
    except Exception:
        from app.worker.tasks.recommendations import refresh_best_effort

        refresh_best_effort(user_id, project_id)  # never raises; no-op under pytest
    return attempt
