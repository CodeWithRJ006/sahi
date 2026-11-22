"""Text normalization and pre-processing utilities for Indic amount parsing."""

import re
from typing import Tuple, List
from sahi.amounts.constants import SELF_CORRECTION_PHRASES, CURRENCY_WORDS

def clean_text(text: str) -> str:
    """Normalize whitespace, lowercases, and strips punctuation except decimal dots."""
    if not text:
        return ""
    text = text.strip().lower()
    # Replace currency symbols
    text = re.sub(r"[₹$]", "", text)
    # Replace commas in numbers (e.g., 50,000 -> 50000)
    text = re.sub(r"(?<=\d),(?=\d)", "", text)
    # Remove punctuation except dots within numbers or words
    text = re.sub(r"[!?,:;\"'()[\]{}|/\\]", " ", text)
    # Normalize spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text

def detect_self_correction(text: str) -> Tuple[bool, List[str]]:
    """
    Checks if an utterance contains self-correction phrases (e.g. 'no wait', 'nahi nahi', 'kadu').
    Returns (has_self_correction, list_of_segments).
    """
    lower = text.lower()
    for phrase in SELF_CORRECTION_PHRASES:
        pattern = r"\b" + re.escape(phrase) + r"\b"
        if re.search(pattern, lower):
            parts = re.split(pattern, lower)
            cleaned_parts = [p.strip() for p in parts if p.strip()]
            if len(cleaned_parts) >= 2:
                return True, cleaned_parts
    return False, [text]

def strip_currency_tokens(tokens: List[str]) -> List[str]:
    """Strips currency denominative words like 'rupees', 'rs', 'inr', 'rupaye'."""
    return [t for t in tokens if t not in CURRENCY_WORDS]
