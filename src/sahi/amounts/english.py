"""Indian English and Hinglish amount parser."""

import re
from typing import Optional
from sahi.amounts.constants import ENGLISH_SCALES, ENGLISH_UNITS
from sahi.amounts.models import ParsedAmount, ParseStatus, LanguageGroup
from sahi.amounts.normalizer import clean_text, strip_currency_tokens

def parse_english_amount(text: str) -> Optional[ParsedAmount]:
    cleaned = clean_text(text)
    tokens = strip_currency_tokens(cleaned.split())
    if not tokens:
        return None

    joined = " ".join(tokens)

    # 1. Number (integer or decimal) + optional English scale (e.g. "5000", "5k", "2.5 lakh", "1.5 crore")
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(k|thousand|thousands|hundred|hundreds|lakh|lakhs|lac|lacs|crore|crores)?\b", joined)
    if match:
        num_str, scale_str = match.groups()
        try:
            val = float(num_str)
            multiplier = 1
            if scale_str:
                multiplier = ENGLISH_SCALES.get(scale_str.lower(), 1)
            total = int(round(val * multiplier))
            if total > 0:
                return ParsedAmount(
                    raw_text=text,
                    status=ParseStatus.PARSED,
                    amount_inr=total,
                    confidence=0.98,
                    language_detected=LanguageGroup.INDIAN_ENGLISH,
                    tokens_parsed=tokens,
                    metadata={"pattern": "numeric_with_scale", "numeric_val": val, "scale": multiplier}
                )
        except ValueError:
            pass

    # 2. Check for "two and a half lakhs", "one and a half crore", "half a lakh"
    fractional_scale_match = re.search(r"\b(one|two|three|four|five)?\s*and\s*a\s*half\s*(lakh|lakhs|crore|crores|thousand|thousands)\b", joined)
    if fractional_scale_match:
        base_word, scale_str = fractional_scale_match.groups()
        base = ENGLISH_UNITS.get(base_word, 0)
        multiplier = ENGLISH_SCALES.get(scale_str.lower(), 100_000)
        total = int((base + 0.5) * multiplier)
        return ParsedAmount(
            raw_text=text,
            status=ParseStatus.PARSED,
            amount_inr=total,
            confidence=0.95,
            language_detected=LanguageGroup.INDIAN_ENGLISH,
            tokens_parsed=tokens,
            metadata={"pattern": "fractional_words"}
        )

    if "half a lakh" in joined or "half lakh" in joined:
        return ParsedAmount(
            raw_text=text,
            status=ParseStatus.PARSED,
            amount_inr=50_000,
            confidence=0.95,
            language_detected=LanguageGroup.INDIAN_ENGLISH,
            tokens_parsed=tokens,
            metadata={"pattern": "half_lakh"}
        )

    # 3. Colloquial hundred multiplier, e.g. "twenty five hundred" (2500)
    hundred_match = re.search(r"\b(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\s*(one|two|three|four|five|six|seven|eight|nine)?\s*hundred\b", joined)
    if hundred_match:
        tens_word, units_word = hundred_match.groups()
        tens = ENGLISH_UNITS.get(tens_word, 0)
        units = ENGLISH_UNITS.get(units_word, 0) if units_word else 0
        total = (tens + units) * 100
        return ParsedAmount(
            raw_text=text,
            status=ParseStatus.PARSED,
            amount_inr=total,
            confidence=0.95,
            language_detected=LanguageGroup.INDIAN_ENGLISH,
            tokens_parsed=tokens,
            metadata={"pattern": "colloquial_hundreds"}
        )

    # 4. Standard word-by-word accumulation
    current_chunk = 0
    total = 0
    has_english_unit = False

    for token in tokens:
        if token in ENGLISH_UNITS:
            current_chunk += ENGLISH_UNITS[token]
            has_english_unit = True
        elif token in ENGLISH_SCALES:
            mult = ENGLISH_SCALES[token]
            if current_chunk == 0:
                current_chunk = 1
            if mult >= 1_000:
                total += current_chunk * mult
                current_chunk = 0
            else:
                current_chunk *= mult

    total += current_chunk
    if has_english_unit and total > 0:
        return ParsedAmount(
            raw_text=text,
            status=ParseStatus.PARSED,
            amount_inr=total,
            confidence=0.95,
            language_detected=LanguageGroup.INDIAN_ENGLISH,
            tokens_parsed=tokens,
            metadata={"pattern": "words_accumulated"}
        )

    return None
