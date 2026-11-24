# Additional regression tests for Phase 3A.1 edge cases

import pytest
from sahi.amounts.engine import AmountEngine
from sahi.amounts.models import ParseStatus, AmbiguityReason


@pytest.fixture
def engine():
    return AmountEngine()


def test_phone_number_is_not_parsed_as_amount(engine):
    # Pure phone number – should be UNRECOGNIZED (no amount)
    assert engine.parse("transfer to 9876543210").status == ParseStatus.UNRECOGNIZED
    # Phone + amount – amount should be extracted correctly
    res1 = engine.parse("send to 9876543210 500 rupees")
    assert res1.status == ParseStatus.PARSED
    assert res1.amount_inr == 500
    res2 = engine.parse("send 500 to 9876543210")
    assert res2.status == ParseStatus.PARSED
    assert res2.amount_inr == 500
    # Explicit 10-digit amount with currency word is not masked away as a phone number,
    # but safely flagged as OUT_OF_BOUNDS because ₹1,234,567,890 exceeds the ₹10 crore maximum limit.
    res3 = engine.parse("send 1234567890 rupees")
    assert res3.status == ParseStatus.AMBIGUOUS
    assert res3.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS
    assert 1234567890 in res3.candidates


def test_compact_negative_forms(engine):
    for txt in ["minus500 rupees", "negative500", "-500 rupees"]:
        result = engine.parse(txt)
        assert result.status == ParseStatus.UNRECOGNIZED
        assert result.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS


def test_date_like_numeric_strings(engine):
    # Should be treated as unrecognized rather than a huge amount
    for txt in ["pay 15082024", "transfer 20241124"]:
        result = engine.parse(txt)
        assert result.status == ParseStatus.UNRECOGNIZED
        # No specific ambiguity reason is required, just ensure not parsed as amount
