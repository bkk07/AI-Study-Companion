"""Phase 42 — mismatch engine: confirmed Blueprint rule, synthetic states, no DB."""

import uuid

import pytest

from app.services.mismatch_service import ConceptState, detect_mismatches


def _state(mcq, applied, mcq_n=5, applied_n=2, **kwargs):
    return ConceptState(concept_id=uuid.uuid4(), mcq_mastery=mcq, applied_mastery=applied,
                        mcq_count=mcq_n, applied_count=applied_n, **kwargs)


def test_primary_threshold_edge():
    assert detect_mismatches([_state(79, 54)]).pop().mismatch_type == "mcq_high_applied_low"  # gap exactly 25
    assert detect_mismatches([_state(78.9, 54)]) == []  # just under
    assert detect_mismatches([_state(92, 54)]).pop().gap == pytest.approx(38.0)
    assert detect_mismatches([_state(54, 92)]) == []  # reversed gap never flags primary


def test_minimum_evidence_gating():
    assert detect_mismatches([_state(95, 40, mcq_n=2)]) == []  # thin mcq
    assert detect_mismatches([_state(95, 40, applied_n=0)]) == []  # no applied
    flagged = detect_mismatches([_state(95, 40, mcq_n=3, applied_n=1)])
    assert len(flagged) == 1  # minima exactly met


def test_unknown_mastery_never_flags():
    assert detect_mismatches([_state(None, 40)]) == []
    assert detect_mismatches([_state(95, None)]) == []
    assert detect_mismatches([_state(None, None)]) == []


def test_calibration_secondary_bands():
    over = detect_mismatches([_state(60, 55, avg_confidence=4.5, accuracy=0.4, evaluated_count=10)])
    assert over.pop().mismatch_type == "overconfident"
    under = detect_mismatches([_state(60, 55, avg_confidence=1.5, accuracy=0.9, evaluated_count=10)])
    assert under.pop().mismatch_type == "underconfident"
    assert detect_mismatches([_state(60, 55, avg_confidence=4.5, accuracy=0.4, evaluated_count=0)]) == []
    assert detect_mismatches([_state(60, 55, avg_confidence=3.0, accuracy=0.7, evaluated_count=10)]) == []
    # primary wins the single badge when both fire:
    both = detect_mismatches([_state(95, 40, avg_confidence=5.0, accuracy=0.0, evaluated_count=10)])
    assert len(both) == 1 and both[0].mismatch_type == "mcq_high_applied_low"


def test_cross_concept_priority_and_tie_break():
    low_gap = _state(80, 54, avg_confidence=1.0, accuracy=1.0, evaluated_count=5)  # gap 26
    high_gap = _state(95, 40)  # gap 55
    under = _state(60, 55, avg_confidence=1.5, accuracy=0.9, evaluated_count=5)
    ranked = detect_mismatches([under, low_gap, high_gap])
    assert [m.mismatch_type for m in ranked] == ["mcq_high_applied_low"] * 2 + ["underconfident"]
    assert [m.gap for m in ranked[:2]] == pytest.approx([55.0, 26.0])  # type first, then gap desc
    twins = detect_mismatches([_state(80, 55), _state(80, 55)])
    assert str(twins[0].concept_id) < str(twins[1].concept_id)  # deterministic tie-break
    repeat = _state(80, 55)
    assert detect_mismatches([repeat]) == detect_mismatches([repeat])  # repeat identical


def test_reason_carries_numbers_and_invalid_inputs_rejected():
    mismatch = detect_mismatches([_state(92, 54)]).pop()
    assert "92.0" in mismatch.reason and "54.0" in mismatch.reason and "38.0" in mismatch.reason
    with pytest.raises(ValueError):
        ConceptState(concept_id=uuid.uuid4(), mcq_mastery=101, applied_mastery=50)
    with pytest.raises(ValueError):
        ConceptState(concept_id=uuid.uuid4(), mcq_mastery=50, applied_mastery=50, mcq_count=-1)
    with pytest.raises(ValueError):
        ConceptState(concept_id=uuid.uuid4(), mcq_mastery=50, applied_mastery=50, avg_confidence=6)
    with pytest.raises(ValueError):
        detect_mismatches([{"mcq_mastery": 90}])


def test_calibration_reason_uses_singular_for_one_record():
    over = detect_mismatches(
        [_state(60, 55, avg_confidence=5.0, accuracy=0.0, evaluated_count=1)]
    ).pop()
    assert over.mismatch_type == "overconfident"
    assert "over 1 evaluated answer." in over.reason
    under = detect_mismatches(
        [_state(60, 55, avg_confidence=1.0, accuracy=1.0, evaluated_count=1)]
    ).pop()
    assert under.mismatch_type == "underconfident"
    assert "over 1 evaluated answer." in under.reason
    many = detect_mismatches(
        [_state(60, 55, avg_confidence=5.0, accuracy=0.0, evaluated_count=4)]
    ).pop()
    assert "over 4 evaluated answers." in many.reason
