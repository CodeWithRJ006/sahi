import pytest
from sahi.amounts.engine import AmountEngine
from sahi.amounts.models import ParseStatus, AmbiguityReason

engine = AmountEngine()

def test_valid_correction_within_limit():
    # 5 karod = 50 000 000 (within the 100 000 000 limit)
    res = engine.parse("send 1 karod no wait send 5 karod")
    assert res.status == ParseStatus.PARSED
    assert res.amount_inr == 50_000_000

def test_out_of_bounds_correction_fallback_prevented():
    # 50 karod = 500 000 000 > limit, intent must be rejected
    res = engine.parse("send 500 no wait send 50 karod")
    assert res.status == ParseStatus.AMBIGUOUS
    assert res.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS
    assert any(a > 100_000_000 for a in res.candidates)

def test_out_of_bounds_correction_with_earlier_amount():
    # later amount 11 karod = 110 000 000 > limit
    res = engine.parse("send 500 no wait send 11 karod")
    assert res.status == ParseStatus.AMBIGUOUS
    assert res.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS
    assert any(a > 100_000_000 for a in res.candidates)

def test_zero_correction_rejected():
    res = engine.parse("send 5 karod no wait send 0 rupees")
    assert res.status == ParseStatus.AMBIGUOUS
    assert res.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS

def test_negative_correction_rejected():
    res = engine.parse("send 5 karod no wait send -500 rupees")
    assert res.status == ParseStatus.AMBIGUOUS
    assert res.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS

def test_conflicting_correction_rejected():
    res = engine.parse("send 5 karod no wait send fifty rupees")
    assert res.status == ParseStatus.AMBIGUOUS
    assert res.ambiguity_reason == AmbiguityReason.SELF_CORRECTION
    assert set(res.candidates) == {50_000_000, 50}

def test_unresolved_correction_rejected():
    res = engine.parse("send 5 karod no wait send bla bla bla")
    assert res.status == ParseStatus.AMBIGUOUS
    assert res.ambiguity_reason == AmbiguityReason.UNRESOLVED_WORDS

def test_ambiguous_multiple_amounts_without_correction():
    res = engine.parse("send 500 and 1000")
    assert res.status == ParseStatus.AMBIGUOUS
    assert res.ambiguity_reason == AmbiguityReason.MULTIPLE_AMOUNTS
