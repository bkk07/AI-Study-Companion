"""Mastery statuses + mastery-target gate — Phase A (learning model).

Single owner for two things that must never drift apart:

1. Status thresholds mapping a 0..100 mastery value (or None = no evidence)
   to a neutral learner-facing state. Bands align with the adaptive quiz
   difficulty bands (<34 / 34-66 / >66); the Mastered band (≥85) is new.
   Thresholds are operational, not scientific — change the constants here
   and every consumer follows.
2. `is_mastery_target`: THE gate for mastery-related behavior (mastery
   rollups, recommendations, browse/progress listings, quiz targeting).
   Only CORE, non-obsolete learning objects pass. RAG/search/context paths
   must never call this — all importances serve the knowledge model.

The EMA engine itself (`mastery_service`) is intentionally untouched.
"""

from __future__ import annotations

from typing import Any

from app.models.concept import DEFAULT_IMPORTANCE, OBSOLETE_STATUS

NOT_STARTED = "Not Started"
NEEDS_PRACTICE = "Needs Practice"
DEVELOPING = "Developing"
STRONG = "Strong"
MASTERED = "Mastered"

STATUSES = (NOT_STARTED, NEEDS_PRACTICE, DEVELOPING, STRONG, MASTERED)

# Upper-exclusive bounds: value < NEEDS_BELOW → Needs Practice, etc.
NEEDS_BELOW = 34.0
DEVELOPING_UPTO = 66.0
STRONG_UPTO = 84.0
MASTERED_FROM = 85.0


def status_for(mastery: float | None) -> str:
    """Map a mastery value to its status. None (no evidence) → Not Started."""
    if mastery is None:
        return NOT_STARTED
    if isinstance(mastery, bool) or not isinstance(mastery, (int, float)):
        raise ValueError("mastery must be None or a number")
    value = float(mastery)
    if not 0.0 <= value <= 100.0:
        raise ValueError("mastery must be 0..100")
    if value < NEEDS_BELOW:
        return NEEDS_PRACTICE
    if value <= DEVELOPING_UPTO:
        return DEVELOPING
    if value < MASTERED_FROM:
        return STRONG
    return MASTERED


def is_mastery_target(concept: Any) -> bool:
    """True only for CORE, non-obsolete learning objects.

    Legacy/partial rows (importance None) read as CORE — matches the DB
    backfill and the COALESCE convention in SQL readers. Accepts any object
    with `importance`/`meta` attributes so tests and future DTOs work.
    """
    importance = getattr(concept, "importance", None) or DEFAULT_IMPORTANCE
    if importance != "CORE":
        return False
    meta = getattr(concept, "meta", None) or {}
    if isinstance(meta, dict) and meta.get("status") == OBSOLETE_STATUS:
        return False
    return True
