"""Unified Multilingual Indic Amount Parsing Engine."""

import re
from typing import Optional, List
from sahi.amounts.models import (
    ParsedAmount, ParseStatus, AmbiguityReason, LanguageGroup
)
from sahi.amounts.normalizer import clean_text, detect_self_correction
from sahi.amounts.english import parse_english_amount
from sahi.amounts.hindi import parse_hindi_amount
from sahi.amounts.telugu import parse_telugu_amount

class AmountEngine:
    """
    Parses spoken or transcribed monetary amounts in Indian English, Hinglish, Hindi, and Telugu
    into exact integer INR values. Returns explicit AMBIGUOUS or UNRECOGNIZED states.
    """

    def parse(self, text: str, preferred_language: LanguageGroup = LanguageGroup.AUTO) -> ParsedAmount:
        cleaned = clean_text(text)
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
            candidates: List[int] = []
            for seg in segments:
                res = self._parse_single(seg)
                if res.status == ParseStatus.PARSED and res.amount_inr is not None:
                    candidates.append(res.amount_inr)
            if len(candidates) >= 2 and len(set(candidates)) > 1:
                return ParsedAmount(
                    raw_text=text,
                    status=ParseStatus.AMBIGUOUS,
                    ambiguity_reason=AmbiguityReason.SELF_CORRECTION,
                    candidates=candidates,
                    confidence=0.85,
                    metadata={"segments": segments, "candidates": candidates}
                )
            elif len(candidates) == 1:
                return ParsedAmount(
                    raw_text=text,
                    status=ParseStatus.PARSED,
                    amount_inr=candidates[0],
                    confidence=0.9,
                    metadata={"resolved_self_correction_to_single": candidates[0]}
                )

        # 2. Detect multiple distinct amounts (e.g. "500 to Ramesh and 1000 to Suresh")
        # Exclude idioms like "and a half" or "aur aadha"
        normalized_for_multi = re.sub(r"\b(and\s+a\s+half|aur\s+aadha)\b", "", cleaned)
        multi_pattern = r"(?:and|aur|mariyu|tatha|,)\s+(?:send|transfer|pay|ivvu|bhejo)?"
        if re.search(r"\b(and|aur|mariyu|tatha)\b", normalized_for_multi):
            sub_parts = re.split(multi_pattern, cleaned)
            if len(sub_parts) > 1:
                sub_candidates: List[int] = []
                for sp in sub_parts:
                    sub_res = self._parse_single(sp)
                    if sub_res.status == ParseStatus.PARSED and sub_res.amount_inr is not None:
                        sub_candidates.append(sub_res.amount_inr)
                if len(sub_candidates) > 1:
                    return ParsedAmount(
                        raw_text=text,
                        status=ParseStatus.AMBIGUOUS,
                        ambiguity_reason=AmbiguityReason.MULTIPLE_AMOUNTS,
                        candidates=sub_candidates,
                        confidence=0.9,
                        metadata={"multi_amount_candidates": sub_candidates}
                    )

        # 3. Standard single amount parsing across engines
        return self._parse_single(cleaned, preferred_language=preferred_language)

    def _parse_single(self, text: str, preferred_language: LanguageGroup = LanguageGroup.AUTO) -> ParsedAmount:
        results: List[ParsedAmount] = []

        # Run language parsers based on preferred language or all
        if preferred_language in (LanguageGroup.AUTO, LanguageGroup.INDIAN_ENGLISH, LanguageGroup.HINGLISH):
            eng_res = parse_english_amount(text)
            if eng_res and eng_res.status == ParseStatus.PARSED:
                results.append(eng_res)

        if preferred_language in (LanguageGroup.AUTO, LanguageGroup.HINDI, LanguageGroup.HINGLISH):
            hindi_res = parse_hindi_amount(text)
            if hindi_res and hindi_res.status == ParseStatus.PARSED:
                results.append(hindi_res)

        if preferred_language in (LanguageGroup.AUTO, LanguageGroup.TELUGU):
            telugu_res = parse_telugu_amount(text)
            if telugu_res and telugu_res.status == ParseStatus.PARSED:
                results.append(telugu_res)

        if not results:
            return ParsedAmount(
                raw_text=text,
                status=ParseStatus.UNRECOGNIZED,
                ambiguity_reason=AmbiguityReason.UNRESOLVED_WORDS,
                confidence=0.0
            )

        # Check for agreement among candidate parses
        unique_amounts = list({r.amount_inr for r in results if r.amount_inr is not None})
        if len(unique_amounts) == 1:
            best_res = max(results, key=lambda r: r.confidence)
            return best_res

        # If different parsers derived different non-zero amounts
        return ParsedAmount(
            raw_text=text,
            status=ParseStatus.AMBIGUOUS,
            ambiguity_reason=AmbiguityReason.CONFLICTING_PARSES,
            candidates=unique_amounts,
            confidence=0.5,
            metadata={"conflicting_results": [r.model_dump() for r in results]}
        )
