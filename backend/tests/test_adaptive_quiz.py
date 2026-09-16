"""Phase 36 — adaptive selector unit tests on synthetic mastery states (no DB)."""

from datetime import datetime, timedelta

import pytest

from app.services.adaptive_quiz_service import (
    DEVELOPING_UPTO,
    NEEDS_BELOW,
    CandidateQuestion,
    _target_level,
    select_questions,
)
from app.services.mastery_levels import DEVELOPING_UPTO as LEVELS_UPTO
from app.services.mastery_levels import NEEDS_BELOW as LEVELS_BELOW

T0 = datetime(2026, 1, 1)
T1 = T0 + timedelta(days=1)


def _c(qid, concept, difficulty="medium", times=0, last=None):
    return CandidateQuestion(question_id=qid, concept_id=concept, difficulty=difficulty,
                             times_asked=times, last_asked_at=last)


def test_weakest_concept_first_round_robin():
    cands = [_c("w1", "weak"), _c("w2", "weak"), _c("s1", "strong"), _c("s2", "strong")]
    got = select_questions(cands, {"weak": 20.0, "strong": 90.0}, 3)
    assert [c.question_id for c in got] == ["w1", "s1", "w2"]


def test_target_level_bands_single_sourced():
    # Audit fix: bands come from mastery_levels — same objects, same values,
    # exact boundary semantics (<34 → 0, <=66 → 1, else 2).
    assert NEEDS_BELOW is LEVELS_BELOW and DEVELOPING_UPTO is LEVELS_UPTO
    assert (NEEDS_BELOW, DEVELOPING_UPTO) == (34.0, 66.0)
    assert _target_level(0) == 0 and _target_level(33.9) == 0
    assert _target_level(34) == 1 and _target_level(66) == 1
    assert _target_level(66.1) == 2 and _target_level(100) == 2


def test_difficulty_matched_to_mastery():
    cands = [
        _c("we-easy", "weak", "easy"), _c("we-hard", "weak", "hard"),
        _c("st-easy", "strong", "easy"), _c("st-hard", "strong", "hard"),
    ]
    got = select_questions(cands, {"weak": 10.0, "strong": 95.0}, 2)
    assert [c.question_id for c in got] == ["we-easy", "st-hard"]


def test_unseen_before_seen_then_least_recent():
    cands = [
        _c("seen-recent", "c", "medium", times=2, last=T1),
        _c("seen-old", "c", "medium", times=2, last=T0),
        _c("fresh", "c", "medium", times=0),
    ]
    got = select_questions(cands, {"c": 50.0}, 3)
    assert [c.question_id for c in got] == ["fresh", "seen-old", "seen-recent"]


def test_unknown_mastery_defaults_neutral_medium():
    cands = [_c("u-easy", "unknown", "easy"), _c("u-hard", "unknown", "hard"), _c("k1", "known")]
    got = select_questions(cands, {"known": 50.0}, 2)
    # unknown (50.0) ties known (50.0) on mastery and exposure → id order: known first
    assert [c.question_id for c in got] == ["k1", "u-easy"]


def test_deterministic_and_edged():
    cands = [_c("b", "c2"), _c("a", "c1")]
    mastery = {"c1": 50.0, "c2": 50.0}
    first = select_questions(cands, mastery, 2)
    second = select_questions(cands, mastery, 2)
    assert first == second
    assert [c.question_id for c in first] == ["a", "b"]  # full tie → concept id order
    assert select_questions([], mastery, 5) == []
    assert len(select_questions(cands, mastery, 20)) == 2  # more asked than available


def test_invalid_inputs_rejected():
    with pytest.raises(ValueError):
        select_questions([_c("q", "c")], {"c": 50.0}, 0)
    with pytest.raises(ValueError):
        select_questions([_c("q", "c")], {"c": 50.0}, 21)
    with pytest.raises(ValueError):
        select_questions([_c("q", "c", "extreme")], {"c": 50.0}, 1)
    with pytest.raises(ValueError):
        select_questions([_c("q", "c")], {"c": 120.0}, 1)
