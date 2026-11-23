import json
import os
from pathlib import Path

from sahi.demo.__main__ import run_demo

def test_demo_results_structure(tmp_path: Path):
    # Run demo and capture results
    results = run_demo()
    # Write results to a temporary file to simulate output generation
    output_file = tmp_path / "demo_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    # Load back and validate structure
    with open(output_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert isinstance(loaded, list)
    assert len(loaded) == 3
    # Check each scenario has expected keys
    expected_keys = {"scenario", "utterance", "intended_amount", "parsed_amount", "llm_proposal", "guard_decision", "reason_code", "ledger"}
    for entry in loaded:
        assert expected_keys.issubset(entry.keys())
        # Ensure ledger is a list of performed transfers (may be empty)
        assert isinstance(entry["ledger"], list)

def test_demo_successful_execution():
    results = run_demo()
    # Scenario A should have EXECUTE decision and ledger with one entry
    scenario_a = next(r for r in results if r["scenario"] == "A_SUCCESS")
    assert scenario_a["guard_decision"] == "EXECUTE"
    assert scenario_a["ledger"] == [{"amount": scenario_a["intended_amount"], "utterance": scenario_a["utterance"]}]

def test_demo_wrong_amount():
    results = run_demo()
    scenario_b = next(r for r in results if r["scenario"] == "B_WRONG_AMOUNT")
    assert scenario_b["guard_decision"] == "ESCALATE"
    assert scenario_b["ledger"] == []

def test_demo_ambiguous():
    results = run_demo()
    scenario_c = next(r for r in results if r["scenario"] == "C_AMBIGUOUS")
    assert scenario_c["guard_decision"] == "RE_ASK"
    assert scenario_c["ledger"] == []
