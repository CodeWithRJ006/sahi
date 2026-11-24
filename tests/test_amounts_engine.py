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

def test_indian_number_formatting_and_commas(engine):
    # Valid Indian and standard grouping
    assert engine.parse("send 1,000 rupees").amount_inr == 1000
    assert engine.parse("send 10,000 rupees").amount_inr == 10000
    assert engine.parse("send 1,00,000 rupees").amount_inr == 100000
    assert engine.parse("send 1,23,456 rupees").amount_inr == 123456
    assert engine.parse("send 10,00,000 rupees").amount_inr == 1000000
    assert engine.parse("send 1,00,00,000 rupees").amount_inr == 10000000

    # Malformed commas must not silently parse into 1234
    res_bad = engine.parse("send 1,2,3,4 rupees")
    assert res_bad.status != ParseStatus.PARSED or res_bad.amount_inr != 1234

def test_decimal_amounts_and_paise(engine):
    # Whole rupees + paise -> flagged as FRACTION_AMBIGUITY (no silent rounding to 101 or 100)
    res_both = engine.parse("send 100 rupees and 50 paise")
    assert res_both.status == ParseStatus.AMBIGUOUS
    assert res_both.ambiguity_reason == AmbiguityReason.FRACTION_AMBIGUITY
    assert res_both.metadata.get("paise") == 50
    assert res_both.metadata.get("rupees") == 100

    res_both2 = engine.parse("send 100 rupees 50 paise")
    assert res_both2.status == ParseStatus.AMBIGUOUS
    assert res_both2.ambiguity_reason == AmbiguityReason.FRACTION_AMBIGUITY

    # Pure paise < 100 -> sub-rupee cannot be settled as integer INR
    res_paise = engine.parse("send 50 paise")
    assert res_paise.status == ParseStatus.UNRECOGNIZED
    assert res_paise.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS

    # Fractional decimal rupees without scale (e.g. 12.75) -> FRACTION_AMBIGUITY, not silently 13
    res_dec = engine.parse("send 12.75 rupees")
    assert res_dec.status == ParseStatus.AMBIGUOUS
    assert res_dec.ambiguity_reason == AmbiguityReason.FRACTION_AMBIGUITY

    # Decimal with scale (e.g. 2.5 lakh = 250,000) is exact integer -> PARSED
    res_scale = engine.parse("send 2.5 lakh rupees")
    assert res_scale.status == ParseStatus.PARSED
    assert res_scale.amount_inr == 250000

def test_hinglish_scale_expressions(engine):
    # Hinglish scales must parse cleanly without conflicting with Hindi
    res1 = engine.parse("send 5 hazar")
    assert res1.status == ParseStatus.PARSED
    assert res1.amount_inr == 5000

    res2 = engine.parse("5 hazar rupees")
    assert res2.status == ParseStatus.PARSED
    assert res2.amount_inr == 5000

    res3 = engine.parse("send 5 velu")
    assert res3.status == ParseStatus.PARSED
    assert res3.amount_inr == 5000

def test_missing_and_unrecognized_amount(engine):
    res1 = engine.parse("send money to Ramesh")
    assert res1.status == ParseStatus.UNRECOGNIZED

    res2 = engine.parse("good morning please transfer money")
    assert res2.status == ParseStatus.UNRECOGNIZED

    res3 = engine.parse("pay account")
    assert res3.status == ParseStatus.UNRECOGNIZED

def test_multiple_amounts_handling(engine):
    # Delimited by 'and'
    res1 = engine.parse("send 500 to Ramesh and 1000 to Suresh")
    assert res1.status == ParseStatus.AMBIGUOUS
    assert res1.ambiguity_reason == AmbiguityReason.MULTIPLE_AMOUNTS
    assert set(res1.candidates) == {500, 1000}

    # Delimited by comma
    res2 = engine.parse("500 to Ramesh , 1000 to Suresh")
    assert res2.status == ParseStatus.AMBIGUOUS
    assert res2.ambiguity_reason == AmbiguityReason.MULTIPLE_AMOUNTS
    assert set(res2.candidates) == {500, 1000}

    # Unparsed multiple numbers in sequence
    res3 = engine.parse("send 500 1000 rupees")
    assert res3.status == ParseStatus.AMBIGUOUS
    assert res3.ambiguity_reason == AmbiguityReason.MULTIPLE_AMOUNTS
    assert set(res3.candidates) == {500, 1000}

