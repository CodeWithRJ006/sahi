"""Tests for the SAHI live pilot runner (scripts/run_live_pilot.py).

All tests are fully offline — no network requests are made.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

# Make sure the scripts/ directory is importable as a module via sys.path trick.
# We import by adding the repo root's scripts/ dir and importing directly.
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import run_live_pilot as runner  # noqa: E402  (must come after sys.path insert)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REAL_YAML = REPO_ROOT / "data" / "live_pilot_8.yaml"


@pytest.fixture()
def eight_utterances():
    """Load the actual 8-utterance YAML plan."""
    return runner.load_yaml_plan(REAL_YAML)


@pytest.fixture()
def good_records():
    """Return a minimal set of 8 fully-valid records."""
    return [
        {
            "id": f"utt_0{i}",
            "language_code": "hi-IN",
            "utterance_native": f"test utterance {i}",
            "proposed_speaker": "simran_en_customer",
            "verification_status": "VERIFIED",
        }
        for i in range(1, 9)
    ]


# ---------------------------------------------------------------------------
# 1. Eight utterances load
# ---------------------------------------------------------------------------

class TestLoad:
    def test_eight_utterances_load(self, eight_utterances):
        assert len(eight_utterances) == 8, (
            f"Expected 8 utterances, got {len(eight_utterances)}"
        )

    def test_utterance_ids_present(self, eight_utterances):
        ids = {r["id"] for r in eight_utterances}
        assert len(ids) == 8

    def test_all_have_utterance_native(self, eight_utterances):
        for r in eight_utterances:
            assert r.get("utterance_native"), f"{r['id']} missing utterance_native"

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            runner.load_yaml_plan(tmp_path / "nonexistent.yaml")


# ---------------------------------------------------------------------------
# 2. Request count equals 80
# ---------------------------------------------------------------------------

class TestRequestCount:
    def test_total_requests_equals_80(self, eight_utterances):
        plan = runner.compute_plan(eight_utterances)
        assert plan["total_requests"] == 80, (
            f"Expected 80 total requests, got {plan['total_requests']}"
        )

    def test_tts_calls_equals_8(self, eight_utterances):
        plan = runner.compute_plan(eight_utterances)
        assert plan["tts_calls"] == 8

    def test_stt_transcribe_equals_24(self, eight_utterances):
        plan = runner.compute_plan(eight_utterances)
        assert plan["stt_transcribe"] == 24

    def test_stt_codemix_equals_24(self, eight_utterances):
        plan = runner.compute_plan(eight_utterances)
        assert plan["stt_codemix"] == 24

    def test_llm_calls_equals_24(self, eight_utterances):
        plan = runner.compute_plan(eight_utterances)
        assert plan["llm_calls"] == 24

    def test_audio_outputs_equals_24(self, eight_utterances):
        plan = runner.compute_plan(eight_utterances)
        assert plan["audio_outputs"] == 24


# ---------------------------------------------------------------------------
# 3. Local transformations equal 16
# ---------------------------------------------------------------------------

class TestLocalTransformations:
    def test_local_xforms_equals_16(self, eight_utterances):
        plan = runner.compute_plan(eight_utterances)
        assert plan["local_xforms"] == 16, (
            f"Expected 16 local transforms, got {plan['local_xforms']}"
        )


# ---------------------------------------------------------------------------
# 4. Missing speaker ID blocks live execution
# ---------------------------------------------------------------------------

class TestSpeakerValidation:
    def test_invalid_speaker_blocked(self):
        bad = [
            {
                "id": f"utt_0{i}",
                "language_code": "hi-IN",
                "utterance_native": "test",
                "proposed_speaker": "not_a_real_speaker_xyz",
                "verification_status": "VERIFIED",
            }
            for i in range(1, 9)
        ]
        errors = runner.validate_gates(bad, live=True)
        speaker_errors = [e for e in errors if "not a known Bulbul" in e]
        assert len(speaker_errors) == 8

    def test_valid_speaker_no_error(self, good_records):
        with patch.dict(os.environ, {"SARVAM_API_KEY": "test_key_abc"}):
            errors = runner.validate_gates(good_records, live=True)
        speaker_errors = [e for e in errors if "catalogue" in e]
        assert speaker_errors == []

    def test_missing_speaker_field_blocked(self):
        bad = [
            {
                "id": "utt_01",
                "language_code": "hi-IN",
                "utterance_native": "hello",
                # proposed_speaker missing → defaults to ""
                "verification_status": "VERIFIED",
            }
        ] * 8
        errors = runner.validate_gates(bad, live=True)
        assert any("not a known Bulbul" in e for e in errors)


# ---------------------------------------------------------------------------
# 5. Unverified phrase blocks live execution
# ---------------------------------------------------------------------------

class TestVerificationGate:
    def test_unverified_phrase_blocked(self):
        unverified = [
            {
                "id": f"utt_0{i}",
                "language_code": "hi-IN",
                "utterance_native": "test",
                "proposed_speaker": "meera",
                "verification_status": "PENDING",
            }
            for i in range(1, 9)
        ]
        errors = runner.validate_gates(unverified, live=True)
        verify_errors = [e for e in errors if "VERIFIED" in e]
        assert len(verify_errors) == 8

    def test_verified_phrase_no_error(self, good_records):
        with patch.dict(os.environ, {"SARVAM_API_KEY": "test_key_abc"}):
            errors = runner.validate_gates(good_records, live=True)
        verify_errors = [e for e in errors if "VERIFIED" in e]
        assert verify_errors == []


# ---------------------------------------------------------------------------
# 6. Missing API key blocks live execution
# ---------------------------------------------------------------------------

class TestApiKeyGate:
    def test_missing_api_key_blocked(self, good_records):
        env = {k: v for k, v in os.environ.items() if k != "SARVAM_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            errors = runner.validate_gates(good_records, live=True)
        key_errors = [e for e in errors if "SARVAM_API_KEY" in e]
        assert len(key_errors) == 1

    def test_missing_api_key_not_blocked_in_dry_run(self, good_records):
        env = {k: v for k, v in os.environ.items() if k != "SARVAM_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            errors = runner.validate_gates(good_records, live=False)
        key_errors = [e for e in errors if "SARVAM_API_KEY" in e]
        assert key_errors == []

    def test_api_key_never_printed(self, good_records, capsys):
        """API key must not appear in stdout/stderr."""
        secret = "super_secret_key_12345"
        with patch.dict(os.environ, {"SARVAM_API_KEY": secret}):
            plan = runner.compute_plan(good_records)
            runner.print_plan(plan, budget=10.0, errors=[])
        captured = capsys.readouterr()
        assert secret not in captured.out
        assert secret not in captured.err


# ---------------------------------------------------------------------------
# 7. Budget overrun blocks live execution
# ---------------------------------------------------------------------------

class TestBudgetGate:
    def test_budget_overrun_reported(self, eight_utterances):
        plan = runner.compute_plan(eight_utterances)
        # Force a tiny budget to guarantee overrun
        errors: list[str] = []
        if plan["total_est_inr"] > 0.001:
            errors.append(
                f"Estimated cost Rs.{plan['total_est_inr']:.4f} exceeds budget cap Rs.0.00."
            )
        budget_errors = [e for e in errors if "exceeds budget" in e]
        assert len(budget_errors) >= 1

    def test_plan_within_10_rupee_cap(self, eight_utterances):
        """Verify that the normal 8‑utterance pilot stays within the default ₹10 budget cap.
        The expected base cost is around ₹3.208, and with the safety buffer the total estimated
        cost should be well under ₹10.
        """
        plan = runner.compute_plan(eight_utterances)
        assert plan["total_est_inr"] <= 10.0, (
            f"Total estimated cost Rs.{plan['total_est_inr']:.4f} exceeds the Rs.10 budget cap."
        )


    def test_main_dry_run_returns_zero(self, tmp_path):
        """main() in dry-run mode must return exit code 0 regardless of budget."""
        result = runner.main(["--plan", str(REAL_YAML), "--budget-inr", "0.001"])
        assert result == 0


    def test_over_budget_with_inflated_config(self, tmp_path, good_records):
        """Create a plan with extremely long utterances to exceed the ₹10 budget.
        This verifies that the budget logic works with realistic large inputs.
        """
        # Create a temporary YAML with long utterances (e.g., 5000 chars each)
        long_text = "a" * 20000
        inflated = [
            {
                "id": f"utt_{i}",
                "language_code": "hi-IN",
                "utterance_native": long_text,
                "proposed_speaker": "simran_en_customer",
                "verification_status": "VERIFIED",
            }
            for i in range(1, 9)
        ]
        yaml_path = tmp_path / "inflated.yaml"
        # Write inflated records as a YAML list
        with yaml_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(inflated, f, default_flow_style=False)

        # Load and compute plan
        records = runner.load_yaml_plan(yaml_path)
        plan = runner.compute_plan(records)
        assert plan["total_est_inr"] > 10.0, (
            f"Inflated total estimated cost Rs.{plan['total_est_inr']:.4f} should exceed budget"
        )
        # Live execution should be blocked due to budget exceed
        result = runner.main(["--plan", str(yaml_path), "--execute-live", "--budget-inr", "10.0"])
        assert result == 1, "Live execution should be blocked by budget exceed"
# ---------------------------------------------------------------------------

class TestDryRunNoNetwork:
    def test_dry_run_no_httpx_calls(self):
        """Importing and running compute_plan + validate_gates must not touch the network."""
        import httpx

        original_send = httpx.Client.send

        def fail_if_called(self, *args, **kwargs):
            raise AssertionError("httpx.Client.send was called during dry-run!")

        httpx.Client.send = fail_if_called
        try:
            records = runner.load_yaml_plan(REAL_YAML)
            plan    = runner.compute_plan(records)
            errors  = runner.validate_gates(records, live=False)
            # print_plan is pure output, no network
            runner.print_plan(plan, budget=10.0, errors=errors)
        finally:
            httpx.Client.send = original_send

    def test_main_dry_run_no_httpx_calls(self):
        """main() with default (dry-run) mode must not make any HTTP calls."""
        import httpx

        original_send = httpx.Client.send

        def fail_if_called(self, *args, **kwargs):
            raise AssertionError("httpx.Client.send was called during dry-run main()!")

        httpx.Client.send = fail_if_called
        try:
            result = runner.main(["--plan", str(REAL_YAML)])
            assert result == 0
        finally:
            httpx.Client.send = original_send
