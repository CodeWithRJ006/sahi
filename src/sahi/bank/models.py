"""Pydantic models for Mock Bank API and ledger."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class TransferRequest(BaseModel):
    from_account: str = Field(..., description="Source account ID (e.g. 'ACC_USER_001')")
    to_payee: str = Field(..., description="Payee name or VPA (e.g. 'ramesh@upi', 'Suresh')")
    amount_inr: int = Field(..., gt=0, description="Exact integer amount in INR to transfer (> 0)")
    idempotency_key: str = Field(..., min_length=8, description="Unique client-provided idempotency key")
    guard_decision: Optional[Dict[str, Any]] = Field(None, description="Serialized SahiGuard decision record")
    remarks: Optional[str] = None

class TransferResponse(BaseModel):
    success: bool
    status: str = Field(..., description="SUCCESS, REJECTED, IDEMPOTENT_DUPLICATE, INSUFFICIENT_FUNDS")
    transaction_id: Optional[str] = None
    from_account: str
    to_payee: str
    amount_inr: int
    new_balance_inr: Optional[int] = None
    message: str
    idempotency_key: str
    timestamp: str

class AccountBalance(BaseModel):
    account_id: str
    holder_name: str
    balance_inr: int
    created_at: str

class TransactionRecord(BaseModel):
    transaction_id: str
    from_account: str
    to_payee: str
    amount_inr: int
    status: str
    guard_decision: Optional[Dict[str, Any]] = None
    idempotency_key: str
    created_at: str
