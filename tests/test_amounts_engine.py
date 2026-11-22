"""Unit tests for Multilingual Indic Amount Parsing Engine."""

import pytest
from sahi.amounts.engine import AmountEngine
from sahi.amounts.models import ParseStatus, AmbiguityReason, LanguageGroup

@pytest.fixture
def engine():
    return AmountEngine()

def test_english_direct_digits_and_scale(engine):
    res1 = engine.parse("send 5000 rupees")
    assert res1.status == ParseStatus.PARSED
    assert res1.amount_inr == 5000

    res2 = engine.parse("transfer 5k to account")
    assert res2.status == ParseStatus.PARSED
    assert res2.amount_inr == 5000

    res3 = engine.parse("pay 2.5 lakh rupees")
    assert res3.status == ParseStatus.PARSED
    assert res3.amount_inr == 250000

def test_english_colloquial_words(engine):
    res1 = engine.parse("transfer twenty five hundred rupees")
    assert res1.status == ParseStatus.PARSED
    assert res1.amount_inr == 2500

    res2 = engine.parse("two and a half lakhs")
    assert res2.status == ParseStatus.PARSED
    assert res2.amount_inr == 250000

    res3 = engine.parse("half a lakh")
    assert res3.status == ParseStatus.PARSED
    assert res3.amount_inr == 50000

def test_hindi_devanagari_and_latin(engine):
    res1 = engine.parse("दो हज़ार पाँच सौ रुपये")
    assert res1.status == ParseStatus.PARSED
    assert res1.amount_inr == 2500

    res2 = engine.parse("do hazar panch sau rupaye")
    assert res2.status == ParseStatus.PARSED
    assert res2.amount_inr == 2500

    res3 = engine.parse("dhai hazar transfer karo")
    assert res3.status == ParseStatus.PARSED
    assert res3.amount_inr == 2500

    res4 = engine.parse("dedh lakh rupaye")
    assert res4.status == ParseStatus.PARSED
    assert res4.amount_inr == 150000

    res5 = engine.parse("sadhe teen hazar bhejo")
    assert res5.status == ParseStatus.PARSED
    assert res5.amount_inr == 3500

def test_hindi_confusables(engine):
    res_50 = engine.parse("pachas hazar")
    res_15 = engine.parse("pandrah hazar")
    assert res_50.amount_inr == 50000
    assert res_15.amount_inr == 15000
    assert res_50.amount_inr != res_15.amount_inr

    res_70 = engine.parse("sattar hazar")
    res_17 = engine.parse("satrah hazar")
    assert res_70.amount_inr == 70000
    assert res_17.amount_inr == 17000
    assert res_70.amount_inr != res_17.amount_inr

def test_telugu_script_and_latin(engine):
    res1 = engine.parse("రెండు వేల ఐదు వందలు రూపాయలు")
    assert res1.status == ParseStatus.PARSED
    assert res1.amount_inr == 2500

    res2 = engine.parse("rendu vela aidu vandalu roopayalu")
    assert res2.status == ParseStatus.PARSED
    assert res2.amount_inr == 2500

    res3 = engine.parse("rendunnara velu pampu")
    assert res3.status == ParseStatus.PARSED
    assert res3.amount_inr == 2500

    res4 = engine.parse("sagam laksha")
    assert res4.status == ParseStatus.PARSED
    assert res4.amount_inr == 50000

    res5 = engine.parse("padi lakshalu")
    assert res5.status == ParseStatus.PARSED
    assert res5.amount_inr == 1000000

def test_telugu_confusables(engine):
    res_50 = engine.parse("yabhai velu")
    res_15 = engine.parse("padihenu velu")
    assert res_50.amount_inr == 50000
    assert res_15.amount_inr == 15000

    res_70 = engine.parse("debbai velu")
    res_17 = engine.parse("padihedu velu")
    assert res_70.amount_inr == 70000
    assert res_17.amount_inr == 17000

def test_self_correction_ambiguity(engine):
    res1 = engine.parse("send 500 no wait 5000 rupees")
    assert res1.status == ParseStatus.AMBIGUOUS
    assert res1.ambiguity_reason == AmbiguityReason.SELF_CORRECTION
    assert 500 in res1.candidates
    assert 5000 in res1.candidates

    res2 = engine.parse("transfer 2000 nahi nahi 20000")
    assert res2.status == ParseStatus.AMBIGUOUS
    assert res2.ambiguity_reason == AmbiguityReason.SELF_CORRECTION
    assert 2000 in res2.candidates
    assert 20000 in res2.candidates

def test_multiple_amounts_ambiguity(engine):
    res = engine.parse("send 500 to Ramesh and 1000 to Suresh")
    assert res.status == ParseStatus.AMBIGUOUS
    assert res.ambiguity_reason == AmbiguityReason.MULTIPLE_AMOUNTS
    assert 500 in res.candidates
    assert 1000 in res.candidates

def test_unrecognized_text(engine):
    res = engine.parse("good morning please transfer money")
    assert res.status == ParseStatus.UNRECOGNIZED
    assert res.amount_inr is None

def test_crore_scale(engine):
    res1 = engine.parse("send 1 crore rupees")
    assert res1.status == ParseStatus.PARSED
    assert res1.amount_inr == 10000000

    res2 = engine.parse("ek karod rupaye")
    assert res2.status == ParseStatus.PARSED
    assert res2.amount_inr == 10000000

    res3 = engine.parse("oka koti roopayalu")
    assert res3.status == ParseStatus.PARSED
    assert res3.amount_inr == 10000000

def test_hindi_devanagari_fractions(engine):
    res1 = engine.parse("डेढ़ लाख रुपये")
    assert res1.status == ParseStatus.PARSED
    assert res1.amount_inr == 150000

    res2 = engine.parse("ढाई हज़ार रुपये")
    assert res2.status == ParseStatus.PARSED
    assert res2.amount_inr == 2500

def test_telugu_script_fractions(engine):
    res1 = engine.parse("రెండున్నర వేలు పంపు")
    assert res1.status == ParseStatus.PARSED
    assert res1.amount_inr == 2500

    res2 = engine.parse("సగం లక్ష")
    assert res2.status == ParseStatus.PARSED
    assert res2.amount_inr == 50000
