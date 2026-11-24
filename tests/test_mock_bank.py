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

def test_direct_database_boundary_rejections(test_db):
    from sahi.bank.models import TransferRequest
    import pytest
    from pydantic import ValidationError

    # Pydantic validation rejects negative or zero amount at model layer
    with pytest.raises(ValidationError):
        TransferRequest(
            from_account="ACC_USER_001",
            to_payee="ramesh@upi",
            amount_inr=-500,
            idempotency_key="IDEMP_NEG_01"
        )

    with pytest.raises(ValidationError):
        TransferRequest(
            from_account="ACC_USER_001",
            to_payee="ramesh@upi",
            amount_inr=0,
            idempotency_key="IDEMP_ZERO_01"
        )

    # If validation is bypassed via model_construct, database boundary still rejects it
    req_bypassed = TransferRequest.model_construct(
        from_account="ACC_USER_001",
        to_payee="ramesh@upi",
        amount_inr=-500,
        idempotency_key="IDEMP_BYPASS_01"
    )
    res_bypassed = test_db.execute_transfer(req_bypassed)
    assert res_bypassed.success is False
    assert res_bypassed.status == "REJECTED"

    # Exceeding ceiling limit (100,000,000)
    req_large = TransferRequest(
        from_account="ACC_USER_001",
        to_payee="ramesh@upi",
        amount_inr=100_000_001,
        idempotency_key="IDEMP_LARGE_01"
    )
    res_large = test_db.execute_transfer(req_large)
    assert res_large.success is False
    assert res_large.status == "REJECTED"

    # Empty payee
    req_nopayee = TransferRequest.model_construct(
        from_account="ACC_USER_001",
        to_payee="",
        amount_inr=1000,
        idempotency_key="IDEMP_NOPAYEE_01"
    )
    res_nopayee = test_db.execute_transfer(req_nopayee)
    assert res_nopayee.success is False
    assert res_nopayee.status == "REJECTED"

def test_concurrent_transfers_consistency(test_db):
    import concurrent.futures
    from sahi.bank.models import TransferRequest

    initial_acc = test_db.get_account("ACC_USER_001")
    initial_balance = initial_acc.balance_inr
    transfer_amount = 1000
    num_threads = 10

    def make_transfer(idx):
        req = TransferRequest(
            from_account="ACC_USER_001",
            to_payee=f"user_{idx}@upi",
            amount_inr=transfer_amount,
            idempotency_key=f"CONCURRENT_TX_{idx}"
        )
        return test_db.execute_transfer(req)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        results = list(executor.map(make_transfer, range(num_threads)))

    for r in results:
        assert r.success is True
        assert r.status == "SUCCESS"

    final_acc = test_db.get_account("ACC_USER_001")
    expected_balance = initial_balance - (transfer_amount * num_threads)
    assert final_acc.balance_inr == expected_balance


def test_get_live_ui(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "SAHI Live" in res.text

    res_live = client.get("/live")
    assert res_live.status_code == 200
    assert "SAHI Live" in res_live.text


def test_voice_process_execute_scenario(client):
    payload = {
        "text": "₹2500 भेजो",
        "to_payee": "ramesh@upi",
        "from_account": "ACC_USER_001",
        "agent_proposed_amount": 2500
    }
    res = client.post("/api/voice/process", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["guard_action"] == "EXECUTE"
    assert data["parsed_amount"] == 2500
    assert data["reason_code"] == "AGREEMENT_VERIFIED"
    assert data["can_confirm"] is True
    assert data["pending_transfer"]["amount_inr"] == 2500


def test_voice_process_10x_mismatch_escalate(client):
    payload = {
        "text": "₹5000 పంపించు",
        "to_payee": "ramesh@upi",
        "from_account": "ACC_USER_001",
        "agent_proposed_amount": 50000
    }
    res = client.post("/api/voice/process", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["guard_action"] == "ESCALATE"
    assert data["reason_code"] == "POWER_OF_TEN_MISMATCH"
    assert data["can_confirm"] is False


def test_voice_process_ambiguous_self_correction_reask(client):
    payload = {
        "text": "send 500 no wait 5000",
        "to_payee": "ramesh@upi",
        "from_account": "ACC_USER_001"
    }
    res = client.post("/api/voice/process", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["guard_action"] == "RE_ASK"
    assert data["reason_code"] == "PARSE_AMBIGUOUS_SELF_CORRECTION"
    assert data["can_confirm"] is False


def test_voice_confirm_flow(client):
    # Step 1: Matching confirmation executes transfer
    payload_ok = {
        "from_account": "ACC_USER_001",
        "to_payee": "ramesh@upi",
        "proposed_amount": 2500,
        "confirmed_amount": 2500,
        "confirmed_payee": "ramesh@upi",
        "is_confirmed": True
    }
    res_ok = client.post("/api/voice/confirm", json=payload_ok)
    assert res_ok.status_code == 200
    data_ok = res_ok.json()
    assert data_ok["success"] is True
    assert data_ok["status"] == "SUCCESS"
    assert data_ok["amount_inr"] == 2500

    # Step 2: Mismatched confirmed amount is rejected by evaluate_confirmation
    payload_mismatch = {
        "from_account": "ACC_USER_001",
        "to_payee": "ramesh@upi",
        "proposed_amount": 2500,
        "confirmed_amount": 25000,  # Altered!
        "confirmed_payee": "ramesh@upi",
        "is_confirmed": True
    }
    res_mismatch = client.post("/api/voice/confirm", json=payload_mismatch)
    assert res_mismatch.status_code == 200
    data_mismatch = res_mismatch.json()
    assert data_mismatch["success"] is False
    assert data_mismatch["status"] == "CONFIRMATION_REJECTED"
    assert data_mismatch["reason_code"] == "CONFIRMATION_MISMATCH"
