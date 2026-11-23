"""Pilot dataset definitions and schemas for SAHI Indic monetary benchmark."""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class UtteranceCategory(str, Enum):
    PLAIN_AMOUNT = "plain_amount"
    LAKH_CRORE = "lakh_crore"
    FRACTIONAL = "fractional"
    CONFUSABLE = "confusable"
    CODEMIX = "codemix"
    SELF_CORRECTION = "self_correction"

class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    NEEDS_NATIVE_REVIEW = "needs_native_review"

class BaseUtterance(BaseModel):
    """
    Ground-truth utterance record.
    Keeps intended ground truth separate from downstream model candidate readings.
    """
    id: str = Field(..., description="Unique utterance identifier (e.g. 'UTT_HI_001')")
    language_group: str = Field(..., description="INDIAN_ENGLISH, HINDI, TELUGU, HINGLISH")
    category: UtteranceCategory
    intended_amount_inr: Optional[int] = Field(None, description="Ground truth target integer INR amount")
    candidate_amounts: List[int] = Field(default_factory=list, description="Ground truth candidate amounts for self-correction or multi-amounts")
    native_text: str = Field(..., description="Prompt in native script (Devanagari, Telugu, or Latin)")
    romanized_text: Optional[str] = Field(None, description="Romanized Latin transliteration where native script is used")
    payee_target: str = Field("ramesh@upi", description="Intended payee")
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    speaker_metadata: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None
