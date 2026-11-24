"""Text normalization and pre-processing utilities for Indic amount parsing."""

import re
import unicodedata
from typing import Tuple, List
from sahi.amounts.constants import SELF_CORRECTION_PHRASES, CURRENCY_WORDS

INDIAN_COMMA_RE = re.compile(r"\b\d{1,2}(?:,\d{2})+,\d{3}(?:\.\d+)?\b")
STANDARD_COMMA_RE = re.compile(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b")
DATE_RE = re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b")
ACCOUNT_RE = re.compile(r"\b(?:account|ac|a/c)(?:\s+(?:number|no|num))?\s*[:#]?\s*(\d{9,18})\b", re.IGNORECASE)
# Phone / contact number patterns – only mask numbers that appear in a contact context.
PHONE_WITH_CONTEXT_RE = re.compile(
    r"\b(?:to|call|phone|mobile|number|no|contact|tel|dial|telephone)\s*[:#]?\s*(?:\+?91[\s-]?)?(\d{7,11})\b"
    r"(?!\s*(?:rupees?|rs|inr|rupaye|roopayalu))",
    re.IGNORECASE,
)
# Mask bare 10‑digit numbers only when they are not followed by a currency token.
PHONE_BARE_RE = re.compile(
    r"\b([6-9]\d{9})\b"
    r"(?!\s*(?:rupees?|rs|inr|rupaye|roopayalu))",
    re.IGNORECASE,
)
# Date‑only numeric strings (YYYYMMDD or DDMMYYYY) without separators – treat as dates.
DATE_BARE_RE = re.compile(r"\b\d{8}\b(?!\s*(?:rupees?|rs|inr|rupaye|roopayalu))", re.IGNORECASE)
# 4-digit calendar years preceded by date/time prepositions
YEAR_RE = re.compile(
    r"\b(?:on|in|date|dated|year|saal|samvatsaram)\s+(?:19\d\d|20\d\d)\b"
    r"(?!\s*(?:rupees?|rs|inr|rupaye|roopayalu))",
    re.IGNORECASE,
)

def clean_text(text: str) -> str:
    """Normalize whitespace, Unicode NFC form, lowercases, and strips punctuation except decimal dots."""
    if not text:
        return ""
    # Unicode NFC normalization to ensure decomposed accents/nuktas are normalized
    text = unicodedata.normalize("NFC", text).strip().lower()
    # 1. Normalize commas in validly grouped numbers (1,23,456 or 10,000)
    text = INDIAN_COMMA_RE.sub(lambda m: m.group(0).replace(",", ""), text)
    text = STANDARD_COMMA_RE.sub(lambda m: m.group(0).replace(",", ""), text)
    # 2. Mask dates (e.g. 15/08/2024, 12-05-2024) so days/years are not mistaken for amounts
    text = DATE_RE.sub(" ", text)
    text = YEAR_RE.sub(" ", text)
    # 3. Mask account numbers (e.g. account 123456789012)
    text = ACCOUNT_RE.sub(" ", text)
    # 4. Mask phone numbers / recipient identifiers
    text = PHONE_WITH_CONTEXT_RE.sub(" ", text)
    text = PHONE_BARE_RE.sub(" ", text)
    # 5. Mask bare date-like numeric strings without separators
    text = DATE_BARE_RE.sub(" ", text)
    # 6. Replace currency symbols
    text = re.sub(r"[₹$]", "", text)
    # 7. Preserve commas as delimiter tokens with spaces around them
    text = re.sub(r",", " , ", text)
    # 8. Remove punctuation except decimal dots within numbers
    text = re.sub(r"[!?:;\"'()[\]{}|/\\]", " ", text)
    # 9. Normalize spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text

def detect_self_correction(text: str) -> Tuple[bool, List[str]]:
    """
    Checks if an utterance contains self-correction phrases (e.g. 'no wait', 'nahi nahi', 'kadu', 'cancel that').
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
            elif len(cleaned_parts) == 1:
                # Trailing self-correction or abort phrase with no replacement amount
                return True, [cleaned_parts[0], ""]
    return False, [text]

def strip_currency_tokens(tokens: List[str]) -> List[str]:
    """Strips currency denominative words like 'rupees', 'rs', 'inr', 'rupaye' and delimiter commas."""
    return [t for t in tokens if t not in CURRENCY_WORDS and t != ","]