def test_conflicting_disjunctive_amounts(engine):
    res1 = engine.parse("send 500 or 1000 rupees")
    assert res1.status == ParseStatus.AMBIGUOUS
    assert res1.ambiguity_reason == AmbiguityReason.CONFLICTING_PARSES
    assert set(res1.candidates) == {500, 1000}

    res2 = engine.parse("500 ya 1000 bhejo")
    assert res2.status == ParseStatus.AMBIGUOUS
    assert res2.ambiguity_reason == AmbiguityReason.CONFLICTING_PARSES
    assert set(res2.candidates) == {500, 1000}

    res3 = engine.parse("500 leda 1000 pampu")
    assert res3.status == ParseStatus.AMBIGUOUS
    assert res3.ambiguity_reason == AmbiguityReason.CONFLICTING_PARSES
    assert set(res3.candidates) == {500, 1000}

def test_zero_and_negative_amounts(engine):
    res_zero1 = engine.parse("send 0 rupees")
    assert res_zero1.status == ParseStatus.UNRECOGNIZED
    assert res_zero1.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS

    res_zero2 = engine.parse("zero rupees")
    assert res_zero2.status == ParseStatus.UNRECOGNIZED
    assert res_zero2.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS

    res_neg1 = engine.parse("send -500 rupees")
    assert res_neg1.status == ParseStatus.UNRECOGNIZED
    assert res_neg1.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS

    res_neg2 = engine.parse("send minus 500 rupees")
    assert res_neg2.status == ParseStatus.UNRECOGNIZED
    assert res_neg2.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS

def test_extremely_large_amounts(engine):
    # Amounts exceeding 10 crore (100,000,000) threshold are flagged as OUT_OF_BOUNDS
    res = engine.parse("send 500000000 rupees")
    assert res.status == ParseStatus.AMBIGUOUS
    assert res.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS
    assert 500000000 in res.candidates

def test_phone_account_and_date_disambiguation(engine):
    # Standalone phone numbers must NOT be parsed as multi-billion rupee amounts
    assert engine.parse("call 9876543210").status == ParseStatus.UNRECOGNIZED
    assert engine.parse("transfer to 9876543210").status == ParseStatus.UNRECOGNIZED

    # Phone number + amount: amount must be extracted cleanly
    res_phone1 = engine.parse("send 500 to 9876543210")
    assert res_phone1.status == ParseStatus.PARSED
    assert res_phone1.amount_inr == 500

    res_phone2 = engine.parse("send to 9876543210 500 rupees")
    assert res_phone2.status == ParseStatus.PARSED
    assert res_phone2.amount_inr == 500

    # Account numbers must not be parsed as amount
    assert engine.parse("transfer to account 123456789012").status == ParseStatus.UNRECOGNIZED
    res_acc = engine.parse("transfer 5000 to account 123456789012")
    assert res_acc.status == ParseStatus.PARSED
    assert res_acc.amount_inr == 5000

    # Dates must not be parsed as amount
    assert engine.parse("transfer on 15/08/2024").status == ParseStatus.UNRECOGNIZED
    res_date = engine.parse("on 15-08-2024 pay 500 rupees")
    assert res_date.status == ParseStatus.PARSED
    assert res_date.amount_inr == 500

def test_invalid_numeric_and_ambiguous_phrases(engine):
    assert engine.parse("send abc123xyz").status == ParseStatus.UNRECOGNIZED
    assert engine.parse("transfer money immediately").status == ParseStatus.UNRECOGNIZED

