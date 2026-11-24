"""FastAPI Mock Bank service for safe simulated transfer execution and SAHI Live Voice Demo."""

import os
import uuid
import base64
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse

from sahi.bank.models import TransferRequest, TransferResponse, AccountBalance, TransactionRecord
from sahi.bank.database import MockBankDatabase
from sahi.bank.ui import LIVE_UI_HTML
from sahi.amounts.engine import AmountEngine
from sahi.guard.engine import SahiGuard
from sahi.guard.models import GuardAction
from sahi.agent.saaras import SaarasSTTAdapter
from sahi.audio.providers.sarvam_bulbul import SarvamBulbulProvider
from sahi.audio.models import TTSRequest

class VoiceProcessRequest(BaseModel):
    text: Optional[str] = Field(None, description="Spoken or typed instruction text")
    audio_base64: Optional[str] = Field(None, description="Base64 encoded audio from browser microphone")
    from_account: str = Field("ACC_USER_001", description="Source account ID")
    to_payee: str = Field("ramesh@upi", description="Target recipient UPI ID")
    agent_proposed_amount: Optional[int] = Field(None, description="Simulated LLM proposal (for mismatch tests)")

class VoiceConfirmRequest(BaseModel):
    from_account: str = Field("ACC_USER_001", description="Source account ID")
    to_payee: str = Field("ramesh@upi", description="Target recipient UPI ID")
    proposed_amount: int = Field(..., description="Amount proposed in transaction")
    confirmed_amount: int = Field(..., description="Amount confirmed by user")
    confirmed_payee: str = Field(..., description="Recipient confirmed by user")
    is_confirmed: bool = Field(True, description="Explicit user confirmation flag")

