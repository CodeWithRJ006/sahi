"""Unit tests for SahiGuard deterministic safety guard."""

import pytest
from sahi.guard.engine import SahiGuard
from sahi.guard.models import GuardAction, ReasonCode, RiskLevel, ReadingSource
from sahi.amounts.models import ParsedAmount, ParseStatus, AmbiguityReason

@pytest.fixture
def guard():
    return SahiGuard(max_auto_execute_limit=50_000)

def test_guard_perfect_agreement_under_limit(guard):
    readings = [
        ReadingSource(source_name="saaras_literal", amount_inr=2500),
        ReadingSource(source_name="saaras_codemix", amount_inr=2500),
        ReadingSource(source_name="sarvam_llm", amount_inr=2500),
    ]
    dec = guard.evaluate(readings)
    assert dec.action == GuardAction.EXECUTE
    assert dec.final_amount_inr == 2500
    assert dec.reason_code == ReasonCode.AGREEMENT_VERIFIED
    assert dec.risk_level == RiskLevel.LOW

def test_guard_high_value_readback_policy(guard):
    readings = [
        ReadingSource(source_name="saaras_literal", amount_inr=60000),
        ReadingSource(source_name="sarvam_llm", amount_inr=60000),
    ]
    dec = guard.evaluate(readings)
    assert dec.action == GuardAction.READ_BACK
    assert dec.final_amount_inr == 60000
    assert dec.requires_readback is True
    assert dec.reason_code == ReasonCode.HIGH_VALUE_THRESHOLD

def test_guard_power_of_ten_discrepancy(guard):
    # 5,000 vs 50,000 is a 10x error
    readings = [
        ReadingSource(source_name="transcript_reading", amount_inr=5000),
        ReadingSource(source_name="agent_proposal", amount_inr=50000),
    ]
    dec = guard.evaluate(readings)
    assert dec.action == GuardAction.ESCALATE
    assert dec.reason_code == ReasonCode.POWER_OF_TEN_MISMATCH
    assert dec.risk_level == RiskLevel.CRITICAL
    assert dec.discrepancy_factor == 10.0

def test_guard_hundred_x_power_of_ten(guard):
    # 5,000 vs 500,000 (100x error)
    readings = [
        ReadingSource(source_name="transcript_reading", amount_inr=5000),
        ReadingSource(source_name="agent_proposal", amount_inr=500000),
    ]
    dec = guard.evaluate(readings)
    assert dec.action == GuardAction.ESCALATE
    assert dec.reason_code == ReasonCode.POWER_OF_TEN_MISMATCH
    assert dec.risk_level == RiskLevel.CRITICAL
    assert dec.discrepancy_factor == 100.0

def test_guard_phonetic_confusable(guard):
    # 15,000 vs 50,000 (pandrah vs pachas)
    readings = [
        ReadingSource(source_name="reading_1", amount_inr=15000),
        ReadingSource(source_name="reading_2", amount_inr=50000),
    ]
    dec = guard.evaluate(readings)
    assert dec.action == GuardAction.RE_ASK
    assert dec.reason_code == ReasonCode.PHONETIC_CONFUSABLE_MISMATCH
    assert dec.risk_level == RiskLevel.HIGH

def test_guard_self_correction_handling(guard):
    parsed = ParsedAmount(
        raw_text="send 500 no wait 5000",
        status=ParseStatus.AMBIGUOUS,
        ambiguity_reason=AmbiguityReason.SELF_CORRECTION,
        candidates=[500, 5000]
    )
    dec = guard.evaluate_parsed_amount(parsed)
    assert dec.action == GuardAction.RE_ASK
    assert dec.reason_code == ReasonCode.PARSE_AMBIGUOUS_SELF_CORRECTION
    assert dec.risk_level == RiskLevel.HIGH

def test_guard_multiple_amounts_handling(guard):
    parsed = ParsedAmount(
        raw_text="send 500 to Ramesh and 1000 to Suresh",
        status=ParseStatus.AMBIGUOUS,
        ambiguity_reason=AmbiguityReason.MULTIPLE_AMOUNTS,
        candidates=[500, 1000]
    )
    dec = guard.evaluate_parsed_amount(parsed)
    assert dec.action == GuardAction.RE_ASK
    assert dec.reason_code == ReasonCode.PARSE_AMBIGUOUS_MULTIPLE_AMOUNTS

def test_guard_unrecognized_text(guard):
    parsed = ParsedAmount(
        raw_text="hello send money",
        status=ParseStatus.UNRECOGNIZED,
        ambiguity_reason=AmbiguityReason.UNRESOLVED_WORDS
    )
    dec = guard.evaluate_parsed_amount(parsed)
    assert dec.action == GuardAction.RE_ASK
    assert dec.reason_code == ReasonCode.PARSE_UNRECOGNIZED

def test_guard_zero_or_negative(guard):
    readings = [ReadingSource(source_name="agent_proposal", amount_inr=-500)]
    dec = guard.evaluate(readings)
    assert dec.action == GuardAction.ESCALATE
    assert dec.reason_code == ReasonCode.ZERO_OR_NEGATIVE_AMOUNT
    assert dec.risk_level == RiskLevel.CRITICAL
