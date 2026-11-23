"""Experimental evaluation engine running baseline vs guarded benchmark arms."""

import os
import uuid
import time
from typing import List, Dict, Any, Optional, Tuple

from sahi.dataset.models import BaseUtterance
from sahi.dataset.pilot import PILOT_DATASET
from sahi.audio.models import AudioClipRecord, AudioCondition
from sahi.agent.models import TranscriptResponse, TransferProposal
from sahi.agent.saaras import SaarasSTTAdapter
from sahi.agent.sarvam_llm import SarvamLLMAdapter
from sahi.amounts.engine import AmountEngine
from sahi.guard.engine import SahiGuard
from sahi.guard.models import GuardAction, ReadingSource
from sahi.bank.database import MockBankDatabase
from sahi.bank.models import TransferRequest
from sahi.metrics.models import TrialResult, PairedComparisonResult
from sahi.metrics.calculator import MetricsCalculator

class EvaluationHarness:
    """
    Executes controlled benchmark experiments comparing:
    Arm 1 (Baseline): Saaras (transcribe) -> Sarvam 105B -> Mock Bank A
    Arm 2 (Guarded):  Saaras (transcribe + codemix) -> AmountEngine + Sarvam 105B -> SahiGuard -> Mock Bank B
    """

    def __init__(
        self,
        saaras_adapter: Optional[SaarasSTTAdapter] = None,
        llm_adapter: Optional[SarvamLLMAdapter] = None,
        amount_engine: Optional[AmountEngine] = None,
        guard: Optional[SahiGuard] = None,
        baseline_db: Optional[MockBankDatabase] = None,
        guarded_db: Optional[MockBankDatabase] = None,
    ):
        self.saaras = saaras_adapter or SaarasSTTAdapter()
        self.llm = llm_adapter or SarvamLLMAdapter()
        self.amount_engine = amount_engine or AmountEngine()
        self.guard = guard or SahiGuard()

        # Enforce isolated mock bank ledgers
        self.baseline_db = baseline_db or MockBankDatabase(":memory:")
        self.guarded_db = guarded_db or MockBankDatabase(":memory:")

    def run_clip_trial(
        self,
        clip_record: AudioClipRecord,
        utterance: BaseUtterance,
        audio_bytes: Optional[bytes] = None
    ) -> Tuple[TrialResult, TrialResult]:
        """
        Runs both Baseline and Guarded arms on a single audio clip.
        Ground truth (utterance.intended_amount_inr) is strictly isolated to scoring.
        """
        trial_id = f"TRIAL_{clip_record.clip_id}_{uuid.uuid4().hex[:6]}"
        intended_amount = utterance.intended_amount_inr

        # If audio bytes are not provided and file doesn't exist
        if audio_bytes is None:
            # Check relative filepath
            if not os.path.isfile(clip_record.relative_filepath):
                # Missing audio file handling
                missing_trial_b = TrialResult(
                    trial_id=f"{trial_id}_B",
                    utterance_id=utterance.id,
                    language_group=utterance.language_group,
                    category=utterance.category.value,
                    condition=clip_record.condition,
                    intended_amount_inr=intended_amount,
                    executed_amount_inr=None,
                    execution_status="MISSING_AUDIO",
                    audit_log={"note": "WAV file not present on disk"}
                )
                missing_trial_g = TrialResult(
                    trial_id=f"{trial_id}_G",
                    utterance_id=utterance.id,
                    language_group=utterance.language_group,
                    category=utterance.category.value,
                    condition=clip_record.condition,
                    intended_amount_inr=intended_amount,
                    executed_amount_inr=None,
                    execution_status="MISSING_AUDIO",
                    audit_log={"note": "WAV file not present on disk"}
                )
                return missing_trial_b, missing_trial_g

        # 1. STT Transcription (Transcribe mode used by both arms)
        t_start = time.perf_counter()
        stt_literal = self.saaras.transcribe(audio_bytes, mode="transcribe")

        # 2. LLM Tool Proposal (Shared identical proposal)
        chat_resp = self.llm.extract_transfer_proposal(stt_literal.transcript)
        llm_proposal = chat_resp.proposal

        latency_common = (time.perf_counter() - t_start) * 1000

        # =========================================================
        # ARM 1: UNGUARDED BASELINE EXECUTION
        # =========================================================
        baseline_executed: Optional[int] = None
        baseline_status = "NO_TRANSFER"

        if llm_proposal and llm_proposal.amount_inr > 0:
            req_b = TransferRequest(
                from_account="ACC_USER_001",
                to_payee=llm_proposal.payee,
                amount_inr=llm_proposal.amount_inr,
                idempotency_key=f"IDEMP_B_{trial_id}"
            )
            resp_b = self.baseline_db.execute_transfer(req_b)
            if resp_b.success:
                baseline_executed = resp_b.amount_inr
                baseline_status = "EXECUTED"
            else:
                baseline_status = resp_b.status
        else:
            baseline_status = "PARSE_FAILURE"

        # Score Baseline Trial (Ground truth used only here)
        b_correct = (baseline_executed == intended_amount) if intended_amount is not None else (baseline_executed is None)
        b_unsafe = (baseline_executed is not None) and (baseline_executed != intended_amount)
        b_silent_wrong = b_unsafe  # Baseline has no guard, so all unsafe transfers are silent
        b_rupees_diff = abs(baseline_executed - intended_amount) if (b_unsafe and intended_amount is not None) else 0

        trial_baseline = TrialResult(
            trial_id=f"{trial_id}_B",
            utterance_id=utterance.id,
            language_group=utterance.language_group,
            category=utterance.category.value,
            condition=clip_record.condition,
            intended_amount_inr=intended_amount,
            executed_amount_inr=baseline_executed,
            execution_status=baseline_status,
            is_completed_transfer=(baseline_executed is not None),
            is_correct=b_correct,
            is_unsafe=b_unsafe,
            is_silent_wrong=b_silent_wrong,
            is_false_hold=False,  # Baseline never holds
            rupees_discrepancy=b_rupees_diff,
            latency_ms=round(latency_common, 2),
            audit_log={
                "transcript": stt_literal.transcript,
                "llm_proposed": llm_proposal.amount_inr if llm_proposal else None
            }
        )

        # =========================================================
        # ARM 2: GUARDED EXECUTION (SahiGuard)
        # =========================================================
        t_guard_start = time.perf_counter()

        # Dual mode transcription
        stt_codemix = self.saaras.transcribe(audio_bytes, mode="codemix")
        parsed_literal = self.amount_engine.parse(stt_literal.transcript)
        parsed_codemix = self.amount_engine.parse(stt_codemix.transcript)

        readings = [
            ReadingSource(
                source_name="saaras_literal",
                amount_inr=parsed_literal.amount_inr,
                raw_text=stt_literal.transcript,
                confidence=parsed_literal.confidence
            ),
            ReadingSource(
                source_name="saaras_codemix",
                amount_inr=parsed_codemix.amount_inr,
                raw_text=stt_codemix.transcript,
                confidence=parsed_codemix.confidence
            )
        ]
        if llm_proposal:
            readings.append(
                ReadingSource(
                    source_name="sarvam_105b_proposal",
                    amount_inr=llm_proposal.amount_inr,
                    raw_text=str(llm_proposal.raw_arguments),
                    confidence=1.0
                )
            )

        guard_decision = self.guard.evaluate(readings)

        guarded_executed: Optional[int] = None
        guarded_status = "UNKNOWN"

        if guard_decision.action == GuardAction.EXECUTE:
            payee = llm_proposal.payee if llm_proposal else "ramesh@upi"
            req_g = TransferRequest(
                from_account="ACC_USER_001",
                to_payee=payee,
                amount_inr=guard_decision.final_amount_inr,
                idempotency_key=f"IDEMP_G_{trial_id}",
                guard_decision=guard_decision.model_dump()
            )
            resp_g = self.guarded_db.execute_transfer(req_g)
            if resp_g.success:
                guarded_executed = resp_g.amount_inr
                guarded_status = "EXECUTED"
            else:
                guarded_status = resp_g.status
        elif guard_decision.action == GuardAction.READ_BACK:
            guarded_status = "HELD_FOR_READBACK"
        elif guard_decision.action == GuardAction.RE_ASK:
            guarded_status = "HELD_FOR_CLARIFICATION"
        elif guard_decision.action == GuardAction.ESCALATE:
            guarded_status = "ESCALATED"

        latency_guarded = latency_common + (time.perf_counter() - t_guard_start) * 1000

        # Score Guarded Trial
        g_correct = (guarded_executed == intended_amount) if (intended_amount is not None and guarded_executed is not None) else (guarded_executed is None and intended_amount is None)
        g_unsafe = (guarded_executed is not None) and (guarded_executed != intended_amount)
        g_silent_wrong = g_unsafe and (guard_decision.action == GuardAction.EXECUTE)
        g_rupees_diff = abs(guarded_executed - intended_amount) if (g_unsafe and intended_amount is not None) else 0

        # False hold: There was an unambiguous correct intended amount (> 0),
        # but guard refused to execute (held for readback, clarification, or escalated).
        g_false_hold = (
            intended_amount is not None and
            utterance.category.value != "self_correction" and
            guarded_executed is None and
            (llm_proposal is not None and llm_proposal.amount_inr == intended_amount)
        )

        trial_guarded = TrialResult(
            trial_id=f"{trial_id}_G",
            utterance_id=utterance.id,
            language_group=utterance.language_group,
            category=utterance.category.value,
            condition=clip_record.condition,
            intended_amount_inr=intended_amount,
            executed_amount_inr=guarded_executed,
            execution_status=guarded_status,
            guard_action=guard_decision.action,
            guard_reason=guard_decision.reason_code,
            is_completed_transfer=(guarded_executed is not None),
            is_correct=g_correct,
            is_unsafe=g_unsafe,
            is_silent_wrong=g_silent_wrong,
            is_false_hold=g_false_hold,
            rupees_discrepancy=g_rupees_diff,
            latency_ms=round(latency_guarded, 2),
            audit_log={
                "literal_transcript": stt_literal.transcript,
                "codemix_transcript": stt_codemix.transcript,
                "guard_decision": guard_decision.model_dump()
            }
        )

        return trial_baseline, trial_guarded

    def evaluate_benchmark(
        self,
        clip_records: List[AudioClipRecord],
        utterances_map: Dict[str, BaseUtterance],
        audio_fixtures_map: Optional[Dict[str, bytes]] = None,
        bootstrap_iterations: int = 1000
    ) -> PairedComparisonResult:
        """
        Runs evaluation over all supplied clip records and computes paired comparison.
        """
        baseline_trials: List[TrialResult] = []
        guarded_trials: List[TrialResult] = []

        fixtures = audio_fixtures_map or {}

        for clip in clip_records:
            utt = utterances_map.get(clip.utterance_id)
            if not utt:
                continue

            audio_data = fixtures.get(clip.clip_id)
            tb, tg = self.run_clip_trial(clip, utt, audio_bytes=audio_data)
            baseline_trials.append(tb)
            guarded_trials.append(tg)

        return MetricsCalculator.compare_arms(
            baseline_trials=baseline_trials,
            guarded_trials=guarded_trials,
            bootstrap_iterations=bootstrap_iterations
        )
