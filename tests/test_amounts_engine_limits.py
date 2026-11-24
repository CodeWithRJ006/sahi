import pytest
from sahi.amounts.engine import AmountEngine
from sahi.amounts.models import ParseStatus, AmbiguityReason

def test_english_so_not_parsed_as_scale():
    engine = AmountEngine()
    result = engine.parse("pay 10 so we can start")
    assert result.status == ParseStatus.PARSED
    assert result.amount_inr == 10

def test_hindi_sau_parses_correctly():
    engine = AmountEngine()
    result = engine.parse("pay 5 sau")
    assert result.status == ParseStatus.PARSED
    assert result.amount_inr == 500

def test_global_limit_boundary_parsed():
    engine = AmountEngine()
    result = engine.parse("10 crore rupees")
    assert result.status == ParseStatus.PARSED
    assert result.amount_inr == 100_000_000

def test_global_limit_exceeds_ambiguous():
    engine = AmountEngine()
    result = engine.parse("11 crore rupees")
    assert result.status == ParseStatus.AMBIGUOUS
    assert result.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS

def test_hindi_limit_boundary_parsed():
    engine = AmountEngine()
    result = engine.parse("10 karod rupees")
    assert result.status == ParseStatus.PARSED
    assert result.amount_inr == 100_000_000

def test_hindi_limit_exceeds_ambiguous():
    engine = AmountEngine()
    result = engine.parse("11 karod rupees")
    assert result.status == ParseStatus.AMBIGUOUS
    assert result.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS

def test_telugu_limit_boundary_parsed():
    engine = AmountEngine()
    result = engine.parse("10 kotlu rupees")
    assert result.status == ParseStatus.PARSED
    assert result.amount_inr == 100_000_000

def test_telugu_limit_exceeds_ambiguous():
    engine = AmountEngine()
    result = engine.parse("11 kotlu rupees")
    assert result.status == ParseStatus.AMBIGUOUS
    assert result.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS
