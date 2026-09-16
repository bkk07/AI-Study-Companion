"""Quiz attempt flow — start/answer/complete with server-side scoring (Phase 37).

Thin bridge over the Phase 34 models: correctness is always computed here from
`correct_index` (never trusted from the client, never revealed before answering).
Scopes are enforced by ID checks — routes supply the authorized project + user.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

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
    quiz = _get_quiz_in_project(db, quiz_id, project_id)
    attempt = QuizAttempt(quiz_id=quiz.id, user_id=user_id, started_at=datetime.now(timezone.utc))
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
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
    db.commit()
    db.refresh(answer)
    return answer, question.correct_index


def attempt_score(db: Session, attempt_id: uuid.UUID) -> tuple[int, int]:
    """(correct_count, answered_count) for an attempt."""
    answers = db.query(QuizAnswer).filter(QuizAnswer.attempt_id == attempt_id).all()
    return sum(1 for a in answers if a.is_correct), len(answers)


def complete_attempt(
    db: Session, *, attempt_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID
) -> QuizAttempt:
    """Lock the attempt and stamp the percentage score."""
    attempt = _get_open_attempt(db, attempt_id, user_id, project_id)
    correct, total = attempt_score(db, attempt.id)
    attempt.completed_at = datetime.now(timezone.utc)
    attempt.score = Decimal(correct * 100) / Decimal(total) if total else Decimal("0")
    db.commit()
    db.refresh(attempt)
    return attempt
