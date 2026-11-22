"""End-to-end execution pipeline for SAHI vertical slice."""

import uuid
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from sahi.amounts.engine import AmountEngine
from sahi.amounts.models import ParsedAmount, LanguageGroup
from sahi.guard.engine import SahiGuard
from sahi.guard.models import GuardDecision, GuardAction
from sahi.bank.database import MockBankDatabase
from sahi.bank.models import TransferRequest, TransferResponse

class PipelineResult(BaseModel):
    status: str = Field(..., description="EXECUTED, HELD_FOR_READBACK, HELD_FOR_CLARIFICATION, ESCALATED, UNRECOGNIZED")
    parsed_amount: ParsedAmount
    guard_decision: GuardDecision
    transfer_response: Optional[TransferResponse] = None
    audit_metadata: Dict[str, Any] = Field(default_factory=dict)

class SahiPipeline:
    """
    Connects multilingual speech text parsing, SahiGuard safety verification,
    and mock bank ledger execution.
    """

    def __init__(
        self,
        amount_engine: Optional[AmountEngine] = None,
        guard: Optional[SahiGuard] = None,
        bank_db: Optional[MockBankDatabase] = None,
    ):
        self.amount_engine = amount_engine or AmountEngine()
        self.guard = guard or SahiGuard()
        self.bank_db = bank_db or MockBankDatabase()

    def process_utterance(
        self,
        utterance: str,
        from_account: str = "ACC_USER_001",
        to_payee: str = "ramesh@upi",
        idempotency_key: Optional[str] = None,
        agent_proposed_amount: Optional[int] = None,
        preferred_language: LanguageGroup = LanguageGroup.AUTO
    ) -> PipelineResult:
        if not idempotency_key:
            idempotency_key = f"IDEMP_{uuid.uuid4().hex[:12].upper()}"

        # 1. Indic amount parsing
        parsed = self.amount_engine.parse(utterance, preferred_language=preferred_language)

        # 2. SahiGuard safety evaluation
        guard_decision = self.guard.evaluate_parsed_amount(
            parsed=parsed,
            proposed_by_agent=agent_proposed_amount
        )

        # 3. Execution routing based on deterministic guard decision
        transfer_resp: Optional[TransferResponse] = None

        if guard_decision.action == GuardAction.EXECUTE:
            # Safe to execute against mock ledger
            req = TransferRequest(
                from_account=from_account,
                to_payee=to_payee,
                amount_inr=guard_decision.final_amount_inr,
                idempotency_key=idempotency_key,
                guard_decision=guard_decision.model_dump()
            )
            transfer_resp = self.bank_db.execute_transfer(req)
            pipeline_status = "EXECUTED" if transfer_resp.success else transfer_resp.status

        elif guard_decision.action == GuardAction.READ_BACK:
            pipeline_status = "HELD_FOR_READBACK"

        elif guard_decision.action == GuardAction.RE_ASK:
            pipeline_status = "HELD_FOR_CLARIFICATION"

        elif guard_decision.action == GuardAction.ESCALATE:
            pipeline_status = "ESCALATED"

        else:
            pipeline_status = "UNKNOWN_GUARD_ACTION"

        return PipelineResult(
            status=pipeline_status,
            parsed_amount=parsed,
            guard_decision=guard_decision,
            transfer_response=transfer_resp,
            audit_metadata={
                "utterance": utterance,
                "from_account": from_account,
                "to_payee": to_payee,
                "idempotency_key": idempotency_key
            }
        )
