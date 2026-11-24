"""Domain models for SahiGuard deterministic amount safety verification."""

from enum import Enum
from typing import Optional, List, Dict, Any, ClassVar
from pydantic import BaseModel, Field

class GuardAction(str, Enum):
    EXECUTE = "EXECUTE"
    READ_BACK = "READ_BACK"
    RE_ASK = "RE_ASK"
    ESCALATE = "ESCALATE"

class ReasonCode(str, Enum):
    AGREEMENT_VERIFIED = "AGREEMENT_VERIFIED"
    POWER_OF_TEN_MISMATCH = "POWER_OF_TEN_MISMATCH"
    PHONETIC_CONFUSABLE_MISMATCH = "PHONETIC_CONFUSABLE_MISMATCH"
    HIGH_VALUE_THRESHOLD = "HIGH_VALUE_THRESHOLD"
    PARSE_AMBIGUOUS_SELF_CORRECTION = "PARSE_AMBIGUOUS_SELF_CORRECTION"
    PARSE_AMBIGUOUS_MULTIPLE_AMOUNTS = "PARSE_AMBIGUOUS_MULTIPLE_AMOUNTS"
    PARSE_AMBIGUOUS_CONFLICT = "PARSE_AMBIGUOUS_CONFLICT"
    PARSE_UNRECOGNIZED = "PARSE_UNRECOGNIZED"
    READING_DISCREPANCY = "READING_DISCREPANCY"
    ZERO_OR_NEGATIVE_AMOUNT = "ZERO_OR_NEGATIVE_AMOUNT"
    EXCEEDS_MAX_LIMIT = "EXCEEDS_MAX_LIMIT"
    MISSING_READINGS = "MISSING_READINGS"
    CONFIRMATION_MISMATCH = "CONFIRMATION_MISMATCH"
    RECIPIENT_MISSING_OR_INVALID = "RECIPIENT_MISSING_OR_INVALID"

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ReadingSource(BaseModel):
    source_name: str = Field(..., description="e.g. 'transcript_literal', 'transcript_codemix', 'llm_tool_call'")
    amount_inr: Optional[int] = Field(None, description="Extracted integer INR amount, if any")
    raw_text: Optional[str] = None
    confidence: float = 1.0
    is_proposal: bool = Field(False, description="True if reading is an unverified LLM/agent proposal")
    status: Optional[str] = Field(None, description="Parse status if from amount engine (e.g. PARSED, AMBIGUOUS, UNRECOGNIZED)")
    candidates: List[int] = Field(default_factory=list, description="Candidate amounts if ambiguous")

from typing import ClassVar

class GuardDecision(BaseModel):
    action: GuardAction
    final_amount_inr: Optional[int] = Field(None, description="Validated amount safe to execute, if approved")
    reason_code: ReasonCode
    risk_level: RiskLevel
    explanation: str
    readings: List[ReadingSource] = Field(default_factory=list)
    discrepancy_factor: Optional[float] = Field(None, description="Ratio if power-of-ten or scale mismatch (e.g. 10.0, 100.0)")
    requires_readback: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Enum-like shortcuts for backward compatibility / test expectations
    EXECUTE: ClassVar[GuardAction] = GuardAction.EXECUTE
    READ_BACK: ClassVar[GuardAction] = GuardAction.READ_BACK
    RE_ASK: ClassVar[GuardAction] = GuardAction.RE_ASK
    ESCALATE: ClassVar[GuardAction] = GuardAction.ESCALATE