def test_mandatory_parser_regressions(engine):
    # 1. Valid self-corrections must use the final correction
    res1 = engine.parse("five hundred rupees no wait six hundred rupees")
    assert res1.status == ParseStatus.PARSED
    assert res1.amount_inr == 600

    res2 = engine.parse("ten thousand rupees actually five thousand rupees")
    assert res2.status == ParseStatus.PARSED
    assert res2.amount_inr == 5000

    res3 = engine.parse("one lakh no wait two lakh")
    assert res3.status == ParseStatus.PARSED
    assert res3.amount_inr == 200000

    res4 = engine.parse("four thousand rupees nahin actually three thousand")
    assert res4.status == ParseStatus.PARSED
    assert res4.amount_inr == 3000

    res5 = engine.parse("seven hundred rupees, wait sorry, eight hundred rupees")
    assert res5.status == ParseStatus.PARSED
    assert res5.amount_inr == 800

    # 2. Conflicting or unsafe corrections must never execute
    res_conf = engine.parse("send 500 no wait 5000 rupees")
    assert res_conf.status == ParseStatus.AMBIGUOUS
    assert set(res_conf.candidates) == {500, 5000}

    res_zero = engine.parse("send 5 karod no wait send 0 rupees")
    assert res_zero.status == ParseStatus.AMBIGUOUS
    assert res_zero.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS

    res_neg = engine.parse("send 5 karod no wait send -500 rupees")
    assert res_neg.status == ParseStatus.AMBIGUOUS
    assert res_neg.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS

    res_oob1 = engine.parse("send 50 karod")
    assert res_oob1.status == ParseStatus.AMBIGUOUS
    assert res_oob1.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS

    res_oob2 = engine.parse("send 50 kotlu")
    assert res_oob2.status == ParseStatus.AMBIGUOUS
    assert res_oob2.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS

    res_oob3 = engine.parse("send 100000001")
    assert res_oob3.status == ParseStatus.AMBIGUOUS
    assert res_oob3.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS

    # 3. English 'so' vs Hindi 'so' scale
    assert engine.parse("pay 10 so we can start").amount_inr == 10
    assert engine.parse("send 5 so far").amount_inr == 5
    assert engine.parse("pay 5 sau").amount_inr == 500

    # 4. Telugu scales inflected forms
    assert engine.parse("ఐదు వందల రూపాయలు").amount_inr == 500
    assert engine.parse("రెండు లక్షల రూపాయలు").amount_inr == 200000
    assert engine.parse("రెండు కోట్ల రూపాయలు").amount_inr == 20000000

    # 5. Word plus digit contradiction
    res_wpd = engine.parse("send 500 five thousand rupees")
    assert res_wpd.status == ParseStatus.AMBIGUOUS
    assert res_wpd.ambiguity_reason == AmbiguityReason.CONFLICTING_PARSES
    assert set(res_wpd.candidates) == {500, 5000}


def test_fractional_scale_boundary_and_arbitrary_bases(engine):
    # Arbitrary base with half crore
    res1 = engine.parse("send six and a half crore rupees")
    assert res1.status == ParseStatus.PARSED
    assert res1.amount_inr == 65_000_000

    res2 = engine.parse("seven and a half lakh")
    assert res2.status == ParseStatus.PARSED
    assert res2.amount_inr == 750_000

    # Exceeding ceiling 100,000,000 via fractional scale
    res_oob = engine.parse("twenty and a half crore")
    assert res_oob.status == ParseStatus.AMBIGUOUS
    assert res_oob.ambiguity_reason == AmbiguityReason.OUT_OF_BOUNDS


def test_trailing_self_correction_aborts(engine):
    # Trailing abort phrases without a new target amount
    res1 = engine.parse("send 500 no wait")
    assert res1.status == ParseStatus.AMBIGUOUS
    assert res1.ambiguity_reason in (AmbiguityReason.SELF_CORRECTION, AmbiguityReason.UNRESOLVED_WORDS)

    res2 = engine.parse("send 500 cancel that")
    assert res2.status == ParseStatus.AMBIGUOUS
    assert res2.ambiguity_reason in (AmbiguityReason.SELF_CORRECTION, AmbiguityReason.UNRESOLVED_WORDS)


def test_unicode_nfc_normalization(engine):
    import unicodedata
    # NFD decomposed string vs NFC composed
    nfd_hi = unicodedata.normalize("NFD", "पाँच सौ रुपये")
    res_hi = engine.parse(nfd_hi)
    assert res_hi.status == ParseStatus.PARSED
    assert res_hi.amount_inr == 500

    nfd_te = unicodedata.normalize("NFD", "ఐదు వందల రూపాయలు")
    res_te = engine.parse(nfd_te)
    assert res_te.status == ParseStatus.PARSED
    assert res_te.amount_inr == 500


def test_contact_phone_and_year_masking(engine):
    # Phone / contact numbers should not be treated as amounts
    res1 = engine.parse("call 2345678")
    assert res1.status == ParseStatus.UNRECOGNIZED

    # Standalone calendar year preceded by preposition
    res2 = engine.parse("transfer on 2024")
    assert res2.status == ParseStatus.UNRECOGNIZED

    # Legitimate amount alongside year
    res3 = engine.parse("transfer 500 on 2024")
    assert res3.status == ParseStatus.PARSED
    assert res3.amount_inr == 500
