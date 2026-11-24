"""Telugu amount parser (Telugu script and Latin transliteration)."""

import re
from typing import Optional
from sahi.amounts.constants import (
    TELUGU_SCALES, TELUGU_SCRIPT, TELUGU_LATIN, COLLOQUIAL_FRACTIONS_TELUGU, MAX_AMOUNT_INR
)
from sahi.amounts.models import ParsedAmount, ParseStatus, AmbiguityReason, LanguageGroup
from sahi.amounts.normalizer import clean_text, strip_currency_tokens

def parse_telugu_amount(text: str) -> Optional[ParsedAmount]:
    cleaned = clean_text(text)
    tokens = strip_currency_tokens(cleaned.split())
    if not tokens:
        return None

    joined = " ".join(tokens)

    # 1. Colloquial Telugu Fractions (e.g. 'rendunnara velu' = 2500, 'moodunnara velu' = 3500, 'sagam laksha' = 50000)
    for frac_word, factor in COLLOQUIAL_FRACTIONS_TELUGU.items():
        pattern = rf"\b{re.escape(frac_word)}\s+(velu|vela|veylu|వేలు|వేల|laksha|lakshalu|లక్ష|లక్షలు|vanda|vandalu|వంద|వందలు)\b"
        match = re.search(pattern, joined)
        if match:
            scale_word = match.group(1)
            mult = TELUGU_SCALES.get(scale_word, 1000)
            total = int(factor * mult)
            if total > MAX_AMOUNT_INR:
                return ParsedAmount(
                    raw_text=text,
                    status=ParseStatus.AMBIGUOUS,
                    ambiguity_reason=AmbiguityReason.OUT_OF_BOUNDS,
                    candidates=[total],
                    confidence=0.5,
                    language_detected=LanguageGroup.TELUGU,
                    tokens_parsed=tokens,
                    metadata={"pattern": "exceeds_maximum_threshold", "amount": total}
                )
            return ParsedAmount(
                raw_text=text,
                status=ParseStatus.PARSED,
                amount_inr=total,
                confidence=0.96,
                language_detected=LanguageGroup.TELUGU,
                tokens_parsed=tokens,
                metadata={"pattern": "telugu_colloquial_fraction", "fraction": frac_word, "scale": mult}
            )

    # 2. Mixed digits and Telugu scales (e.g. "50 velu", "2.5 లక్షలు", "10 lakshalu")
    mixed_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(velu|vela|veylu|వేలు|వేల|laksha|lakshalu|లక్ష|లక్షలు|vanda|vandalu|వంద|వందలు|koti|kotlu|కోటి|కోట్లు)\b", joined)
    if mixed_match:
        num_str, scale_word = mixed_match.groups()
        try:
            val = float(num_str)
            mult = TELUGU_SCALES.get(scale_word, 1)
            total = int(round(val * mult))
            if total > MAX_AMOUNT_INR:
                return ParsedAmount(
                    raw_text=text,
                    status=ParseStatus.AMBIGUOUS,
                    ambiguity_reason=AmbiguityReason.OUT_OF_BOUNDS,
                    candidates=[total],
                    confidence=0.5,
                    language_detected=LanguageGroup.TELUGU,
                    tokens_parsed=tokens,
                    metadata={"pattern": "exceeds_maximum_threshold", "amount": total}
                )
            return ParsedAmount(
                raw_text=text,
                status=ParseStatus.PARSED,
                amount_inr=total,
                confidence=0.96,
                language_detected=LanguageGroup.TELUGU,
                tokens_parsed=tokens,
                metadata={"pattern": "mixed_digit_telugu_scale"}
            )
        except ValueError:
            pass

    # 3. Standard Telugu Word-by-Word Parsing
    current_chunk = 0
    total = 0
    has_telugu_unit = False

    for token in tokens:
        val = TELUGU_SCRIPT.get(token) or TELUGU_LATIN.get(token)
        if val is not None:
            current_chunk += val
            has_telugu_unit = True
        elif token in TELUGU_SCALES:
            mult = TELUGU_SCALES[token]
            if current_chunk == 0:
                current_chunk = 1
            if mult >= 1_000:
                total += current_chunk * mult
                current_chunk = 0
            else:
                current_chunk *= mult

    total += current_chunk
    if has_telugu_unit and total > 0:
        if total > MAX_AMOUNT_INR:
            return ParsedAmount(
                raw_text=text,
                status=ParseStatus.AMBIGUOUS,
                ambiguity_reason=AmbiguityReason.OUT_OF_BOUNDS,
                candidates=[total],
                confidence=0.5,
                language_detected=LanguageGroup.TELUGU,
                tokens_parsed=tokens,
                metadata={"pattern": "exceeds_maximum_threshold", "amount": total}
            )
        return ParsedAmount(
            raw_text=text,
            status=ParseStatus.PARSED,
            amount_inr=total,
            confidence=0.96,
            language_detected=LanguageGroup.TELUGU,
            tokens_parsed=tokens,
            metadata={"pattern": "telugu_words_accumulated"}
        )

    return None
