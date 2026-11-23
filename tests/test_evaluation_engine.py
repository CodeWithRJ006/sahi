"""Unit and integration tests for SAHI Stage E evaluation engine, metrics, and reporter."""

import os
import json
import pytest
from unittest.mock import Mock

from sahi.metrics.models import TrialResult, ArmEvaluationSummary
from sahi.metrics.calculator import MetricsCalculator
from sahi.metrics.evaluator import EvaluationHarness
from sahi.metrics.reporter import EvaluationReporter
from sahi.audio.models import AudioClipRecord, AudioCondition
from sahi.dataset.models import BaseUtterance, UtteranceCategory, VerificationStatus
from sahi.bank.database import MockBankDatabase
from sahi.guard.models import GuardAction, ReasonCode

@pytest.fixture
def sample_utterance():
    return BaseUtterance(
        id="UTT_TEST_001",
        language_group="HINDI",
        category=UtteranceCategory.PLAIN_AMOUNT,
        intended_amount_inr=5000,
        native_text="पाँच हज़ार रुपये भेजो",
        romanized_text="paanch hazaar rupaye bhejo"
    )

@pytest.fixture
def sample_clip():
    return AudioClipRecord(
        clip_id="CLIP_UTT_TEST_001_CLEAN",
        utterance_id="UTT_TEST_001",
        condition=AudioCondition.CLEAN,
        sha256_hash="abc123hash",
        sample_rate=16000,
        duration_seconds=1.5,
        provider="mock",
        model="bulbul:v4-flash",
        relative_filepath="clean/CLIP_UTT_TEST_001_CLEAN.wav"
    )

# 1. Metric calculations & zero error handling
def test_metric_calculations_zero_error():
    trials = [
        TrialResult(
            trial_id=f"T_{i}",
            utterance_id=f"UTT_{i}",
            language_group="HINDI",
            category="plain_amount",
            condition=AudioCondition.CLEAN,
            intended_amount_inr=5000,
            executed_amount_inr=5000,
            execution_status="EXECUTED",
            is_completed_transfer=True,
            is_correct=True,
            is_unsafe=False,
            is_silent_wrong=False,
            is_false_hold=False,
            rupees_discrepancy=0
        )
        for i in range(10)
    ]
    summary = MetricsCalculator.summarize_arm("TestArm", trials)
    assert summary.total_trials == 10
    assert summary.wrong_amount_execution_rate == 0.0
    assert summary.unsafe_execution_rate == 0.0
    assert summary.silent_wrong_rate == 0.0
    assert summary.false_hold_rate == 0.0
    assert summary.rupees_at_risk_per_1000 == 0.0

# 2. Incorrect transfer handling and Rupees at risk
def test_metric_calculations_with_errors():
    trials = [
        TrialResult(
            trial_id="T_1",
            utterance_id="UTT_1",
            language_group="HINDI",
            category="plain_amount",
            condition=AudioCondition.CLEAN,
            intended_amount_inr=5000,
            executed_amount_inr=50000,  # 10x error! (discrepancy 45,000)
            execution_status="EXECUTED",
            is_completed_transfer=True,
            is_correct=False,
            is_unsafe=True,
            is_silent_wrong=True,
            rupees_discrepancy=45000
        ),
        TrialResult(
            trial_id="T_2",
            utterance_id="UTT_2",
            language_group="HINDI",
            category="plain_amount",
            condition=AudioCondition.CLEAN,
            intended_amount_inr=2000,
            executed_amount_inr=2000,
            execution_status="EXECUTED",
            is_completed_transfer=True,
            is_correct=True,
            is_unsafe=False,
            is_silent_wrong=False,
            rupees_discrepancy=0
        )
    ]
    summary = MetricsCalculator.summarize_arm("TestArm", trials)
    assert summary.total_completed_transfers == 2
    assert summary.wrong_amount_execution_rate == 0.5
    assert summary.unsafe_execution_rate == 0.5
    assert summary.silent_wrong_rate == 0.5
    # Total discrepancy 45,000 over 2 trials = 22,500 avg * 1000 = 22,500,000 per 1k trials
    assert summary.rupees_at_risk_per_1000 == 22500000.0

# 3. Held transfer and false-hold rate
def test_false_hold_calculation():
    trials = [
        TrialResult(
            trial_id="T_1",
            utterance_id="UTT_1",
            language_group="HINDI",
            category="plain_amount",
            condition=AudioCondition.CLEAN,
            intended_amount_inr=5000,
            executed_amount_inr=None,
            execution_status="HELD_FOR_READBACK",
            is_completed_transfer=False,
            is_false_hold=True,  # False hold: was correct 5000 but held
            rupees_discrepancy=0
        ),
        TrialResult(
            trial_id="T_2",
            utterance_id="UTT_2",
            language_group="HINDI",
            category="plain_amount",
            condition=AudioCondition.CLEAN,
            intended_amount_inr=2000,
            executed_amount_inr=2000,
            execution_status="EXECUTED",
            is_completed_transfer=True,
            is_false_hold=False,
            rupees_discrepancy=0
        )
    ]
    summary = MetricsCalculator.summarize_arm("TestArm", trials)
    assert summary.read_back_rate == 0.5
    assert summary.false_hold_rate == 0.5
    assert summary.wrong_amount_execution_rate == 0.0