def create_bank_app(
    db: Optional[MockBankDatabase] = None,
    amount_engine: Optional[AmountEngine] = None,
    guard: Optional[SahiGuard] = None,
    stt_adapter: Optional[SaarasSTTAdapter] = None,
    tts_provider: Optional[SarvamBulbulProvider] = None,
) -> FastAPI:
    if db is None:
        db_path = os.getenv("MOCK_BANK_DB_PATH", "data/mock_bank.sqlite3")
        os.makedirs(os.path.dirname(db_path), exist_ok=True) if os.path.dirname(db_path) else None
        db = MockBankDatabase(db_path)

    amount_engine = amount_engine or AmountEngine()
    guard = guard or SahiGuard()
    stt_adapter = stt_adapter or SaarasSTTAdapter()
    tts_provider = tts_provider or SarvamBulbulProvider()

    app = FastAPI(
        title="SAHI Mock Bank & Voice Safety Demo",
        description="Safe, isolated mock banking API and SAHI Live interactive voice safety interface.",
        version="0.2.0"
    )

    # -------------------------------------------------------------------------
    # Web UI
    # -------------------------------------------------------------------------
    @app.get("/", response_class=HTMLResponse, tags=["Web UI"])
    @app.get("/live", response_class=HTMLResponse, tags=["Web UI"])
    def get_live_ui():
        """Serves the SAHI Live interactive voice and safety guard browser demonstration."""
        return LIVE_UI_HTML

    # -------------------------------------------------------------------------
    # System & Banking Endpoints
    # -------------------------------------------------------------------------
    @app.get("/health", tags=["System"])
    def health_check():
        return {"status": "ok", "service": "sahi-mock-bank", "safety_mode": "SIMULATION_ONLY"}

    @app.get("/accounts/{account_id}", response_model=AccountBalance, tags=["Accounts"])
    def get_account_balance(account_id: str):
        acc = db.get_account(account_id)
        if not acc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account '{account_id}' not found."
            )
        return acc

    @app.post("/transfer", response_model=TransferResponse, tags=["Transfers"])
    def process_transfer(req: TransferRequest):
        # Validate that amount is positive
        if req.amount_inr <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transfer amount must be strictly greater than zero."
            )
        resp = db.execute_transfer(req)
        return resp

    @app.get("/transactions", response_model=List[TransactionRecord], tags=["Audit"])
    def list_audit_transactions(limit: int = 50):
        return db.list_transactions(limit=limit)

    # -------------------------------------------------------------------------
    # Voice Safety & Confirmation Endpoints
    # -------------------------------------------------------------------------
    @app.post("/api/voice/process", tags=["Voice Safety"])
    def process_voice_instruction(req: VoiceProcessRequest):
        """
        Receives spoken or typed payment instructions, runs multilingual Indic amount
        parsing and SahiGuard safety consensus evaluation, and generates spoken response.
        """
        transcript = ""
        if req.text and req.text.strip():
            transcript = req.text.strip()
        elif req.audio_base64:
            try:
                raw_b64 = req.audio_base64
                if "," in raw_b64:
                    raw_b64 = raw_b64.split(",", 1)[1]
                audio_bytes = base64.b64decode(raw_b64)
                if stt_adapter.api_key:
                    stt_res = stt_adapter.transcribe(audio_bytes, mode="transcribe")
                    transcript = stt_res.transcript
                else:
                    transcript = "Audio received (Live STT requires SARVAM_API_KEY in .env)"
            except Exception as e:
                transcript = f"STT error: {str(e)}"

        if not transcript:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either text instruction or audio must be provided."
            )

        # 1. Deterministic amount parsing
        parsed = amount_engine.parse(transcript)

        # 2. SahiGuard safety consensus evaluation
        guard_decision = guard.evaluate_parsed_amount(
            parsed=parsed,
            proposed_by_agent=req.agent_proposed_amount
        )

        # 3. Spoken response text
        if guard_decision.action == GuardAction.EXECUTE:
            spoken_text = f"Transfer of {guard_decision.final_amount_inr} rupees to {req.to_payee} verified. Please confirm to proceed."
        elif guard_decision.action == GuardAction.READ_BACK:
            spoken_text = f"High value transfer of {guard_decision.final_amount_inr} rupees to {req.to_payee}. Read-back required. Please confirm."
        elif guard_decision.action == GuardAction.RE_ASK:
            spoken_text = f"Clarification needed: {guard_decision.explanation}"
        else:  # ESCALATE
            spoken_text = f"Transfer blocked due to high-risk mismatch: {guard_decision.explanation}"

        # 4. Optional TTS synthesis if API key is present
        audio_base64_out = None
        if tts_provider.api_key and guard_decision.action in (GuardAction.EXECUTE, GuardAction.READ_BACK, GuardAction.RE_ASK):
            try:
                tts_res = tts_provider.synthesize(TTSRequest(text=spoken_text, target_language_code="hi-IN"))
                audio_base64_out = "data:audio/wav;base64," + base64.b64encode(tts_res.audio_bytes).decode("ascii")
            except Exception:
                pass

        can_confirm = (
            guard_decision.action in (GuardAction.EXECUTE, GuardAction.READ_BACK)
            and guard_decision.final_amount_inr is not None
            and guard_decision.final_amount_inr > 0
        )

        pending_transfer = None
        if can_confirm:
            pending_transfer = {
                "from_account": req.from_account,
                "to_payee": req.to_payee,
                "amount_inr": guard_decision.final_amount_inr
            }

        return {
            "transcript": transcript,
            "parsed_status": parsed.status.value,
            "parsed_amount": parsed.amount_inr,
            "ambiguity_reason": parsed.ambiguity_reason.value,
            "candidates": parsed.candidates,
            "guard_action": guard_decision.action.value,
            "reason_code": guard_decision.reason_code.value,
            "risk_level": guard_decision.risk_level.value,
            "explanation": guard_decision.explanation,
            "spoken_response": spoken_text,
            "audio_base64": audio_base64_out,
            "can_confirm": can_confirm,
            "pending_transfer": pending_transfer
        }

    @app.post("/api/voice/confirm", tags=["Voice Safety"])
    def confirm_voice_transfer(req: VoiceConfirmRequest):
        """
        Validates confirmation integrity via SahiGuard.evaluate_confirmation.
        If confirmed details strictly match proposed amount and payee, executes
        simulated debit against MockBankDatabase.
        """
        guard_dec = guard.evaluate_confirmation(
            proposed_amount=req.proposed_amount,
            proposed_payee=req.to_payee,
            confirmed_amount=req.confirmed_amount,
            confirmed_payee=req.confirmed_payee,
            is_confirmed=req.is_confirmed
        )

        if guard_dec.action != GuardAction.EXECUTE:
            return {
                "success": False,
                "status": "CONFIRMATION_REJECTED",
                "reason_code": guard_dec.reason_code.value,
                "risk_level": guard_dec.risk_level.value,
                "message": guard_dec.explanation,
                "guard_decision": guard_dec.model_dump()
            }

        # Safe to execute against mock ledger
        transfer_req = TransferRequest(
            from_account=req.from_account,
            to_payee=req.to_payee,
            amount_inr=req.confirmed_amount,
            idempotency_key=f"IDEMP_CONFIRM_{uuid.uuid4().hex[:10].upper()}",
            guard_decision=guard_dec.model_dump(),
            remarks="Voice transfer verified and confirmed by user"
        )
        resp = db.execute_transfer(transfer_req)
        return resp

    return app

# Default instance
app = create_bank_app()
