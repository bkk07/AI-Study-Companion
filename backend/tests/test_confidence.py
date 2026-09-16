"""Phase 38 — confidence calibration unit tests, incl. mastery separation (no DB)."""

import pytest

from app.services.confidence_service import AnswerRecord, summarize


def test_gap_math_and_extremes():
    records = [
        AnswerRecord("c", True, 5),   # sure + right
        AnswerRecord("c", True, 2),   # unsure + right
        AnswerRecord("c", False, 5),  # confidently wrong
        AnswerRecord("c", False, 4),  # confidently wrong
    ]
    cal = summarize(records).by_concept["c"]
    assert (cal.answered, cal.correct, cal.accuracy) == (4, 2, 0.5)
    assert cal.rated == 4 and cal.avg_confidence == 4.0
    assert cal.calibration_gap == pytest.approx((4 - 1) * 25 - 50.0)  # 75 - 50
    assert cal.confidently_wrong == 2
    assert cal.unsure_right == 1


def test_unrated_counts_for_accuracy_never_confidence():
    records = [AnswerRecord("c", True, None), AnswerRecord("c", False, 3)]
    cal = summarize(records).by_concept["c"]
    assert (cal.answered, cal.correct, cal.accuracy) == (2, 1, 0.5)
    assert cal.rated == 1 and cal.avg_confidence == 3.0
    assert cal.confidently_wrong == 0 and cal.unsure_right == 0


def test_empty_and_all_unrated():
    empty = summarize([])
    assert empty.by_concept == {}
    assert empty.overall.answered == 0 and empty.overall.avg_confidence is None
    assert empty.overall.calibration_gap is None
    cal = summarize([AnswerRecord("c", True, None)]).by_concept["c"]
    assert cal.avg_confidence is None and cal.calibration_gap is None


def test_overall_rollup_across_concepts():
    records = [AnswerRecord("a", True, 5), AnswerRecord("b", False, 1)]
    summary = summarize(records)
    assert set(summary.by_concept) == {"a", "b"}
    assert (summary.overall.answered, summary.overall.correct) == (2, 1)
    assert summary.overall.avg_confidence == 3.0


def test_mastery_proxy_unaffected_by_confidence_swings():
    """Contract step 3: correctness-only accuracy is constant as confidence varies."""
    base = [True, True, False, True]  # fixed correctness
    for confidences in ([1, 1, 1, 1], [5, 5, 5, 5], [1, 5, 3, None]):
        records = [AnswerRecord("c", ok, cf) for ok, cf in zip(base, confidences)]
        cal = summarize(records).by_concept["c"]
        assert cal.accuracy == 0.75  # mastery-side output never moves
    low = summarize([AnswerRecord("c", ok, 1) for ok in base]).by_concept["c"]
    high = summarize([AnswerRecord("c", ok, 5) for ok in base]).by_concept["c"]
    assert low.calibration_gap != high.calibration_gap  # ...while the confidence signal moves


def test_bad_confidence_rejected():
    with pytest.raises(ValueError):
        summarize([AnswerRecord("c", True, 0)])
    with pytest.raises(ValueError):
        summarize([AnswerRecord("c", True, 6)])
