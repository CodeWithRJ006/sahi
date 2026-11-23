"""Data models for SAHI benchmark evaluation and metrics."""

from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from sahi.audio.models import AudioCondition
from sahi.guard.models import GuardAction, ReasonCode

class TrialResult(BaseModel):
    """Result of a single evaluation trial on an audio clip."""
    trial_id: str
    utterance_id: str
    language_group: str
    category: str
    condition: AudioCondition
    intended_amount_inr: Optional[int] = None
    executed_amount_inr: Optional[int] = None
    execution_status: str  # EXECUTED, HELD_FOR_READBACK, HELD_FOR_CLARIFICATION, ESCALATED, PARSE_FAILURE, MISSING_AUDIO
    guard_action: Optional[GuardAction] = None
    guard_reason: Optional[ReasonCode] = None
    is_completed_transfer: bool = False
    is_correct: bool = False
    is_unsafe: bool = False
    is_silent_wrong: bool = False
    is_false_hold: bool = False
    rupees_discrepancy: int = 0
    latency_ms: float = 0.0
    cost_inr: float = 0.0
    audit_log: Dict[str, Any] = Field(default_factory=dict)

class ArmEvaluationSummary(BaseModel):
    """Aggregate evaluation metrics for an experimental arm (Baseline or Guarded)."""
    arm_name: str
    total_trials: int
    total_completed_transfers: int
    wrong_amount_execution_rate: float = Field(..., description="Wrong transfers / completed transfers")
    unsafe_execution_rate: float = Field(..., description="Wrong transfers / all trials")
    silent_wrong_rate: float = Field(..., description="Wrong transfers without flag or readback / all trials")
    false_hold_rate: float = Field(..., description="Correct amounts held or re-asked / trials with correct candidate")
    rupees_at_risk_per_1000: float = Field(..., description="Sum of absolute rupees discrepancy per 1000 trials")
    no_transfer_rate: float
    parse_failure_rate: float
    ambiguity_rate: float
    read_back_rate: float
    escalation_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    total_cost_inr: float

class PairedComparisonResult(BaseModel):
    """Paired comparative analysis between Baseline and Guarded arms."""
    baseline: ArmEvaluationSummary
    guarded: ArmEvaluationSummary
    baseline_only_errors: int
    guard_only_errors: int
    shared_errors: int
    unsafe_rate_delta: float = Field(..., description="Baseline unsafe rate minus Guarded unsafe rate")
    unsafe_rate_delta_ci_95: Tuple[float, float]
    rupees_at_risk_delta: float
    rupees_at_risk_delta_ci_95: Tuple[float, float]
    experiment_metadata: Dict[str, Any] = Field(default_factory=dict)
