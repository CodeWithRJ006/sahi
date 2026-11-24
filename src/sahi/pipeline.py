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

    def process_audio_pipeline(
        self,
        audio_bytes: bytes,
        saaras_adapter: Any,
        llm_adapter: Any,
        from_account: str = "ACC_USER_001",
        to_payee_fallback: str = "recipient@upi",
        idempotency_key: Optional[str] = None
    ) -> PipelineResult:
        """
        Executes full audio pipeline:
        Audio -> Saaras v4 (transcribe + codemix) -> Sarvam 105B proposal -> SahiGuard -> Mock Bank.

        CRITICAL SAFETY RULE:
        The LLM only proposes transfer parameters. SahiGuard evaluates consensus across
        transcript readings and LLM proposal before any simulated execution.
        """
        from sahi.guard.models import ReadingSource

        if not idempotency_key:
            idempotency_key = f"IDEMP_AUDIO_{uuid.uuid4().hex[:10].upper()}"

        # 1. Dual-mode STT transcriptions
        stt_literal = saaras_adapter.transcribe(audio_bytes, mode="transcribe")
        stt_codemix = saaras_adapter.transcribe(audio_bytes, mode="codemix")

        # 2. Local Indic amount parsing
        parsed_literal = self.amount_engine.parse(stt_literal.transcript)
        parsed_codemix = self.amount_engine.parse(stt_codemix.transcript)

        # 3. LLM structured tool proposal
        chat_resp = llm_adapter.extract_transfer_proposal(stt_literal.transcript)
        llm_proposal = chat_resp.proposal

        payee = llm_proposal.payee if (llm_proposal and llm_proposal.payee) else to_payee_fallback

        # 4. Construct SahiGuard candidate readings
        readings = [
            ReadingSource(
                source_name="saaras_literal",
                amount_inr=parsed_literal.amount_inr,
                raw_text=stt_literal.transcript,
                confidence=parsed_literal.confidence,
                is_proposal=False,
                status=parsed_literal.status.name,
                candidates=parsed_literal.candidates
            ),
            ReadingSource(
                source_name="saaras_codemix",
                amount_inr=parsed_codemix.amount_inr,
                raw_text=stt_codemix.transcript,
                confidence=parsed_codemix.confidence,
                is_proposal=False,
                status=parsed_codemix.status.name,
                candidates=parsed_codemix.candidates
            )
        ]
        if llm_proposal and llm_proposal.amount_inr is not None:
            readings.append(
                ReadingSource(
                    source_name="sarvam_105b_proposal",
                    amount_inr=llm_proposal.amount_inr,
                    raw_text=str(llm_proposal.raw_arguments),
                    confidence=1.0,
                    is_proposal=True
                )
            )

        # 5. Deterministic SahiGuard evaluation
        guard_decision = self.guard.evaluate(readings)

        # 6. Safe simulated execution
        transfer_resp: Optional[TransferResponse] = None
        if guard_decision.action == GuardAction.EXECUTE:
            req = TransferRequest(
                from_account=from_account,
                to_payee=payee,
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
            parsed_amount=parsed_literal,
            guard_decision=guard_decision,
            transfer_response=transfer_resp,
            audit_metadata={
                "literal_transcript": stt_literal.transcript,
                "codemix_transcript": stt_codemix.transcript,
                "llm_proposed_amount": llm_proposal.amount_inr if llm_proposal else None,
                "llm_payee": payee,
                "idempotency_key": idempotency_key
            }
        )
