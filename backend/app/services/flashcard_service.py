"""Flashcards v1 — deterministic decks + SM-2 review (learning model).

Deck building creates one card per CORE learning object (front/back derived
from the LO type — no LLM, works offline) and is idempotent: existing
(concept_id, front) rows are skipped, never duplicated. Review applies
classic SM-2 (intervals 1/6/efactor-scaled, 1.30 efactor floor, lapse resets
repetitions) and banks one `flashcard` evidence row per review (score =
quality x 20, transparent mapping) so recall practice moves applied mastery
like other free-recall evidence.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.concept import Concept
from app.models.flashcard import Flashcard
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.services.mastery_levels import is_mastery_target

GRADES = ("again", "hard", "good", "easy")
GRADE_QUALITY = {"again": 0, "hard": 3, "good": 4, "easy": 5}
MIN_EFACTOR = Decimal("1.30")
DEFAULT_EFACTOR = Decimal("2.50")
MAX_LIST_LIMIT = 100


def front_back_for(title: str, lo_type: str | None, summary: str) -> tuple[str, str]:
    """Deterministic card content by LO type (subject-agnostic)."""
    name = (title or "").strip()
    back = (summary or "").strip()
    kind = (lo_type or "CONCEPT").upper()
    if kind in ("TERM", "DEFINITION", "OTHER"):
        front = name
    elif kind == "FORMULA":
        front = f"{name} — state the formula"
    elif kind == "PROCESS":
        front = f"Describe the process: {name}"
    elif kind == "SKILL":
        front = f"How do you apply: {name}?"
    else:  # CONCEPT and any future type default to the recall question
        front = f"What is {name}?"
    return front, back


def _scope_subtopics(
    db: Session, project: Project, subtopic_id: uuid.UUID | None, topic_id: uuid.UUID | None
) -> list[Subtopic]:
    if subtopic_id is not None:
        sub = db.get(Subtopic, subtopic_id)
        if sub is None or sub.project_id != project.id:
            raise LookupError("subtopic not found in this project")
        return [sub]
    if topic_id is not None:
        topic = db.get(Topic, topic_id)
        if topic is None or topic.project_id != project.id:
            raise LookupError("topic not found in this project")
        return (
            db.query(Subtopic).filter(Subtopic.topic_id == topic.id)
            .order_by(Subtopic.created_at.asc()).all()
        )
    topic_ids = [t.id for t in db.query(Topic).filter(Topic.project_id == project.id).all()]
    if not topic_ids:
        return []
    return (
        db.query(Subtopic).filter(Subtopic.topic_id.in_(topic_ids))
        .order_by(Subtopic.created_at.asc()).all()
    )


def _create_card(db: Session, project: Project, row: Concept, existing: set) -> bool:
    """Insert one deterministic card for a CORE target unless present."""
    if not is_mastery_target(row):
        return False
    front, back = front_back_for(row.title, row.type, row.summary)
    if not front or not back:
        return False
    if (row.id, front) in existing:
        return False
    db.add(Flashcard(project_id=project.id, concept_id=row.id,
                     front=front, back=back, source="auto"))
    existing.add((row.id, front))
    return True


def build_deck(
    db: Session,
    *,
    project_id: uuid.UUID,
    subtopic_id: uuid.UUID | None = None,
    topic_id: uuid.UUID | None = None,
    concept_id: uuid.UUID | None = None,
    concept_ids: list[uuid.UUID] | None = None,
) -> dict:
    """Create missing cards for CORE targets in scope. Idempotent.

    Returns {"created": N, "total": M}. Exactly one scope may narrow the
    build: subtopic_id/topic_id/concept_id, or an explicit concept_ids list
    (tutor quiz-me style multi-select); none means the whole project.
    Non-target concepts in an explicit list are skipped.
    """
    provided = [v is not None for v in (subtopic_id, topic_id, concept_id)]
    if sum(provided) > 1 or (any(provided) and concept_ids):
        raise ValueError("pass at most one scope: subtopic_id, topic_id, concept_id, or concept_ids")
    project = db.get(Project, project_id)
    if project is None:
        raise LookupError("project not found")
    created = 0
    try:
        existing = {
            (c.concept_id, c.front)
            for c in db.query(Flashcard).filter(Flashcard.project_id == project.id).all()
        }
        if concept_ids is not None:
            seen: set[uuid.UUID] = set()
            for cid in concept_ids:
                if cid in seen:
                    continue
                seen.add(cid)
                row = db.get(Concept, cid)
                if row is None or row.project_id != project.id:
                    raise LookupError("concept not found in this project")
                if _create_card(db, project, row, existing):
                    created += 1
        elif concept_id is not None:
            row = db.get(Concept, concept_id)
            if row is None or row.project_id != project.id:
                raise LookupError("concept not found in this project")
            if not is_mastery_target(row):
                raise ValueError(f"Learning object '{row.title}' is not a deck target")
            if _create_card(db, project, row, existing):
                created += 1
        else:
            for sub in _scope_subtopics(db, project, subtopic_id, topic_id):
                rows = (
                    db.query(Concept).filter(Concept.subtopic_id == sub.id)
                    .order_by(Concept.created_at.asc()).all()
                )
                for row in rows:
                    if _create_card(db, project, row, existing):
                        created += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    total = db.query(Flashcard).filter(Flashcard.project_id == project.id).count()
    return {"created": created, "total": total}


def list_cards(
    db: Session,
    *,
    project_id: uuid.UUID,
    subtopic_id: uuid.UUID | None = None,
    topic_id: uuid.UUID | None = None,
    concept_id: uuid.UUID | None = None,
    concept_ids: list[uuid.UUID] | None = None,
    due_only: bool = False,
    limit: int = MAX_LIST_LIMIT,
    now: datetime | None = None,
) -> list[Flashcard]:
    """Cards in scope: due-first (overdue/nulls first), then by next review."""
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer")
    limit = max(1, min(limit, MAX_LIST_LIMIT))
    if concept_id is not None and concept_ids is not None:
        raise ValueError("pass at most one of concept_id, concept_ids")
    project = db.get(Project, project_id)
    if project is None:
        raise LookupError("project not found")
    moment = now or datetime.now(timezone.utc)
    q = db.query(Flashcard).filter(Flashcard.project_id == project.id)
    if concept_ids is not None:
        for cid in concept_ids:
            row = db.get(Concept, cid)
            if row is None or row.project_id != project.id:
                raise LookupError("concept not found in this project")
        q = q.filter(Flashcard.concept_id.in_(list(dict.fromkeys(concept_ids))))
    elif concept_id is not None:
        concept = db.get(Concept, concept_id)
        if concept is None or concept.project_id != project.id:
            raise LookupError("concept not found in this project")
        q = q.filter(Flashcard.concept_id == concept.id)
    elif subtopic_id is not None or topic_id is not None:
        subs = _scope_subtopics(db, project, subtopic_id, topic_id)
        q = q.filter(Flashcard.concept_id.in_(
            [c.id for s in subs for c in db.query(Concept).filter(
                Concept.subtopic_id == s.id).all()]
        ))
    if due_only:
        q = q.filter((Flashcard.next_review_at.is_(None))
                     | (Flashcard.next_review_at <= moment))
    return (
        q.order_by(Flashcard.next_review_at.asc().nulls_first(),
                   Flashcard.created_at.asc())
        .limit(limit).all()
    )


def count_due(
    db: Session, *, project_id: uuid.UUID, now: datetime | None = None
) -> int:
    """Project-wide due count (new cards count as due)."""
    project = db.get(Project, project_id)
    if project is None:
        raise LookupError("project not found")
    moment = now or datetime.now(timezone.utc)
    return (
        db.query(Flashcard)
        .filter(
            Flashcard.project_id == project.id,
            (Flashcard.next_review_at.is_(None)) | (Flashcard.next_review_at <= moment),
        )
        .count()
    )


def review_card(
    db: Session,
    *,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    card_id: uuid.UUID,
    grade: str,
    now: datetime | None = None,
) -> Flashcard:
    """Grade one review: SM-2 reschedule + banked flashcard evidence."""
    if grade not in GRADES:
        raise ValueError(f"grade must be one of {GRADES}")
    project = db.get(Project, project_id)
    if project is None:
        raise LookupError("project not found")
    card = db.get(Flashcard, card_id)
    if card is None or card.project_id != project.id:
        raise LookupError("flashcard not found in this project")
    quality = GRADE_QUALITY[grade]
    moment = now or datetime.now(timezone.utc)
    efactor = Decimal(card.efactor)
    efactor = efactor + (Decimal("0.1") - Decimal(5 - quality) * (
        Decimal("0.08") + Decimal(5 - quality) * Decimal("0.02")))
    if efactor < MIN_EFACTOR:
        efactor = MIN_EFACTOR
    if quality >= 3:
        if card.repetitions == 0:
            interval = 1
        elif card.repetitions == 1:
            interval = 6
        else:
            interval = round(card.interval_days * float(efactor))
        card.repetitions = card.repetitions + 1
    else:
        card.repetitions = 0
        interval = 1
        card.lapses = card.lapses + 1
    card.efactor = efactor.quantize(Decimal("0.01"))
    card.interval_days = interval
    card.next_review_at = moment + timedelta(days=interval)
    card.total_reviews = card.total_reviews + 1
    if quality >= 3:
        card.correct_reviews = card.correct_reviews + 1
    try:
        db.add(MasteryEvidence(
            user_id=user_id,
            project_id=project.id,
            concept_id=card.concept_id,
            evidence_type="flashcard",
            raw_score=Decimal(str(quality * 20)),
        ))
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(card)
    return card
