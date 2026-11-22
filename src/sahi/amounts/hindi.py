"""Hindi and Hinglish amount parser (Devanagari script and Latin transliteration)."""

import re
from typing import Optional
from sahi.amounts.constants import (
    HINDI_SCALES, HINDI_DEVANAGARI, HINDI_LATIN, COLLOQUIAL_FRACTIONS_HINDI
)
from sahi.amounts.models import ParsedAmount, ParseStatus, LanguageGroup
from sahi.amounts.normalizer import clean_text, strip_currency_tokens

def parse_hindi_amount(text: str) -> Optional[ParsedAmount]:
    cleaned = clean_text(text)
    tokens = strip_currency_tokens(cleaned.split())
    if not tokens:
        return None

    joined = " ".join(tokens)

    # 1. Colloquial Hindi Fractions: "sadhe / साढ़े" + number + scale
    sadhe_match = re.search(r"\b(sadhe|साढ़े)\s+(\S+)\s+(hazar|हज़ार|हजार|lakh|लाख|karod|करोड़)\b", joined)
    if sadhe_match:
        _, num_word, scale_word = sadhe_match.groups()
        base = HINDI_LATIN.get(num_word) or HINDI_DEVANAGARI.get(num_word)
        mult = HINDI_SCALES.get(scale_word)
        if base and mult:
            total = int((base + 0.5) * mult)
            return ParsedAmount(
                raw_text=text,
                status=ParseStatus.PARSED,
                amount_inr=total,
                confidence=0.96,
                language_detected=LanguageGroup.HINDI,
                tokens_parsed=tokens,
                metadata={"pattern": "hindi_sadhe_fraction", "base": base, "scale": mult}
            )

    # Colloquial fixed fractions: "dedh", "dhai", "aadha" + scale
    for frac_word, factor in COLLOQUIAL_FRACTIONS_HINDI.items():
        pattern = rf"\b{re.escape(frac_word)}\s+(hazar|हज़ार|हजार|lakh|लाख|karod|करोड़|sau|सौ)\b"
        match = re.search(pattern, joined)
        if match:
            scale_word = match.group(1)
            mult = HINDI_SCALES.get(scale_word, 1000)
            total = int(factor * mult)
            return ParsedAmount(
                raw_text=text,
                status=ParseStatus.PARSED,
                amount_inr=total,
                confidence=0.96,
                language_detected=LanguageGroup.HINDI,
                tokens_parsed=tokens,
                metadata={"pattern": "hindi_colloquial_fraction", "fraction": frac_word, "scale": mult}
            )

    # 2. Mixed digits and Hindi scales (e.g., "50 hazar", "2.5 लाख", "10 lakh")
    mixed_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(hazar|हज़ार|हजार|lakh|लाख|karod|करोड़|sau|सौ)\b", joined)
    if mixed_match:
        num_str, scale_word = mixed_match.groups()
        try:
            val = float(num_str)
            mult = HINDI_SCALES.get(scale_word, 1)
            total = int(round(val * mult))
            return ParsedAmount(
                raw_text=text,
                status=ParseStatus.PARSED,
                amount_inr=total,
                confidence=0.96,
                language_detected=LanguageGroup.HINDI,
                tokens_parsed=tokens,
                metadata={"pattern": "mixed_digit_hindi_scale"}
            )
        except ValueError:
            pass

    # 3. Standard Hindi Word-by-Word Parsing
    # Disambiguate English verb 'do' (e.g. 'do something', 'please do', 'how do')
    COMMON_ENGLISH_WORDS = {"please", "something", "anything", "not", "this", "that", "it", "how", "what", "can", "you", "namaste"}
    has_english_context = any(t in COMMON_ENGLISH_WORDS for t in tokens)

    current_chunk = 0
    total = 0
    has_hindi_unit = False
    has_hindi_scale = False
    matched_tokens_count = 0

    for token in tokens:
        # Ignore English 'do' when surrounded by English prose
        if token == "do" and has_english_context:
            continue

        val = HINDI_DEVANAGARI.get(token) or HINDI_LATIN.get(token)
        if val is not None:
            current_chunk += val
            has_hindi_unit = True
            matched_tokens_count += 1
        elif token in HINDI_SCALES:
            mult = HINDI_SCALES[token]
            has_hindi_scale = True
            matched_tokens_count += 1
            if current_chunk == 0:
                current_chunk = 1
            if mult >= 1_000:
                total += current_chunk * mult
                current_chunk = 0
            else:
                current_chunk *= mult

    total += current_chunk

    # Require either a scale word OR significant number of matched tokens relative to total tokens
    # e.g., prevents isolated homophone matching in conversational sentences
    is_valid_extraction = (
        (has_hindi_scale and has_hindi_unit) or
        (has_hindi_unit and matched_tokens_count >= len(tokens) / 2) or
        (has_hindi_unit and any(w in cleaned for w in ["rupaye", "rupee", "rupees", "bhejo", "transfer", "send"]))
    )

    if has_hindi_unit and total > 0 and is_valid_extraction:
        return ParsedAmount(
            raw_text=text,
            status=ParseStatus.PARSED,
            amount_inr=total,
            confidence=0.96,
            language_detected=LanguageGroup.HINDI,
            tokens_parsed=tokens,
            metadata={"pattern": "hindi_words_accumulated"}
        )

    return None
