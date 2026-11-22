"""FastAPI Mock Bank service for safe simulated transfer execution."""

import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from sahi.bank.models import TransferRequest, TransferResponse, AccountBalance, TransactionRecord
from sahi.bank.database import MockBankDatabase

def create_bank_app(db: Optional[MockBankDatabase] = None) -> FastAPI:
    if db is None:
        db_path = os.getenv("MOCK_BANK_DB_PATH", "data/mock_bank.sqlite3")
        os.makedirs(os.path.dirname(db_path), exist_ok=True) if os.path.dirname(db_path) else None
        db = MockBankDatabase(db_path)

    app = FastAPI(
        title="SAHI Mock Bank Ledger",
        description="Safe, isolated mock banking API with strict idempotency and audit ledger.",
        version="0.1.0"
    )

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

    return app

# Default instance
app = create_bank_app()
