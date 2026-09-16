"""Mismatch result types — derived domain types, NOT a database table (Phase 42).

Mismatch is computed on read from mastery scores + evidence counts (like
mastery itself): a persisted snapshot would go stale with every new
evidence row and nothing recomputes it. Consumers (recommendation engine,
dashboard) call `mismatch_service.detect_mismatches` with current values.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

MCQ_HIGH_APPLIED_LOW = "mcq_high_applied_low"
OVERCONFIDENT = "overconfident"
UNDERCONFIDENT = "underconfident"

MISMATCH_TYPES = (MCQ_HIGH_APPLIED_LOW, OVERCONFIDENT, UNDERCONFIDENT)

# One badge per concept; the primary differentiator always wins.
TYPE_PRIORITY = {MCQ_HIGH_APPLIED_LOW: 0, OVERCONFIDENT: 1, UNDERCONFIDENT: 2}


@dataclass(frozen=True)
class Mismatch:
    """One flagged concept — gap/reason carry the numbers, non-judgmental."""

    concept_id: uuid.UUID
    mismatch_type: str
    mcq_mastery: float
    applied_mastery: float
    gap: float
    reason: str
