"""Data models for amount parsing in SAHI."""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ParseStatus(str, Enum):
    PARSED = "PARSED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRECOGNIZED = "UNRECOGNIZED"

class AmbiguityReason(str, Enum):
    NONE = "NONE"
    MULTIPLE_AMOUNTS = "MULTIPLE_AMOUNTS"
    SELF_CORRECTION = "SELF_CORRECTION"
    UNRESOLVED_WORDS = "UNRESOLVED_WORDS"
    FRACTION_AMBIGUITY = "FRACTION_AMBIGUITY"
    CONFLICTING_PARSES = "CONFLICTING_PARSES"
    OUT_OF_BOUNDS = "OUT_OF_BOUNDS"

class LanguageGroup(str, Enum):
    HINDI = "HINDI"
    TELUGU = "TELUGU"
    HINGLISH = "HINGLISH"
    INDIAN_ENGLISH = "INDIAN_ENGLISH"
    AUTO = "AUTO"

class ParsedAmount(BaseModel):
    raw_text: str
    status: ParseStatus
    amount_inr: Optional[int] = Field(
        default=None,
        description="Exact integer INR value. Null if status != PARSED."
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Confidence score for this extraction."
    )
    language_detected: LanguageGroup = LanguageGroup.AUTO
    ambiguity_reason: AmbiguityReason = AmbiguityReason.NONE
    candidates: List[int] = Field(
        default_factory=list,
        description="Candidate amounts found when multiple or self-corrected amounts are detected."
    )
    tokens_parsed: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
