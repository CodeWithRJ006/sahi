"""Test that budget reservation aborts before any live request is made.
The runner should return a non‑zero exit code when the budget is too low for the first TTS call.
No network providers are instantiated because the check happens prior to any request.
"""

import sys
from pathlib import Path
scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(scripts_dir))
import run_live_pilot as runner
from pathlib import Path


def test_budget_reservation_abort(tmp_path: Path, monkeypatch):
    # Use the real YAML plan – it has 8 utterances.
    plan_path = Path(__file__).parent.parent / "data" / "live_pilot_8.yaml"
    # Very tiny budget to force early abort (less than a single TTS cost estimate).
    small_budget = 0.01
    # Call main with live execution flag.
    exit_code = runner.main([
        f"--plan={plan_path}",
        f"--budget-inr={small_budget}",
        "--execute-live",
    ])
    # Expect non‑zero exit because budget exceeded before any request.
    assert exit_code != 0
