"""End-to-End Vertical Slice Integration Tests for SAHI."""

import pytest
from sahi.pipeline import SahiPipeline
from sahi.bank.database import MockBankDatabase
from sahi.guard.models import GuardAction, ReasonCode

@pytest.fixture
def pipeline(temp_db_path):
    bank_db = MockBankDatabase(temp_db_path)
    p = SahiPipeline(bank_db=bank_db)
    yield p
    bank_db.close()

def test_vertical_slice_hindi_success(pipeline):
    # Spoken Hindi: "दो हज़ार पाँच सौ रुपये" (2,500 INR)
    result = pipeline.process_utterance(
        utterance="दो हज़ार पाँच सौ रुपये",
        from_account="ACC_USER_001",
        to_payee="ramesh@upi",
        idempotency_key="IDEMP_HINDI_001"
    )
    assert result.status == "EXECUTED"
    assert result.parsed_amount.amount_inr == 2500
    assert result.guard_decision.action == GuardAction.EXECUTE
    assert result.transfer_response is not None
    assert result.transfer_response.success is True
    assert result.transfer_response.new_balance_inr == 97500

    # Verify transaction in bank audit log
    txns = pipeline.bank_db.list_transactions()
    assert len(txns) == 1
    assert txns[0].amount_inr == 2500
    assert txns[0].status == "SUCCESS"

def test_vertical_slice_telugu_success(pipeline):
    # Spoken Telugu: "rendunnara velu pampu" (2,500 INR)
    result = pipeline.process_utterance(
        utterance="rendunnara velu pampu",
        from_account="ACC_USER_001",
        to_payee="suresh@upi",
        idempotency_key="IDEMP_TELUGU_001"
    )
    assert result.status == "EXECUTED"
    assert result.parsed_amount.amount_inr == 2500
    assert result.transfer_response.success is True
    assert result.transfer_response.new_balance_inr == 97500

def test_vertical_slice_power_of_ten_interception(pipeline):
    # User says "send 5000", but agent or upstream proposes 50,000 (10x error)
    result = pipeline.process_utterance(
        utterance="send 5000 rupees to Ramesh",
        from_account="ACC_USER_001",
        to_payee="ramesh@upi",
        agent_proposed_amount=50000,
        idempotency_key="IDEMP_P10_ATTACK_001"
    )
    assert result.status == "ESCALATED"
    assert result.guard_decision.action == GuardAction.ESCALATE
    assert result.guard_decision.reason_code == ReasonCode.POWER_OF_TEN_MISMATCH
    assert result.transfer_response is None

    # Verify no funds deducted from mock bank
    acc = pipeline.bank_db.get_account("ACC_USER_001")
    assert acc.balance_inr == 100000

def test_vertical_slice_self_correction_hold(pipeline):
    # Spoken self-correction: "send 500 no wait 5000"
    result = pipeline.process_utterance(
        utterance="send 500 no wait 5000 rupees",
        from_account="ACC_USER_001",
        to_payee="ramesh@upi"
    )
    assert result.status == "HELD_FOR_CLARIFICATION"
    assert result.guard_decision.action == GuardAction.RE_ASK
    assert result.guard_decision.reason_code == ReasonCode.PARSE_AMBIGUOUS_SELF_CORRECTION
    assert result.transfer_response is None

    # Balance remains untouched
    acc = pipeline.bank_db.get_account("ACC_USER_001")
    assert acc.balance_inr == 100000

def test_vertical_slice_high_value_readback_hold(pipeline):
    # Large amount > 50,000 INR
    result = pipeline.process_utterance(
        utterance="pay 75000 rupees",
        from_account="ACC_USER_001",
        to_payee="suresh@upi"
    )
    assert result.status == "HELD_FOR_READBACK"
    assert result.guard_decision.action == GuardAction.READ_BACK
    assert result.guard_decision.reason_code == ReasonCode.HIGH_VALUE_THRESHOLD
    assert result.transfer_response is None

    # Balance remains untouched
    acc = pipeline.bank_db.get_account("ACC_USER_001")
    assert acc.balance_inr == 100000

def test_vertical_slice_unrecognized_text(pipeline):
    result = pipeline.process_utterance(
        utterance="namaste please do something",
        from_account="ACC_USER_001",
        to_payee="suresh@upi"
    )
    assert result.status == "HELD_FOR_CLARIFICATION"
    assert result.guard_decision.action == GuardAction.RE_ASK
    assert result.guard_decision.reason_code == ReasonCode.PARSE_UNRECOGNIZED
    assert result.transfer_response is None