# 4. Paired comparison and cluster bootstrap confidence intervals
def test_paired_comparison_and_bootstrap():
    b_trials = []
    g_trials = []

    # 4 utterances, each with 3 conditions = 12 trials
    for u in range(4):
        for c in [AudioCondition.CLEAN, AudioCondition.TELEPHONY, AudioCondition.TELEPHONY_NOISE]:
            tid = f"T_{u}_{c.value}"
            # Baseline fails on utterance 0 condition NOISE (10x error)
            b_unsafe = (u == 0 and c == AudioCondition.TELEPHONY_NOISE)
            g_unsafe = False  # Guard intercepts it!

            b_trials.append(TrialResult(
                trial_id=tid,
                utterance_id=f"UTT_{u}",
                language_group="HINDI",
                category="plain_amount",
                condition=c,
                intended_amount_inr=5000,
                executed_amount_inr=50000 if b_unsafe else 5000,
                execution_status="EXECUTED",
                is_completed_transfer=True,
                is_unsafe=b_unsafe,
                rupees_discrepancy=45000 if b_unsafe else 0
            ))

            g_trials.append(TrialResult(
                trial_id=tid,
                utterance_id=f"UTT_{u}",
                language_group="HINDI",
                category="plain_amount",
                condition=c,
                intended_amount_inr=5000,
                executed_amount_inr=None if b_unsafe else 5000,
                execution_status="ESCALATED" if b_unsafe else "EXECUTED",
                is_completed_transfer=not b_unsafe,
                is_unsafe=g_unsafe,
                rupees_discrepancy=0
            ))

    res = MetricsCalculator.compare_arms(b_trials, g_trials, bootstrap_iterations=500, seed=42)
    assert res.baseline_only_errors == 1
    assert res.guard_only_errors == 0
    assert res.shared_errors == 0
    assert res.unsafe_rate_delta > 0.0
    assert res.rupees_at_risk_delta > 0.0
    assert len(res.unsafe_rate_delta_ci_95) == 2
    assert res.unsafe_rate_delta_ci_95[0] <= res.unsafe_rate_delta_ci_95[1]

# 5. Missing audio handling in EvaluationHarness
def test_missing_audio_handling(sample_clip, sample_utterance):
    harness = EvaluationHarness()
    # Path doesn't exist on disk and audio_bytes is None
    tb, tg = harness.run_clip_trial(sample_clip, sample_utterance, audio_bytes=None)
    assert tb.execution_status == "MISSING_AUDIO"
    assert tg.execution_status == "MISSING_AUDIO"
    assert tb.is_completed_transfer is False

# 6. Separate Mock Bank ledger isolation
def test_mock_bank_ledger_isolation(sample_clip, sample_utterance):
    db_baseline = MockBankDatabase(":memory:")
    db_guarded = MockBankDatabase(":memory:")

    stt_mock = Mock()
    stt_mock.transcribe.return_value = Mock(transcript="send 5000 rupees")

    llm_mock = Mock()
    llm_mock.extract_transfer_proposal.return_value = Mock(
        proposal=Mock(amount_inr=5000, payee="ramesh@upi", raw_arguments={})
    )

    harness = EvaluationHarness(
        saaras_adapter=stt_mock,
        llm_adapter=llm_mock,
        baseline_db=db_baseline,
        guarded_db=db_guarded
    )

    dummy_audio = b"RIFF....WAVE"
    tb, tg = harness.run_clip_trial(sample_clip, sample_utterance, audio_bytes=dummy_audio)

    assert tb.execution_status == "EXECUTED"
    assert tg.execution_status == "EXECUTED"

    # Verify both ledgers recorded exactly 1 transaction independently
    txns_b = db_baseline.list_transactions()
    txns_g = db_guarded.list_transactions()
    assert len(txns_b) == 1
    assert len(txns_g) == 1
    assert txns_b[0].amount_inr == 5000
    assert txns_g[0].amount_inr == 5000
    assert txns_b[0].transaction_id != txns_g[0].transaction_id

    db_baseline.close()
    db_guarded.close()

# 7. Reporter file and plot generation
def test_reporter_generation(tmp_path):
    reporter = EvaluationReporter(output_dir=str(tmp_path / "report"))

    trial = TrialResult(
        trial_id="T_1",
        utterance_id="UTT_1",
        language_group="HINDI",
        category="plain_amount",
        condition=AudioCondition.CLEAN,
        intended_amount_inr=5000,
        executed_amount_inr=5000,
        execution_status="EXECUTED",
        guard_reason=ReasonCode.AGREEMENT_VERIFIED,
        is_completed_transfer=True,
        is_correct=True
    )

    comp = MetricsCalculator.compare_arms([trial], [trial], bootstrap_iterations=10)
    paths = reporter.generate_all(comp, [trial], [trial], is_live_measurement=False)

    assert os.path.isfile(paths["results_json"])
    assert os.path.isfile(paths["evaluation_run_json"])
    assert os.path.isfile(paths["index_html"])
    assert os.path.isfile(paths["baseline_vs_guard_png"])
    assert os.path.isfile(paths["error_by_condition_png"])
    assert os.path.isfile(paths["failure_taxonomy_png"])

    with open(paths["results_json"], "r") as f:
        data = json.load(f)
    assert data["status"] == "SYNTHETIC_SIMULATION"
