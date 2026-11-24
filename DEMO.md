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
pip install -r requirements.txt
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

* No real audio files are processed – the demo works purely with text fixtures.
* No live calls to Saaras, Sarvam, or TTS providers are made.
* Results are synthetic; they illustrate the control flow rather than performance or cost.

---

For a real‑audio pilot, see `LIVE_PILOT_PREFLIGHT.md`.
