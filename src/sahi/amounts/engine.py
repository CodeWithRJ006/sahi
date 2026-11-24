"""Unified Multilingual Indic Amount Parsing Engine."""

import re
from typing import Optional, List
from sahi.amounts.models import (
    ParsedAmount, ParseStatus, AmbiguityReason, LanguageGroup
)
from sahi.amounts.constants import MAX_AMOUNT_INR
from sahi.amounts.normalizer import clean_text, detect_self_correction
from sahi.amounts.english import parse_english_amount
from sahi.amounts.hindi import parse_hindi_amount
from sahi.amounts.telugu import parse_telugu_amount
from sahi.guard.rules import is_power_of_ten_discrepancy, is_phonetic_confusable

class AmountEngine:
    """
    Parses spoken or transcribed monetary amounts in Indian English, Hinglish, Hindi, and Telugu
    into exact integer INR values. Returns explicit AMBIGUOUS or UNRECOGNIZED states.
    """

    def parse(self, text: str, preferred_language: LanguageGroup = LanguageGroup.AUTO) -> ParsedAmount:
        # Zero/negative checks are performed after self‑correction detection (see later).

        cleaned = clean_text(text)
        # Detect self‑correction before any explicit checks so that correction phrases
        # involving zero or negative amounts are handled as AMBIGUOUS rather than UNRECOGNIZED.
        is_correction, segments = detect_self_correction(cleaned)
        if not is_correction:
            if re.search(r"(?:^|[\s(])(?:-|minus|negative|ऋण|மானஸ)\s*\d+", text, re.IGNORECASE):
                return ParsedAmount(
                    raw_text=text,
                    status=ParseStatus.UNRECOGNIZED,
                    ambiguity_reason=AmbiguityReason.OUT_OF_BOUNDS,
                    confidence=0.0,
                    metadata={"error": "negative_amount_not_allowed"}
                )
            if re.search(r"\b(?:0|zero|shunya|sunna|शून्य|సున్నా)\s*(?:rupees?|rs|inr|rupaye|roopayalu)?\b", text, re.IGNORECASE):
                return ParsedAmount(
                    raw_text=text,
                    status=ParseStatus.UNRECOGNIZED,
                    ambiguity_reason=AmbiguityReason.OUT_OF_BOUNDS,
                    confidence=0.0,
                    metadata={"error": "zero_amount_not_allowed"}
                )
        if not cleaned:
            return ParsedAmount(
                raw_text=text,
                status=ParseStatus.UNRECOGNIZED,
                ambiguity_reason=AmbiguityReason.UNRESOLVED_WORDS,
                confidence=0.0
            )

        # 1. Detect self-correction first
        is_correction, segments = detect_self_correction(cleaned)
        if is_correction and len(segments) >= 2:
            # Parse both the preceding segment and the final corrected segment.
            prev_seg = segments[-2]
            final_seg = segments[-1]
            prev_res = self._parse_single(prev_seg, preferred_language=preferred_language)
            final_res = self._parse_single(final_seg, preferred_language=preferred_language)

            # If previous segment did not parse but contains a plain numeric amount, extract it as a fallback.
            fallback_prev_amount = None
            if prev_res.status != ParseStatus.PARSED:
                num_match = re.search(r"\\b(\\d{1,9})\\b", prev_seg)
                if num_match:
                    try:
                        val = int(num_match.group(1))
                        if 0 < val <= MAX_AMOUNT_INR:
                            fallback_prev_amount = val
                    except ValueError:
                        fallback_prev_amount = None
            # Use the fallback amount if available for conflict detection.
            prev_amount_for_check = prev_res.amount_inr if prev_res.amount_inr is not None else fallback_prev_amount

            # If the final segment does not parse cleanly, treat as ambiguous (cannot fallback to previous).
            if final_res.status != ParseStatus.PARSED:
                # Propagate existing ambiguous result (e.g., out‑of‑bounds) to retain candidates.
                if final_res.status == ParseStatus.AMBIGUOUS:
                    return final_res
                return ParsedAmount(
                    raw_text=text,
                    status=ParseStatus.AMBIGUOUS,
                    ambiguity_reason=final_res.ambiguity_reason or AmbiguityReason.UNRESOLVED_WORDS,
                    confidence=0.5,
                    metadata={"self_correction": "unresolved", "segments": segments},
                )

            # Reject zero or negative amounts in the final correction.
            if final_res.amount_inr is None or final_res.amount_inr <= 0:
                return ParsedAmount(
                    raw_text=text,
                    status=ParseStatus.AMBIGUOUS,
                    ambiguity_reason=AmbiguityReason.OUT_OF_BOUNDS,
                    confidence=0.5,
                    metadata={"self_correction": "zero_or_negative", "segments": segments},
                )

            # Detect dash‑based negative corrections that survived cleaning (e.g., "-500").
            if any("-" in seg for seg in segments):
                return ParsedAmount(
                    raw_text=text,
                    status=ParseStatus.AMBIGUOUS,
                    ambiguity_reason=AmbiguityReason.OUT_OF_BOUNDS,
                    confidence=0.5,
                    metadata={"self_correction": "dash_negative", "segments": segments},
                )


            # NOTE: Removed non-numeric correction guard to allow word‑based self-corrections.

            # Detect conflict between preceding and final amounts when amounts differ.
            prev_amt = prev_res.amount_inr if prev_res.amount_inr is not None else fallback_prev_amount
            final_amt = final_res.amount_inr
            if prev_amt is not None and final_amt is not None and prev_amt != final_amt:
                # 1. Critical power-of-ten scale mismatch (e.g. 500 vs 5,000)
                is_p10, _ = is_power_of_ten_discrepancy(prev_amt, final_amt)
                if is_p10:
                    return ParsedAmount(
                        raw_text=text,
                        status=ParseStatus.AMBIGUOUS,
                        ambiguity_reason=AmbiguityReason.SELF_CORRECTION,
                        candidates=[prev_amt, final_amt],
                        confidence=0.5,
                        metadata={"self_correction": "power_of_ten_conflict", "segments": segments},
                    )

                # 2. Phonetic confusable mismatch (e.g. 15,000 vs 50,000)
                if is_phonetic_confusable(prev_amt, final_amt):
                    return ParsedAmount(
                        raw_text=text,
                        status=ParseStatus.AMBIGUOUS,
                        ambiguity_reason=AmbiguityReason.SELF_CORRECTION,
                        candidates=[prev_amt, final_amt],
                        confidence=0.5,
                        metadata={"self_correction": "phonetic_conflict", "segments": segments},
                    )

                # 3. If both lack explicit units but both contain digits, treat as numeric conflict.
                from sahi.amounts.constants import ALL_SCALES, CURRENCY_WORDS
                prev_tokens = set(prev_seg.split())
                final_tokens = set(final_seg.split())
                prev_has_scale = any(tok in ALL_SCALES for tok in prev_tokens)
                final_has_scale = any(tok in ALL_SCALES for tok in final_tokens)
                prev_has_currency = any(tok in CURRENCY_WORDS for tok in prev_tokens)
                final_has_currency = any(tok in CURRENCY_WORDS for tok in final_tokens)
                prev_has_any = prev_has_scale or prev_has_currency
                final_has_any = final_has_scale or final_has_currency

                if not prev_has_any and not final_has_any and re.search(r"\d", prev_seg) and re.search(r"\d", final_seg):
                    return ParsedAmount(
                        raw_text=text,
                        status=ParseStatus.AMBIGUOUS,
                        ambiguity_reason=AmbiguityReason.SELF_CORRECTION,
                        candidates=[prev_amt, final_amt],
                        confidence=0.5,
                        metadata={"self_correction": "numeric_conflict", "segments": segments},
                    )

                # Default for valid self-corrections: accept the final amount.
                return ParsedAmount(
                    raw_text=text,
                    status=ParseStatus.PARSED,
                    amount_inr=final_amt,
                    confidence=0.9,
                    metadata={"resolved_self_correction_to_single": final_amt, "segments": segments},
                )

            # Otherwise, accept the corrected amount.
            return ParsedAmount(
                raw_text=text,
                status=ParseStatus.PARSED,
                amount_inr=final_res.amount_inr,
                confidence=0.9,
                metadata={"resolved_self_correction_to_single": final_res.amount_inr, "segments": segments},
            )

        # 2. Check for conflicting/disjunctive amounts (e.g. "send 500 or 1000 rupees", "500 ya 1000 bhejo")
        if re.search(r"\b(or|ya|athava|leda)\b", cleaned, re.IGNORECASE):
            or_parts = re.split(r"\b(?:or|ya|athava|leda)\b", cleaned, flags=re.IGNORECASE)
            if len(or_parts) > 1:
                or_candidates: List[int] = []
                for op in or_parts:
                    op_res = self._parse_single(op, preferred_language=preferred_language)
                    if op_res.status == ParseStatus.PARSED and op_res.amount_inr is not None:
                        or_candidates.append(op_res.amount_inr)
                if len(or_candidates) > 1 and len(set(or_candidates)) > 1:
                    return ParsedAmount(
                        raw_text=text,
                        status=ParseStatus.AMBIGUOUS,
                        ambiguity_reason=AmbiguityReason.CONFLICTING_PARSES,
                        candidates=or_candidates,
                        confidence=0.5,
                        metadata={"disjunctive_candidates": or_candidates}
                    )

        # 3. Detect multiple distinct amounts (e.g. "500 to Ramesh and 1000 to Suresh", "500, 1000")
        normalized_for_multi = re.sub(r"\b(and\s+a\s+half|aur\s+aadha)\b", "", cleaned)
        multi_pattern = r"(?:and|aur|mariyu|tatha|,)\s*(?:send|transfer|pay|ivvu|bhejo)?"
        if re.search(r"\b(and|aur|mariyu|tatha)\b|,", normalized_for_multi):
            sub_parts = re.split(multi_pattern, cleaned)
            if len(sub_parts) > 1:
                sub_candidates: List[int] = []
                for sp in sub_parts:
                    sub_res = self._parse_single(sp, preferred_language=preferred_language)
                    if sub_res.status == ParseStatus.PARSED and sub_res.amount_inr is not None:
                        sub_candidates.append(sub_res.amount_inr)
                if len(sub_candidates) > 1 and len(set(sub_candidates)) > 1:
                    return ParsedAmount(
                        raw_text=text,
                        status=ParseStatus.AMBIGUOUS,
                        ambiguity_reason=AmbiguityReason.MULTIPLE_AMOUNTS,
                        candidates=sub_candidates,
                        confidence=0.9,
                        metadata={"multi_amount_candidates": sub_candidates}
                    )

        # 4. Detect word-plus-digit contradiction (e.g. "send 500 five thousand rupees")
        digit_match = re.search(r"\b(\d+(?:,\d+)*(?:\.\d+)?)\b", cleaned)
        if digit_match:
            words_only = re.sub(r"\b\d+(?:,\d+)*(?:\.\d+)?\b", " ", cleaned).strip()
            from sahi.amounts.constants import ALL_SCALES, ENGLISH_UNITS, HINDI_DEVANAGARI, HINDI_LATIN, TELUGU_SCRIPT, TELUGU_LATIN
            word_tokens = words_only.split()
            has_number_words = any(
                w in ALL_SCALES or w in ENGLISH_UNITS or w in HINDI_DEVANAGARI
                or w in HINDI_LATIN or w in TELUGU_SCRIPT or w in TELUGU_LATIN
                for w in word_tokens
            )
            if has_number_words:
                words_res = self._parse_single(words_only, preferred_language=preferred_language)
                if words_res.status == ParseStatus.PARSED and words_res.amount_inr is not None:
                    digit_str = digit_match.group(1).replace(",", "")
                    try:
                        digit_val = int(float(digit_str))
                        if digit_val != words_res.amount_inr:
                            return ParsedAmount(
                                raw_text=text,
                                status=ParseStatus.AMBIGUOUS,
                                ambiguity_reason=AmbiguityReason.CONFLICTING_PARSES,
                                candidates=sorted([digit_val, words_res.amount_inr]),
                                confidence=0.5,
                                metadata={"contradiction": "word_plus_digit", "digit_val": digit_val, "word_val": words_res.amount_inr}
                            )
                    except ValueError:
                        pass

        # 5. Standard single amount parsing across engines
        res = self._parse_single(cleaned, preferred_language=preferred_language)
        if res.status == ParseStatus.PARSED and res.amount_inr is not None and res.amount_inr > MAX_AMOUNT_INR:
            return ParsedAmount(
                raw_text=text,
                status=ParseStatus.AMBIGUOUS,
                ambiguity_reason=AmbiguityReason.OUT_OF_BOUNDS,
                candidates=[res.amount_inr],
                confidence=0.5,
                language_detected=res.language_detected,
                tokens_parsed=res.tokens_parsed,
                metadata={"pattern": "exceeds_maximum_threshold", "amount": res.amount_inr}
            )
        return res

    def _parse_single(self, text: str, preferred_language: LanguageGroup = LanguageGroup.AUTO) -> ParsedAmount:
        results: List[ParsedAmount] = []
        ambiguous_results: List[ParsedAmount] = []
        unrecognized_results: List[ParsedAmount] = []

        if preferred_language in (LanguageGroup.AUTO, LanguageGroup.INDIAN_ENGLISH, LanguageGroup.HINGLISH):
            eng_res = parse_english_amount(text)
            if eng_res:
                if eng_res.status == ParseStatus.PARSED:
                    results.append(eng_res)
                elif eng_res.status == ParseStatus.AMBIGUOUS:
                    ambiguous_results.append(eng_res)
                elif eng_res.status == ParseStatus.UNRECOGNIZED and eng_res.ambiguity_reason != AmbiguityReason.UNRESOLVED_WORDS:
                    unrecognized_results.append(eng_res)

        if preferred_language in (LanguageGroup.AUTO, LanguageGroup.HINDI, LanguageGroup.HINGLISH):
            hindi_res = parse_hindi_amount(text)
            if hindi_res:
                if hindi_res.status == ParseStatus.PARSED:
                    results.append(hindi_res)
                elif hindi_res.status == ParseStatus.AMBIGUOUS:
                    ambiguous_results.append(hindi_res)
                elif hindi_res.status == ParseStatus.UNRECOGNIZED and hindi_res.ambiguity_reason != AmbiguityReason.UNRESOLVED_WORDS:
                    unrecognized_results.append(hindi_res)

        if preferred_language in (LanguageGroup.AUTO, LanguageGroup.TELUGU):
            telugu_res = parse_telugu_amount(text)
            if telugu_res:
                if telugu_res.status == ParseStatus.PARSED:
                    results.append(telugu_res)
                elif telugu_res.status == ParseStatus.AMBIGUOUS:
                    ambiguous_results.append(telugu_res)
                elif telugu_res.status == ParseStatus.UNRECOGNIZED and telugu_res.ambiguity_reason != AmbiguityReason.UNRESOLVED_WORDS:
                    unrecognized_results.append(telugu_res)

        valid_results: List[ParsedAmount] = []
        for r in results:
            if r.amount_inr is not None and r.amount_inr > MAX_AMOUNT_INR:
                ambiguous_results.append(
                    ParsedAmount(
                        raw_text=text,
                        status=ParseStatus.AMBIGUOUS,
                        ambiguity_reason=AmbiguityReason.OUT_OF_BOUNDS,
                        candidates=[r.amount_inr],
                        confidence=0.5,
                        language_detected=r.language_detected,
                        tokens_parsed=r.tokens_parsed,
                        metadata={"pattern": "exceeds_maximum_threshold", "amount": r.amount_inr}
                    )
                )
            else:
                valid_results.append(r)
        results = valid_results

        if not results:
            if ambiguous_results:
                return ambiguous_results[0]
            if unrecognized_results:
                return unrecognized_results[0]
            return ParsedAmount(
                raw_text=text,
                status=ParseStatus.UNRECOGNIZED,
                ambiguity_reason=AmbiguityReason.UNRESOLVED_WORDS,
                confidence=0.0
            )

        unique_amounts = list({r.amount_inr for r in results if r.amount_inr is not None})
        if len(unique_amounts) == 1:
            best_res = max(results, key=lambda r: r.confidence)
            return best_res

        return ParsedAmount(
            raw_text=text,
            status=ParseStatus.AMBIGUOUS,
            ambiguity_reason=AmbiguityReason.CONFLICTING_PARSES,
            candidates=unique_amounts,
            confidence=0.5,
            metadata={"conflicting_results": [r.model_dump() for r in results]}
        )