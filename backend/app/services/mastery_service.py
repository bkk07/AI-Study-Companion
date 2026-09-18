"""Mastery engine — deterministic EMA over append-only evidence (Plan A).

Five activity streams, each with its own EMA, combined into one weighted
final mastery per (user, project, concept):

    Final = sum(weight_s * mastery_s over streams WITH evidence)
            / sum(weight_s over streams WITH evidence)

Missing streams are renormalized away — never treated as zero.

Stream weights (Plan A, confirmed by the user 2026-09-17):

- quiz:        0.35 (summative quiz / exam mode — highest validity)
- open_ended:  0.25 (graded free-text + Explain-It-Back)
- practice:    0.20 (formative MCQ with hints — lower stakes than quiz)
- flashcard:   0.15 (retention / recall)
- tutor:       0.05 (graded tutor check only — easy to game, capped low)

Per-stream EMA keeps the confirmed Blueprint formula (A1): seed mastery
with the first score, then `mastery += weight * (score - mastery)`,
clamped to 0..100, where `weight = difficulty base + gap boost`, capped
at 0.5 (easy 0.2 / medium 0.3 / hard 0.4, +0.1 when the gap since the
previous evidence in that stream strictly exceeds 7 days).

Tutor is special:

- fixed EMA weight 0.15 per update (difficulty and gap boost ignored),
- at most 1 tutor evidence per UTC calendar day per concept (the pure
  engine keeps the latest point per day; the DB writer
  `record_tutor_evidence` rejects a second row for the same day),
- tutor rows come ONLY from a graded explain-back/follow-up check via
  `record_tutor_evidence` — plain tutor chat messages never write
  `mastery_evidence` (tutor_conversation_service has no evidence import;
  this separation is structural, like the confidence separation).

Final-mastery rules:

- 0 evidence -> final None (explicit unknown, "Not Started"),
- fewer than 3 total evidence rows -> evidence_confidence "low",
- tutor-only evidence -> final capped at 40 (chatting alone can never
  master a concept),
- formative-only evidence (practice/flashcard/tutor, no quiz or
  open-ended stream) -> final capped at 70 (drills alone can build
  Strong recognition but never Mastered; a summative grade lifts the cap),
- a single evidence row caps final at 60, two rows at 75 (one answer is
  never mastery, however perfect; streams keep raw values, only the
  headline final is capped),
- missing streams renormalized (see formula above).

Backward compatibility: legacy rows have `source` NULL and are routed by
`evidence_type` (`mcq` -> quiz, `open_ended`/`explain_back` -> open_ended,
`flashcard` -> flashcard, `tutor` -> tutor). The `mcq` / `applied`
aggregate streams are kept so every existing consumer (dashboard, growth,
rollups, recommendations, mismatch) keeps working unchanged: `mcq` replays
the old formula over quiz+practice points, `applied` over
open_ended+flashcard+tutor points.

The engine is pure (no LLM) plus two thin read-only helpers
(`mastery_for_concept`) and one guarded writer (`record_tutor_evidence`).
Evidence rows are never mutated. Confidence is not an input anywhere in
this module: the mastery/confidence separation is structural.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.concept import Concept
from app.models.mastery_evidence import MasteryEvidence
from app.models.project import Project

EASY_WEIGHT = 0.2
MEDIUM_WEIGHT = 0.3
HARD_WEIGHT = 0.4
DEFAULT_WEIGHT = 0.3
GAP_BOOST = 0.1
MAX_WEIGHT = 0.5
GAP_THRESHOLD = timedelta(days=7)

# Tutor update weight is fixed — difficulty/gap never apply to tutor points.
TUTOR_WEIGHT = 0.15
# Tutor-only concepts can never exceed this final mastery.
TUTOR_ONLY_CAP = 40.0
# Formative-only concepts (practice/flashcard/tutor streams, no summative
# quiz or graded open-ended evidence) can never exceed this final mastery.
# Practice with hints and flashcard recall must not grind a concept to
# Mastered on their own; a quiz or open-ended grade lifts the cap.
FORMATIVE_ONLY_CAP = 70.0
# Thin-evidence guard: one lucky/careless answer must not read as mastery.
# A single data point seeds the stream at its face value, so the headline
# final is capped until evidence accumulates (streams keep raw values for
# transparency; only the final shown to learners is capped).
THIN_EVIDENCE_CAP_1 = 60.0
THIN_EVIDENCE_CAP_2 = 75.0
# Fewer total rows than this -> evidence_confidence "low".
LOW_CONFIDENCE_MIN_ROWS = 3

QUIZ_STREAM = "quiz"
OPEN_ENDED_STREAM = "open_ended"
PRACTICE_STREAM = "practice"
FLASHCARD_STREAM = "flashcard"
TUTOR_STREAM = "tutor"

STREAMS = (QUIZ_STREAM, OPEN_ENDED_STREAM, PRACTICE_STREAM, FLASHCARD_STREAM, TUTOR_STREAM)

STREAM_WEIGHTS = {
    QUIZ_STREAM: 0.35,
    OPEN_ENDED_STREAM: 0.25,
    PRACTICE_STREAM: 0.20,
    FLASHCARD_STREAM: 0.15,
    TUTOR_STREAM: 0.05,
}
# Streams whose evidence is summative enough to lift the formative-only cap.
SUMMATIVE_STREAMS = frozenset({QUIZ_STREAM, OPEN_ENDED_STREAM})

MCQ_TYPE = "mcq"
OPEN_ENDED_TYPE = "open_ended"
EXPLAIN_BACK_TYPE = "explain_back"
FLASHCARD_TYPE = "flashcard"
TUTOR_TYPE = "tutor"

OPEN_ENDED_TYPES = frozenset({OPEN_ENDED_TYPE, EXPLAIN_BACK_TYPE})
KNOWN_TYPES = frozenset({MCQ_TYPE, OPEN_ENDED_TYPE, EXPLAIN_BACK_TYPE, FLASHCARD_TYPE, TUTOR_TYPE})
DIFFICULTY_WEIGHTS = {"easy": EASY_WEIGHT, "medium": MEDIUM_WEIGHT, "hard": HARD_WEIGHT}

EVIDENCE_NONE = "none"
EVIDENCE_LOW = "low"
EVIDENCE_OK = "ok"


@dataclass(frozen=True)
class EvidenceInput:
    """One scored evidence point. Note: there is deliberately no confidence field."""

    evidence_type: str
    score: float
    difficulty: str | None = None
    at: datetime | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        if self.evidence_type not in KNOWN_TYPES:
            raise ValueError(f"evidence_type must be one of {sorted(KNOWN_TYPES)}")
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
            raise ValueError("score must be a number")
        if not 0 <= self.score <= 100:
            raise ValueError("score must be 0..100")
        if self.difficulty is not None and self.difficulty not in DIFFICULTY_WEIGHTS:
            raise ValueError("difficulty must be easy, medium, hard, or None")
        if self.source is not None and self.source not in STREAMS:
            raise ValueError(f"source must be None or one of {list(STREAMS)}")


@dataclass(frozen=True)
class StreamMastery:
    """Derived state of one stream — value None means no evidence yet."""

    value: float | None
    count: int = 0
    last_at: datetime | None = None


@dataclass(frozen=True)
class MasteryScores:
    """Five activity streams plus backward-compatible aggregates and final.

    `mcq` replays the legacy formula over quiz+practice points and
    `applied` over open_ended+flashcard+tutor points, so consumers written
    against the two-stream engine read identical numbers for legacy data.
    `final` is the Plan A weighted mastery (None when there is no
    evidence); `evidence_confidence` is "none" (0 rows), "low" (<3 rows),
    or "ok".
    """

    quiz: StreamMastery = field(default_factory=StreamMastery)
    open_ended: StreamMastery = field(default_factory=StreamMastery)
    practice: StreamMastery = field(default_factory=StreamMastery)
    flashcard: StreamMastery = field(default_factory=StreamMastery)
    tutor: StreamMastery = field(default_factory=StreamMastery)
    mcq: StreamMastery = field(default_factory=StreamMastery)
    applied: StreamMastery = field(default_factory=StreamMastery)
    final: float | None = None
    total_count: int = 0
    evidence_confidence: str = EVIDENCE_NONE


def stream_for(evidence_type: str, source: str | None) -> str:
    """Route one evidence point to its Plan A stream.

    Explicit `source` always wins (new rows). Legacy rows (`source` NULL)
    route by `evidence_type` so pre-Plan-A history is preserved verbatim.
    """
    if source is not None:
        if source not in STREAMS:
            raise ValueError(f"source must be one of {list(STREAMS)}")
        return source
    if evidence_type == MCQ_TYPE:
        return QUIZ_STREAM
    if evidence_type in OPEN_ENDED_TYPES:
        return OPEN_ENDED_STREAM
    if evidence_type == FLASHCARD_TYPE:
        return FLASHCARD_STREAM
    if evidence_type == TUTOR_TYPE:
        return TUTOR_STREAM
    raise ValueError(f"evidence_type must be one of {sorted(KNOWN_TYPES)}")


def _weight(difficulty: str | None, gap: timedelta | None) -> float:
    base = DIFFICULTY_WEIGHTS.get(difficulty, DEFAULT_WEIGHT) if difficulty else DEFAULT_WEIGHT
    if gap is not None and gap > GAP_THRESHOLD:
        base += GAP_BOOST
    return min(base, MAX_WEIGHT)


def _check_timestamps(points: list[EvidenceInput]) -> list[EvidenceInput]:
    ats = [p.at for p in points]
    if any(a is None for a in ats) and any(a is not None for a in ats):
        raise ValueError("timestamps must be all present or all absent within a stream")
    if len({a.tzinfo is None for a in ats if a is not None}) > 1:
        raise ValueError("timestamps must not mix naive and aware datetimes within a stream")
    if ats[0] is not None:
        return sorted(points, key=lambda p: p.at)
    return list(points)


def _dedupe_tutor_days(points: list[EvidenceInput]) -> list[EvidenceInput]:
    """Enforce max 1 tutor evidence per UTC calendar day (keep the latest).

    Points without timestamps cannot be day-bucketed, so each counts (the
    DB writer always stamps rows, making this a pure-engine safety net).
    """
    by_day: dict[object, EvidenceInput] = {}
    untimed: list[EvidenceInput] = []
    for point in points:
        if point.at is None:
            untimed.append(point)
            continue
        by_day[point.at.date()] = point  # input is time-ordered: later wins
    return [by_day[day] for day in sorted(by_day)] + untimed


def _run_stream(points: list[EvidenceInput], *, fixed_weight: float | None = None) -> StreamMastery:
    if not points:
        return StreamMastery(value=None)
    ordered = _check_timestamps(points)
    mastery = float(ordered[0].score)
    for prev, cur in zip(ordered, ordered[1:]):
        if fixed_weight is not None:
            step = fixed_weight
        else:
            gap = (cur.at - prev.at) if cur.at is not None and prev.at is not None else None
            step = _weight(cur.difficulty, gap)
        mastery += step * (float(cur.score) - mastery)
    mastery = min(100.0, max(0.0, mastery))
    last = ordered[-1].at
    return StreamMastery(value=mastery, count=len(ordered), last_at=last)


def _run_tutor_stream(points: list[EvidenceInput]) -> StreamMastery:
    if not points:
        return StreamMastery(value=None)
    ordered = _check_timestamps(points)
    deduped = _dedupe_tutor_days(ordered)
    return _run_stream(deduped, fixed_weight=TUTOR_WEIGHT)


def compute_final(streams: dict[str, StreamMastery]) -> float | None:
    """Plan A weighted final over streams that have evidence (renormalized).

    Tutor-only input is capped at TUTOR_ONLY_CAP; formative-only input
    (practice/flashcard/tutor with no summative quiz or open-ended stream)
    is capped at FORMATIVE_ONLY_CAP. No evidence -> None.
    """
    present = {name: s for name, s in streams.items() if s.value is not None}
    if not present:
        return None
    known = [s.value for s in present.values()]
    if any(v is None for v in known):
        return None
    total_w = sum(STREAM_WEIGHTS[name] for name in present)
    final = sum(STREAM_WEIGHTS[name] * float(s.value) for name, s in present.items()) / total_w
    if set(present) == {TUTOR_STREAM}:
        final = min(final, TUTOR_ONLY_CAP)
    elif not (set(present) & SUMMATIVE_STREAMS):
        final = min(final, FORMATIVE_ONLY_CAP)
    return min(100.0, max(0.0, final))


def evidence_confidence_for(total_count: int) -> str:
    """Evidence-amount flag: "none" (0 rows), "low" (<3), else "ok"."""
    if total_count <= 0:
        return EVIDENCE_NONE
    if total_count < LOW_CONFIDENCE_MIN_ROWS:
        return EVIDENCE_LOW
    return EVIDENCE_OK


def compute_mastery(points: list[EvidenceInput]) -> MasteryScores:
    """Derive five streams, compat aggregates, and final mastery. Pure — no I/O."""
    if any(not isinstance(p, EvidenceInput) for p in points):
        raise ValueError("points must all be EvidenceInput")
    by_stream: dict[str, list[EvidenceInput]] = {name: [] for name in STREAMS}
    for point in points:
        by_stream[stream_for(point.evidence_type, point.source)].append(point)
    streams = {
        QUIZ_STREAM: _run_stream(by_stream[QUIZ_STREAM]),
        OPEN_ENDED_STREAM: _run_stream(by_stream[OPEN_ENDED_STREAM]),
        PRACTICE_STREAM: _run_stream(by_stream[PRACTICE_STREAM]),
        FLASHCARD_STREAM: _run_stream(by_stream[FLASHCARD_STREAM]),
        TUTOR_STREAM: _run_tutor_stream(by_stream[TUTOR_STREAM]),
    }
    # Compat aggregates replay the legacy two-stream formula over the same
    # points (tutor points join applied with standard weights here; the
    # dedicated tutor stream above still uses the fixed 0.15 weight).
    mcq = _run_stream(by_stream[QUIZ_STREAM] + by_stream[PRACTICE_STREAM])
    applied = _run_stream(
        by_stream[OPEN_ENDED_STREAM] + by_stream[FLASHCARD_STREAM] + by_stream[TUTOR_STREAM]
    )
    final = compute_final(streams)
    if final is not None:
        if len(points) == 1:
            final = min(final, THIN_EVIDENCE_CAP_1)
        elif len(points) == 2:
            final = min(final, THIN_EVIDENCE_CAP_2)
    return MasteryScores(
        quiz=streams[QUIZ_STREAM],
        open_ended=streams[OPEN_ENDED_STREAM],
        practice=streams[PRACTICE_STREAM],
        flashcard=streams[FLASHCARD_STREAM],
        tutor=streams[TUTOR_STREAM],
        mcq=mcq,
        applied=applied,
        final=final,
        total_count=len(points),
        evidence_confidence=evidence_confidence_for(len(points)),
    )


def _row_to_input(row: MasteryEvidence) -> EvidenceInput:
    return EvidenceInput(
        evidence_type=row.evidence_type,
        score=float(row.raw_score),
        difficulty=getattr(row, "difficulty", None),
        at=row.created_at,
        source=getattr(row, "source", None),
    )


def mastery_for_concept(
    db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID, concept_id: uuid.UUID
) -> MasteryScores:
    """Read-only derivation for one (user, project, concept). Writes nothing."""
    project = db.get(Project, project_id)
    concept = db.get(Concept, concept_id)
    if project is None or concept is None or concept.project_id != project.id:
        raise LookupError("project or concept not found in scope")
    rows = (
        db.query(MasteryEvidence)
        .filter(
            MasteryEvidence.user_id == user_id,
            MasteryEvidence.project_id == project.id,
            MasteryEvidence.concept_id == concept.id,
        )
        .order_by(MasteryEvidence.created_at.asc())
        .all()
    )
    return compute_mastery([_row_to_input(r) for r in rows])


def evidence_inputs_by_concept(
    db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID
) -> dict[uuid.UUID, list[EvidenceInput]]:
    """All of a user's project evidence in ONE query, grouped by concept.

    Same row filter and ordering as the per-concept reader; shared so batch
    derivations (tree, dashboard, growth) never replay N sequential queries.
    """
    rows = (
        db.query(MasteryEvidence)
        .filter(
            MasteryEvidence.user_id == user_id,
            MasteryEvidence.project_id == project_id,
        )
        .order_by(MasteryEvidence.created_at.asc())
        .all()
    )
    by_concept: dict[uuid.UUID, list[EvidenceInput]] = {}
    for row in rows:
        by_concept.setdefault(row.concept_id, []).append(_row_to_input(row))
    return by_concept


def mastery_for_concepts(
    db: Session, *, user_id: uuid.UUID, project_id: uuid.UUID
) -> dict[uuid.UUID, MasteryScores]:
    """Batch derivation for every concept of (user, project) in ONE evidence query.

    Identical math to calling mastery_for_concept per concept: same row filter,
    same pure compute_mastery. Only concepts WITH evidence rows appear as keys;
    callers fall back to compute_mastery([]) for unevidenced concepts.
    Exists so read-heavy endpoints (knowledge tree) don't pay N sequential
    round-trips against remote Postgres.
    """
    return {
        concept_id: compute_mastery(points)
        for concept_id, points in evidence_inputs_by_concept(
            db, user_id=user_id, project_id=project_id
        ).items()
    }


def record_tutor_evidence(
    db: Session,
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    concept_id: uuid.UUID,
    score: float,
    feedback: str | None = None,
    now: datetime | None = None,
) -> MasteryEvidence:
    """Bank one graded tutor check as `tutor` evidence (the ONLY tutor writer).

    Guards: score 0..100 (bool rejected); project/concept scope; at most one
    tutor row per UTC calendar day per (user, project, concept). Plain tutor
    chat messages must never call this — they are ungraded and carry no
    difficulty, so folding them into mastery would invent signal.
    """
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ValueError("score must be a number")
    if not 0 <= float(score) <= 100:
        raise ValueError("score must be 0..100")
    project = db.get(Project, project_id)
    concept = db.get(Concept, concept_id)
    if project is None or concept is None or concept.project_id != project.id:
        raise LookupError("project or concept not found in scope")
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    day_start = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    same_day = (
        db.query(MasteryEvidence)
        .filter(
            MasteryEvidence.user_id == user_id,
            MasteryEvidence.project_id == project.id,
            MasteryEvidence.concept_id == concept.id,
            MasteryEvidence.evidence_type == TUTOR_TYPE,
            MasteryEvidence.created_at >= day_start,
        )
        .count()
    )
    if same_day >= 1:
        raise ValueError("at most 1 tutor evidence per day per concept")
    try:
        row = MasteryEvidence(
            user_id=user_id,
            project_id=project.id,
            concept_id=concept.id,
            evidence_type=TUTOR_TYPE,
            source=TUTOR_STREAM,
            raw_score=Decimal(str(float(score))),
            feedback=feedback,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        # §12: mastery.updated — graded tutor check banked as evidence.
        try:
            from app.services import activity_service

            activity_service.record_event_committed(
                db,
                user_id=user_id,
                project_id=project.id,
                space_id=activity_service.resolve_space_id(db, project_id=project.id),
                event_type=activity_service.EVENT_MASTERY_UPDATED,
                entity_type="evidence",
                entity_id=row.id,
                payload={"evidence_rows": 1, "source": "tutor"},
                idempotency_key=f"evidence:{row.id}:mastery",
            )
        except Exception:
            pass
        return row
    except Exception:
        db.rollback()
        raise
