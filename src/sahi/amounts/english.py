"""Indian English and Hinglish amount parser."""

import re
from typing import Optional
from sahi.amounts.constants import ALL_SCALES, ENGLISH_SCALES, ENGLISH_UNITS, MAX_AMOUNT_INR
from sahi.amounts.models import ParsedAmount, ParseStatus, AmbiguityReason, LanguageGroup
from sahi.amounts.normalizer import clean_text, strip_currency_tokens

RUPEES_AND_PAISE_RE = re.compile(
    r"\b(\d+)\s*(?:rupees?|rs|inr|rupaye|roopayalu)\s*(?:and\s+)?(\d+)\s*(?:paise|paisa|పైసలు|पैसे)\b|\b(\d+)\s+and\s+(\d+)\s*(?:paise|paisa|పైసలు|पैसे)\b",
    re.IGNORECASE
)
PAISE_ONLY_RE = re.compile(r"\b(\d+)\s*(?:paise|paisa|పైసలు|पैसे)\b", re.IGNORECASE)

def parse_english_amount(text: str) -> Optional[ParsedAmount]:
    cleaned = clean_text(text)

    # Check for paise expressions
    m_both = RUPEES_AND_PAISE_RE.search(cleaned)
    if m_both:
        r = int(m_both.group(1) or m_both.group(3))
        p = int(m_both.group(2) or m_both.group(4))
        return ParsedAmount(
            raw_text=text,
            status=ParseStatus.AMBIGUOUS,
            ambiguity_reason=AmbiguityReason.FRACTION_AMBIGUITY,
            candidates=[r],
            confidence=0.85,
            language_detected=LanguageGroup.INDIAN_ENGLISH,
            tokens_parsed=[str(r), str(p), "paise"],
            metadata={"rupees": r, "paise": p, "exact_amount": r + p / 100.0}
        )

    m_only = PAISE_ONLY_RE.search(cleaned)
    if m_only:
        p = int(m_only.group(1))
        return ParsedAmount(
            raw_text=text,
            status=ParseStatus.UNRECOGNIZED,
            ambiguity_reason=AmbiguityReason.OUT_OF_BOUNDS,
            confidence=0.0,
            language_detected=LanguageGroup.INDIAN_ENGLISH,
            tokens_parsed=[str(p), "paise"],
            metadata={"error": "sub_rupee_amount_cannot_be_settled", "paise": p}
        )

    tokens = strip_currency_tokens(cleaned.split())
    if not tokens:
        return None

    joined = " ".join(tokens)

    # 1. Number (integer or decimal) + optional scale (e.g. "5000", "5k", "2.5 lakh", "1.5 crore", "5 hazar")
    scale_keys = "|".join(re.escape(k) for k in sorted(ALL_SCALES.keys(), key=len, reverse=True))
    match = re.search(rf"\b(\d+(?:\.\d+)?)\s*({scale_keys})?\b", joined)
    if match:
        num_str, scale_str = match.groups()
        try:
            val = float(num_str)
            multiplier = 1
            if scale_str:
                multiplier = ALL_SCALES.get(scale_str.lower(), 1)
            raw_total = val * multiplier

            # If there is a non-zero fractional paise (e.g. 12.75 rupees), do not silently round
            if raw_total % 1 != 0:
                int_part = int(raw_total)
                return ParsedAmount(
                    raw_text=text,
                    status=ParseStatus.AMBIGUOUS,
                    ambiguity_reason=AmbiguityReason.FRACTION_AMBIGUITY,
                    candidates=[int_part],
                    confidence=0.85,
                    language_detected=LanguageGroup.INDIAN_ENGLISH,
                    tokens_parsed=tokens,
                    metadata={"pattern": "fractional_decimal_paise", "exact_amount": raw_total}
                )

            total = int(round(raw_total))

            # Disallow zero or negative values
            if total <= 0:
                return ParsedAmount(
                    raw_text=text,
                    status=ParseStatus.UNRECOGNIZED,
                    ambiguity_reason=AmbiguityReason.OUT_OF_BOUNDS,
                    confidence=0.0,
                    metadata={"error": "non_positive_amount"}
                )

            # Check upper limit boundary (> 10 crore)
            if total > MAX_AMOUNT_INR:
                return ParsedAmount(
                    raw_text=text,
                    status=ParseStatus.AMBIGUOUS,
                    ambiguity_reason=AmbiguityReason.OUT_OF_BOUNDS,
                    candidates=[total],
                    confidence=0.5,
                    language_detected=LanguageGroup.INDIAN_ENGLISH,
                    tokens_parsed=tokens,
                    metadata={"pattern": "exceeds_maximum_threshold", "amount": total}
                )

            # Check if there are other unparsed numeric digits in tokens (e.g. "500 1000")
            numeric_tokens = [t for t in tokens if re.match(r"^\d+(?:\.\d+)?$", t)]
            if len(numeric_tokens) > 1:
                sub_cands = [int(float(t)) for t in numeric_tokens if float(t) > 0]
                if len(set(sub_cands)) > 1:
                    return ParsedAmount(
                        raw_text=text,
                        status=ParseStatus.AMBIGUOUS,
                        ambiguity_reason=AmbiguityReason.MULTIPLE_AMOUNTS,
                        candidates=sub_cands,
                        confidence=0.85,
                        language_detected=LanguageGroup.INDIAN_ENGLISH,
                        tokens_parsed=tokens,
                        metadata={"pattern": "multiple_unparsed_numerics"}
                    )

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

    # 2. Check for "two and a half lakhs", "one and a half crore", "twenty and a half crore", "half a lakh"
    fractional_scale_match = re.search(
        r"\b(?:(.*?)\s+)?and\s+a\s+half\s+(lakh|lakhs|lac|lacs|crore|crores|thousand|thousands)\b",
        joined,
        re.IGNORECASE
    )
    if fractional_scale_match:
        prefix, scale_str = fractional_scale_match.groups()
        multiplier = ALL_SCALES.get(scale_str.lower(), 100_000)
        base = 0.0
        if prefix:
            words = prefix.strip().split()
            curr = 0
            tot = 0.0
            valid = False
            for w in words:
                if re.match(r"^\d+(?:\.\d+)?$", w):
                    tot += float(w)
                    valid = True
                elif w in ENGLISH_UNITS:
                    v = ENGLISH_UNITS[w]
                    if v >= 100:
                        tot += curr * v if curr else v
                        curr = 0
                    else:
                        curr += v
                    valid = True
                elif w in ("send", "transfer", "pay", "please", "to", "rupees", "rs", "inr"):
                    continue
                else:
                    valid = False
                    break
            tot += curr
            if not valid and tot == 0:
                return ParsedAmount(
                    raw_text=text,
                    status=ParseStatus.AMBIGUOUS,
                    ambiguity_reason=AmbiguityReason.UNRESOLVED_WORDS,
                    confidence=0.5,
                    language_detected=LanguageGroup.INDIAN_ENGLISH,
                    tokens_parsed=tokens,
                    metadata={"error": "unresolved_fractional_prefix"}
                )
            base = tot

        total = int(round((base + 0.5) * multiplier))
        if total > MAX_AMOUNT_INR:
            return ParsedAmount(
                raw_text=text,
                status=ParseStatus.AMBIGUOUS,
                ambiguity_reason=AmbiguityReason.OUT_OF_BOUNDS,
                candidates=[total],
                confidence=0.5,
                language_detected=LanguageGroup.INDIAN_ENGLISH,
                tokens_parsed=tokens,
                metadata={"pattern": "exceeds_maximum_threshold", "amount": total}
            )
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
