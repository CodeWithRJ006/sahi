"""SahiGuard: Deterministic Amount Safety Engine."""

from typing import List, Optional
from sahi.guard.models import (
    GuardDecision, GuardAction, ReasonCode, RiskLevel, ReadingSource
)
from sahi.guard.rules import (
    is_power_of_ten_discrepancy, is_phonetic_confusable, check_high_value_limit
)
from sahi.amounts.models import ParsedAmount, ParseStatus, AmbiguityReason

class SahiGuard:
    """
    Deterministic safety engine evaluating multi-source amount interpretations.
    
    CRITICAL ARCHITECTURAL NOTE:
    Transcripts derived from different modes (literal, codemix) or downstream LLM extractions
    share common upstream acoustic and transcription failure risks. They must NEVER be treated
    as statistically independent. Disagreements represent elevated operational risk.
    """

    def __init__(self, max_auto_execute_limit: int = 50_000):
        self.max_auto_execute_limit = max_auto_execute_limit

    def evaluate(self, readings: List[ReadingSource]) -> GuardDecision:
        """
        Evaluates a set of candidate amount readings from multiple extraction sources.
        """
        if not readings:
            return GuardDecision(
                action=GuardAction.RE_ASK,
                reason_code=ReasonCode.MISSING_READINGS,
                risk_level=RiskLevel.HIGH,
                explanation="No amount readings available to evaluate.",
                readings=[]
            )

        valid_readings = [r for r in readings if r.amount_inr is not None]
        if not valid_readings:
            return GuardDecision(
                action=GuardAction.RE_ASK,
                reason_code=ReasonCode.PARSE_UNRECOGNIZED,
                risk_level=RiskLevel.HIGH,
                explanation="None of the readings produced a valid numerical amount.",
                readings=readings
            )

        # Check for invalid non-positive amounts
        for r in valid_readings:
            if r.amount_inr <= 0:
                return GuardDecision(
                    action=GuardAction.ESCALATE,
                    final_amount_inr=r.amount_inr,
                    reason_code=ReasonCode.ZERO_OR_NEGATIVE_AMOUNT,
                    risk_level=RiskLevel.CRITICAL,
                    explanation=f"Invalid non-positive amount ({r.amount_inr}) detected from source {r.source_name}.",
                    readings=readings
                )

        # Check if any reading explicitly reports an ambiguous parse status
        ambiguous_readings = [r for r in readings if r.status == "AMBIGUOUS" or len(r.candidates) > 0]
        if ambiguous_readings:
            all_candidates = []
            for ar in ambiguous_readings:
                all_candidates.extend(ar.candidates)
            unique_cands = sorted(list(set(all_candidates)))
            return GuardDecision(
                action=GuardAction.RE_ASK,
                reason_code=ReasonCode.PARSE_AMBIGUOUS_SELF_CORRECTION if len(unique_cands) > 1 else ReasonCode.PARSE_AMBIGUOUS_CONFLICT,
                risk_level=RiskLevel.HIGH,
                explanation=f"Ambiguous amount reading detected with candidate figures: {unique_cands}.",
                readings=readings,
                metadata={"candidates": unique_cands}
            )

        # Check that there is at least one deterministic reading (not just an LLM / agent proposal)
        def _is_proposal(r: ReadingSource) -> bool:
            if getattr(r, "is_proposal", False):
                return True
            sname = r.source_name.lower()
            return any(k in sname for k in ["proposal", "llm", "agent", "tool_call"])

        has_deterministic_reading = any(not _is_proposal(r) for r in valid_readings)
        if not has_deterministic_reading:
            return GuardDecision(
                action=GuardAction.RE_ASK,
                reason_code=ReasonCode.PARSE_UNRECOGNIZED,
                risk_level=RiskLevel.HIGH,
                explanation="An LLM-generated amount is a proposal, not the authority to move money. No validated deterministic reading was available.",
                readings=readings
            )

        amounts = [r.amount_inr for r in valid_readings]
        unique_amounts = sorted(list(set(amounts)))

        # Check absolute maximum transaction limit (₹100,000,000)
        for a in unique_amounts:
            if a > 100_000_000:
                return GuardDecision(
                    action=GuardAction.ESCALATE,
                    reason_code=ReasonCode.EXCEEDS_MAX_LIMIT,
                    risk_level=RiskLevel.CRITICAL,
                    explanation=f"Amount (Rs. {a:,}) exceeds maximum allowable transaction limit (Rs. 100,000,000).",
                    readings=readings
                )

        # Case 1: All available readings agree on a single amount
        if len(unique_amounts) == 1:
            amount = unique_amounts[0]
            if check_high_value_limit(amount, self.max_auto_execute_limit):
                return GuardDecision(
                    action=GuardAction.READ_BACK,
                    final_amount_inr=amount,
                    reason_code=ReasonCode.HIGH_VALUE_THRESHOLD,
                    risk_level=RiskLevel.MEDIUM,
                    explanation=f"Amount (Rs. {amount:,}) exceeds straight-through limit (Rs. {self.max_auto_execute_limit:,}); explicit user read-back required.",
                    readings=readings,
                    requires_readback=True
                )
            return GuardDecision(
                action=GuardAction.EXECUTE,
                final_amount_inr=amount,
                reason_code=ReasonCode.AGREEMENT_VERIFIED,
                risk_level=RiskLevel.LOW,
                explanation=f"All {len(valid_readings)} reading(s) agree on Rs. {amount:,}.",
                readings=readings
            )

        # Case 2: Disagreement detected between readings
        amt_min, amt_max = unique_amounts[0], unique_amounts[-1]

        # Check for catastrophic power-of-ten mismatch (e.g. 5,000 vs 50,000)
        is_p10, ratio = is_power_of_ten_discrepancy(amt_min, amt_max)
        if is_p10:
            return GuardDecision(
                action=GuardAction.ESCALATE,
                reason_code=ReasonCode.POWER_OF_TEN_MISMATCH,
                risk_level=RiskLevel.CRITICAL,
                discrepancy_factor=ratio,
                explanation=f"Critical {ratio:g}x power-of-ten scale mismatch detected between readings ({amt_min:,} vs {amt_max:,}). Execution halted.",
                readings=readings
            )

        # Check for phonetic confusable mismatch (e.g. 15,000 vs 50,000)
        if is_phonetic_confusable(amt_min, amt_max):
            return GuardDecision(
                action=GuardAction.RE_ASK,
                reason_code=ReasonCode.PHONETIC_CONFUSABLE_MISMATCH,
                risk_level=RiskLevel.HIGH,
                explanation=f"Phonetic confusable pair detected between readings ({amt_min:,} vs {amt_max:,}). Clarification required.",
                readings=readings
            )

        # General discrepancy
        return GuardDecision(
            action=GuardAction.RE_ASK,
            reason_code=ReasonCode.READING_DISCREPANCY,
            risk_level=RiskLevel.HIGH,
            explanation=f"Disagreement between candidate readings ({', '.join(str(a) for a in unique_amounts)}). Prompting user to re-confirm.",
            readings=readings
        )

    def evaluate_parsed_amount(
        self,
        parsed: ParsedAmount,
        proposed_by_agent: Optional[int] = None
    ) -> GuardDecision:
        """
        Convenience evaluator mapping a single ParsedAmount output and optional LLM agent proposed amount.
        """
        if parsed.status == ParseStatus.UNRECOGNIZED:
            return GuardDecision(
                action=GuardAction.RE_ASK,
                reason_code=ReasonCode.PARSE_UNRECOGNIZED,
                risk_level=RiskLevel.HIGH,
                explanation="Utterance did not contain an interpretable monetary figure.",
                readings=[ReadingSource(source_name="parsed_amount", raw_text=parsed.raw_text)]
            )

        if parsed.status == ParseStatus.AMBIGUOUS:
            if parsed.ambiguity_reason == AmbiguityReason.SELF_CORRECTION:
                return GuardDecision(
                    action=GuardAction.RE_ASK,
                    reason_code=ReasonCode.PARSE_AMBIGUOUS_SELF_CORRECTION,
                    risk_level=RiskLevel.HIGH,
                    explanation=f"Spoken self-correction detected with candidate amounts: {parsed.candidates}.",
                    readings=[ReadingSource(source_name="candidates", amount_inr=c) for c in parsed.candidates],
                    metadata={"candidates": parsed.candidates}
                )
            if parsed.ambiguity_reason == AmbiguityReason.MULTIPLE_AMOUNTS:
                return GuardDecision(
                    action=GuardAction.RE_ASK,
                    reason_code=ReasonCode.PARSE_AMBIGUOUS_MULTIPLE_AMOUNTS,
                    risk_level=RiskLevel.HIGH,
                    explanation=f"Multiple amounts detected in single utterance: {parsed.candidates}.",
                    readings=[ReadingSource(source_name="candidates", amount_inr=c) for c in parsed.candidates],
                    metadata={"candidates": parsed.candidates}
                )
            return GuardDecision(
                action=GuardAction.ESCALATE,
                reason_code=ReasonCode.PARSE_AMBIGUOUS_CONFLICT,
                risk_level=RiskLevel.CRITICAL,
                explanation=f"Ambiguous amount expression: {parsed.ambiguity_reason}.",
                readings=[ReadingSource(source_name="parsed_amount", raw_text=parsed.raw_text)]
            )

        # Parsed status is PARSED
        readings = [
            ReadingSource(
                source_name="amount_engine",
                amount_inr=parsed.amount_inr,
                confidence=parsed.confidence
            )
        ]
        if proposed_by_agent is not None:
            readings.append(
                ReadingSource(
                    source_name="agent_proposal",
                    amount_inr=proposed_by_agent,
                    confidence=1.0
                )
            )

        return self.evaluate(readings)

    def evaluate_confirmation(
        self,
        proposed_amount: int,
        proposed_payee: str,
        confirmed_amount: Optional[int],
        confirmed_payee: Optional[str],
        is_confirmed: bool = True
    ) -> GuardDecision:
        """
        Validates confirmation integrity: confirmation must be bound to specific transaction details.
        Missing, stale, invalid or mismatched confirmation cannot authorize execution.
        Changes in amount or recipient invalidate previous confirmation.
        """
        if not proposed_payee or not proposed_payee.strip():
            return GuardDecision(
                action=GuardAction.RE_ASK,
                reason_code=ReasonCode.RECIPIENT_MISSING_OR_INVALID,
                risk_level=RiskLevel.HIGH,
                explanation="Recipient information is missing or invalid.",
                readings=[]
            )

        if not is_confirmed:
            return GuardDecision(
                action=GuardAction.RE_ASK,
                reason_code=ReasonCode.CONFIRMATION_MISMATCH,
                risk_level=RiskLevel.HIGH,
                explanation="User confirmation was not granted.",
                readings=[]
            )

        if confirmed_amount is None or confirmed_amount <= 0:
            return GuardDecision(
                action=GuardAction.RE_ASK,
                reason_code=ReasonCode.CONFIRMATION_MISMATCH,
                risk_level=RiskLevel.HIGH,
                explanation="Confirmed amount is missing or non-positive.",
                readings=[]
            )

        if not confirmed_payee or not confirmed_payee.strip():
            return GuardDecision(
                action=GuardAction.RE_ASK,
                reason_code=ReasonCode.CONFIRMATION_MISMATCH,
                risk_level=RiskLevel.HIGH,
                explanation="Confirmed recipient payee is missing or invalid.",
                readings=[]
            )

        if confirmed_amount != proposed_amount:
            is_p10, factor = is_power_of_ten_discrepancy(proposed_amount, confirmed_amount)
            return GuardDecision(
                action=GuardAction.ESCALATE if is_p10 else GuardAction.RE_ASK,
                reason_code=ReasonCode.CONFIRMATION_MISMATCH,
                risk_level=RiskLevel.CRITICAL if is_p10 else RiskLevel.HIGH,
                discrepancy_factor=factor if is_p10 else None,
                explanation=f"Confirmed amount (Rs. {confirmed_amount:,}) does not match proposed amount (Rs. {proposed_amount:,}). Authorization invalidated.",
                readings=[
                    ReadingSource(source_name="proposed_amount", amount_inr=proposed_amount),
                    ReadingSource(source_name="confirmed_amount", amount_inr=confirmed_amount),
                ]
            )

        if confirmed_payee.strip().lower() != proposed_payee.strip().lower():
            return GuardDecision(
                action=GuardAction.ESCALATE,
                reason_code=ReasonCode.CONFIRMATION_MISMATCH,
                risk_level=RiskLevel.CRITICAL,
                explanation=f"Confirmed recipient '{confirmed_payee}' does not match proposed recipient '{proposed_payee}'. Authorization invalidated.",
                readings=[]
            )

        readings = [ReadingSource(source_name="confirmed_amount", amount_inr=proposed_amount)]
        return self.evaluate(readings)
