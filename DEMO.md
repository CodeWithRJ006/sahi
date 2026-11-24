# Demo

## Overview

This demo showcases the SAHI pipeline in a fully deterministic, locally reproducible way. It runs three pre‑defined scenarios without making any external API calls:

* **Scenario A – SUCCESS** – A clear Hindi utterance for ₹2,500 that is parsed, proposed, and safely executed.
* **Scenario B – WRONG_AMOUNT** – A Telugu utterance where the LLM proposal disagrees with the parsed amount, causing the guard to **ESCALATE**.
* **Scenario C – AMBIGUOUS** – A Hinglish utterance with conflicting amounts, leading the guard to **RE_ASK** for clarification.

The demo prints a JSON summary of each scenario, writes the same data to `demo_results.json` and returns a deterministic result suitable for documentation or testing.

## Setup

```bash
# Install project dependencies (if not already installed)
pip install -e ".[dev]"
```

The demo does not require audio files, network access, or API keys – it relies on mocked adapters inside the existing `Pipeline` implementation (using `mock_mode=True`).

## Running the demo

```bash
python -m sahi.demo
```

Expected output (formatted):

```json
[
  {
    "scenario": "A_SUCCESS",
    "utterance": "₹2500 भेजो",
    "intended_amount": 2500,
    "parsed_amount": 2500,
    "llm_proposal": 2500,
    "guard_decision": "EXECUTE",
    "reason_code": "AGREEMENT_VERIFIED",
    "ledger": [
      {
        "amount": 2500,
        "utterance": "₹2500 भेजो"
      }
    ]
  },
  {
    "scenario": "B_WRONG_AMOUNT",
    "utterance": "₹5000 పంపించు",
    "intended_amount": 5000,
    "parsed_amount": 5000,
    "llm_proposal": 50000,
    "guard_decision": "ESCALATE",
    "reason_code": "POWER_OF_TEN_MISMATCH",
    "ledger": []
  },
  {
    "scenario": "C_AMBIGUOUS",
    "utterance": "send 500 no wait 5000",
    "intended_amount": 0,
    "parsed_amount": null,
    "llm_proposal": null,
    "guard_decision": "RE_ASK",
    "reason_code": "PARSE_AMBIGUOUS_SELF_CORRECTION",
    "ledger": []
  }
]
```

The same JSON is written to `demo_results.json` at the repository root.

## How it works

The demo re‑uses the existing SAHI components:

* `SahiPipeline` – the core end‑to‑end pipeline (with `mock_mode=True`).
* `SahiGuard` – deterministic safety checks.
* `MockBankDatabase` – an in‑memory SQLite ledger.
* `AmountEngine` – language‑aware amount parsing.

Only the fixture data for transcripts and LLM proposals is hard‑coded for reproducibility.

## Limitations

* No real audio files are processed in `sahi.demo` – the terminal demo works purely with text fixtures.
* No live calls to Saaras, Sarvam, or TTS providers are made unless configured in `.env`.
* Results are synthetic; they illustrate the control flow rather than performance or cost.

---

## Interactive SAHI Live Browser Demo

To launch the interactive browser interface with push-to-talk microphone support, preset safety scenarios, and simulated ledger execution:

```bash
python -m uvicorn sahi.bank.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` in your browser:
1. **Push-to-Talk Voice Input**: Click the microphone icon to record speech in Hindi, Telugu, Hinglish, or English (or click any of the preset scenario buttons).
2. **Deterministic Safety Guard**: Observe SahiGuard's real-time safety classification (`EXECUTE`, `READ_BACK`, `RE_ASK`, `ESCALATE`), reason code, and candidate figures.
3. **Confirmation & Ledger Execution**: For approved transactions, click "Confirm Payment" to execute against the simulated SQLite bank ledger via `SahiGuard.evaluate_confirmation`.
4. **Live Audit Trail**: View real-time account balances and transaction ledger records.

---

For a real‑audio pilot preflight, see `LIVE_PILOT_PREFLIGHT.md`.
