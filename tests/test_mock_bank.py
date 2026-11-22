"""Unit and integration tests for Mock Bank and SQLite ledger."""

import pytest
from fastapi.testclient import TestClient
from sahi.bank.database import MockBankDatabase
from sahi.bank.app import create_bank_app
from sahi.bank.models import TransferRequest

@pytest.fixture
def test_db(temp_db_path):
    db = MockBankDatabase(temp_db_path)
    yield db
    db.close()

@pytest.fixture
def client(test_db):
    app = create_bank_app(test_db)
    return TestClient(app)

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["safety_mode"] == "SIMULATION_ONLY"

def test_get_account_balance(client):
    response = client.get("/accounts/ACC_USER_001")
    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == "ACC_USER_001"
    assert data["balance_inr"] == 100_000

def test_execute_transfer_success(client):
    payload = {
        "from_account": "ACC_USER_001",
        "to_payee": "ramesh@upi",
        "amount_inr": 2500,
        "idempotency_key": "IDEMP_KEY_001_A",
        "remarks": "Test transfer"
    }
    response = client.post("/transfer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "SUCCESS"
    assert data["amount_inr"] == 2500
    assert data["new_balance_inr"] == 97500
    assert data["transaction_id"] is not None

    # Check updated balance
    acc_res = client.get("/accounts/ACC_USER_001")
    assert acc_res.json()["balance_inr"] == 97500

def test_idempotency_protection(client):
    payload = {
        "from_account": "ACC_USER_001",
        "to_payee": "suresh@upi",
        "amount_inr": 5000,
        "idempotency_key": "IDEMP_DUPLICATE_TEST_KEY",
    }
    # First request
    res1 = client.post("/transfer", json=payload)
    assert res1.status_code == 200
    assert res1.json()["status"] == "SUCCESS"
    assert res1.json()["new_balance_inr"] == 95000

    # Duplicate request with same key
    res2 = client.post("/transfer", json=payload)
    assert res2.status_code == 200
    assert res2.json()["status"] == "IDEMPOTENT_DUPLICATE"
    assert res2.json()["amount_inr"] == 5000

    # Ensure balance was NOT deducted a second time
    acc_res = client.get("/accounts/ACC_USER_001")
    assert acc_res.json()["balance_inr"] == 95000

def test_insufficient_funds(client):
    payload = {
        "from_account": "ACC_SURESH_003", # balance is 5,000
        "to_payee": "ramesh@upi",
        "amount_inr": 15000,
        "idempotency_key": "IDEMP_OVERDRAW_KEY_001",
    }
    response = client.post("/transfer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["status"] == "INSUFFICIENT_FUNDS"

def test_zero_or_negative_amount_rejected(client):
    payload = {
        "from_account": "ACC_USER_001",
        "to_payee": "ramesh@upi",
        "amount_inr": -500,
        "idempotency_key": "IDEMP_INVALID_AMOUNT",
    }
    response = client.post("/transfer", json=payload)
    assert response.status_code == 422 # Pydantic gt=0 validation error

def test_transactions_audit_log(client):
    payload = {
        "from_account": "ACC_USER_001",
        "to_payee": "ramesh@upi",
        "amount_inr": 1200,
        "idempotency_key": "IDEMP_AUDIT_LOG_KEY",
        "guard_decision": {"action": "EXECUTE", "risk": "LOW"}
    }
    client.post("/transfer", json=payload)
    response = client.get("/transactions")
    assert response.status_code == 200
    txns = response.json()
    assert len(txns) >= 1
    latest = txns[0]
    assert latest["amount_inr"] == 1200
    assert latest["to_payee"] == "ramesh@upi"
    assert latest["guard_decision"]["action"] == "EXECUTE"
