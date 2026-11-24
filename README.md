# SAHI — Indic Voice Agent Amount Safety Benchmark & Deterministic Guard

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![CI](https://github.com/CodeWithRJ006/sahi/actions/workflows/test.yml/badge.svg)](https://github.com/CodeWithRJ006/sahi/actions/workflows/test.yml)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#running-tests)

**SAHI** is an open-source evaluation benchmark and deterministic safety guard designed to prevent catastrophic monetary transfer errors in Indic voice banking agents.

In conversational voice banking, language models and speech recognizers frequently propose incorrect transaction amounts due to:
- **Power-of-ten scale confusion** (e.g., dropping or adding a zero, confusing *thousand* with *lakh*).
- **Phonetic digit swaps** (e.g., 15 vs 50, *pandrah* vs *pachas*, *padihenu* vs *yabhai*).
- **Colloquial fractional expressions** (e.g., *dhai hazar* [₹2,500], *dedh lakh* [₹1,50,000], *rendunnara velu* [₹2,500]).
- **Spoken self-corrections** (e.g., *"five hundred rupees no wait six hundred rupees"*).
- **Ambiguous or conflicting amounts** (e.g., *"send 500 or 1000 rupees"*, *"send 500 five thousand rupees"*).

SAHI establishes the core architectural principle: **an LLM-generated amount is an unverified proposal, not the authority to move money.** Transactions are never executed merely because an LLM or speech recognizer proposed them.

---

## Key Components

1. **Multilingual Amount Parsing Engine (`AmountEngine`)**:
   - Parses spoken Hindi (Devanagari & Latin script), Telugu (Telugu script & Latin), Hinglish, and Indian English into exact integer INR values.
   - Enforces an absolute maximum transaction ceiling of **₹100,000,000** (₹10 crore).
   - Rejects zero and negative amounts at the parser boundary.
   - Accurately resolves valid self-corrections to the final intended correction, while flagging conflicting or unsafe corrections as `AMBIGUOUS`.
   - Detects word-plus-digit contradictions and disjunctive expressions (*or*, *ya*, *athava*, *leda*).
   - Correctly handles Indian comma grouping (`1,00,000`) and standard international grouping (`100,000`).
   - Disambiguates phone numbers, dates, and account numbers from monetary values.

2. **Deterministic Safety Guard (`SahiGuard`)**:
   - Multi-source agreement evaluation across independent transcripts and LLM proposals.
   - Detects catastrophic power-of-ten mismatches (10x, 100x, 1000x) and escalates.
   - Detects phonetic confusable pairs and prompts for clarification.
   - Enforces straight-through execution limits (default ₹50,000) requiring explicit user read-back for high-value amounts.
   - Validates user confirmation integrity: confirmations are strictly bound to specific amounts and recipient payees.
   - Fail-closed security: missing, ambiguous, or unvalidated proposals cannot execute.

3. **Atomic Mock Bank Ledger (`MockBankDatabase` / FastAPI Service)**:
   - Thread-safe, process-safe simulated banking ledger using SQLite with transaction atomicity.
   - Strict transfer idempotency preventing duplicate debits.
   - Boundary validation for strictly positive amounts, account balance sufficiency, and ceiling limits.
   - Complete audit logging and ledger history.

4. **Live-Pilot Runner & Preflight (`scripts/run_live_pilot.py`)**:
   - Safe offline dry-run by default with zero network or external API calls.
   - Rigorous budget cap enforcement (default ₹10) prior to any paid API execution.
   - Content-addressed caching with automatic credential redaction from cache keys.

---

## Architecture Pipeline

```
           Spoken User Utterance / Audio
                         │
                         ▼
┌──────────────────────────────────────────────────┐
│      Dual-Mode Speech Recognition (Saaras v4)     │
│       - Literal Transcript Mode                  │
│       - Code-mixed Transcript Mode               │
└────────────────────────┬─────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌──────────────────┐           ┌──────────────────┐
│   AmountEngine   │           │    Sarvam 105B   │
│  Deterministic   │           │    LLM Agent     │
│   Amount Parse   │           │ (Proposal Only)  │
└────────┬─────────┘           └────────┬─────────┘
         │                              │
         └───────────────┬──────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────┐
│                    SahiGuard                     │
│        Deterministic Safety Guard Engine         │
│  - Multi-reading consensus verification          │
│  - Power-of-ten mismatch detection (10x, 100x)   │
│  - Phonetic confusable pair checks               │
│  - High-value read-back policy enforcement       │
│  - Confirmation & payee binding checks           │
└────────────────────────┬─────────────────────────┘
                         │
     ┌───────────────────┼───────────────────┐
     ▼                   ▼                   ▼
 [EXECUTE]          [READ_BACK]          [RE_ASK] / [ESCALATE]
     │                   │                   │
     ▼                   │                   ▼
┌──────────────────┐     │            Halt Execution &
│  FastAPI / SQLite│     │            Prompt / Escalate
│    Mock Bank     │◄────┘
│  Atomic Transfer │  (Upon User Confirmation)
└──────────────────┘
```

---

## Supported Languages & Sample Expressions

| Language | Example Spoken Input | Parsed INR |
|---|---|---|
| **Telugu (Script)** | `రెండు వేల ఐదు వందల రూపాయలు` | ₹2,500 |
| **Telugu (Script)** | `రెండు లక్షల రూపాయలు` | ₹2,00,000 |
| **Telugu (Script)** | `రెండు కోట్ల రూపాయలు` | ₹20,000,000 |
| **Telugu (Latin)** | `rendu vela aidu vandalu` | ₹2,500 |
| **Telugu (Latin)** | `rendunnara velu` (colloquial fraction) | ₹2,500 |
| **Hindi (Devanagari)** | `दो हज़ार पाँच सौ रुपये` | ₹2,500 |
| **Hindi (Devanagari)** | `ढाई हज़ार रुपये` | ₹2,500 |
| **Hindi (Devanagari)** | `डेढ़ लाख रुपये` | ₹1,50,000 |
| **Hindi (Latin)** | `dhai hazar rupaye` | ₹2,500 |
| **Hinglish** | `send 5k`, `transfer 5 hazar`, `pay 2.5 lakh` | ₹5,000 / ₹2,50,000 |
| **Indian English** | `twenty five hundred rupees` | ₹2,500 |
| **Indian English** | `two and a half lakhs` | ₹2,50,000 |
| **Indian English** | `ten thousand rupees actually five thousand rupees` | ₹5,000 (Self-corrected) |

---

## Safety Guard Decision Taxonomy

| Guard Action | Trigger Condition | Safety Objective |
|---|---|---|
| `EXECUTE` | All deterministic readings and LLM proposal agree; amount <= straight-through limit (₹50,000). | Safe straight-through processing in mock ledger. |
| `READ_BACK` | All readings agree, but amount exceeds ₹50,000 straight-through threshold. | Requires explicit conversational confirmation before moving money. |
| `RE_ASK` | Disagreement between readings, phonetic confusion (e.g. 15k vs 50k), self-correction ambiguity, or missing readings. | Halts execution; re-prompts the customer for clarification. |
| `ESCALATE` | Critical power-of-ten mismatch (e.g. 5,000 vs 50,000), zero/negative amount, or out-of-bounds ceiling violation. | Immediately halts execution; triggers human-in-the-loop review. |

---

## Quickstart & Commands

### Prerequisites
- Python 3.11, 3.12, or 3.13
- Git

### 1. Installation

**Windows PowerShell:**
```powershell
Set-Location "C:\Users\bokin\Downloads\sahi"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

### 2. Verify Installation
```powershell
python -c "import sahi; print('SAHI package loaded successfully')"
```

### 3. Run Automated Tests
```powershell
pytest -q
```

To run with coverage:
```powershell
pytest --cov=sahi tests/
```

### 4. Run the Deterministic Demo
Runs the vertical slice across three standard safety scenarios:
```powershell
python -m sahi.demo
```
**Expected Outcomes:**
1. `₹2500 भेजो` (Agreement) → `EXECUTE` (mock ledger debited ₹2,500).
2. `₹5000 పంపించు` with simulated 10x LLM proposal `₹50000` → `ESCALATE` (`POWER_OF_TEN_MISMATCH`).
3. `send 500 no wait 5000` (Self-correction conflict) → `RE_ASK` (`PARSE_AMBIGUOUS_SELF_CORRECTION`).

Output is printed as JSON and saved to `demo_results.json`.

### 5. Run Live Pilot Preflight (Safe Dry-Run)
Verifies the pilot manifest, budget calculations, and degradation pipeline offline:
```powershell
python scripts/run_live_pilot.py --dry-run
```
To view CLI options:
```powershell
python scripts/run_live_pilot.py --help
```

---

## Mock Banking Simulation Guarantee

The mock bank ledger (`MockBankDatabase`) is an **isolated SQLite simulation**.
- It **never** connects to any real bank, payment processor, or UPI switch.
- All account IDs (`ACC_USER_001`, `ACC_RAMESH_002`, `ACC_SURESH_003`) are synthetic test fixtures.
- All debits enforce atomic balance checks and idempotency keys to ensure reproducibility.

---

## External API Requirements & Live Pilot Policy

- **Offline / Deterministic Testing**: The complete test suite and demo run 100% offline using deterministic mocks and local fixtures. No API keys or paid accounts are needed.
- **Optional Live Testing**: `test_sarvam_adapters.py:404` contains an opt-in live test that is skipped by default. It only activates when `RUN_LIVE_SARVAM_TESTS=1` and `SARVAM_API_KEY` are explicitly configured in `.env`.
- **Live Pilot Runner**: `scripts/run_live_pilot.py` defaults strictly to `--dry-run`. Live execution via `--execute-live` requires an active `SARVAM_API_KEY` and enforces a hard ₹10 budget cap.

---

## Known Limitations

1. **Dialect and Colloquial Vocabulary**: Telugu and Hindi dialects have varied regional colloquialisms. While common forms (*dhai*, *dedh*, *vandalu*, *kotlu*, *lakshalu*) are fully supported, localized slang outside these sets defaults to `UNRECOGNIZED`.
2. **Sub-Rupee Paise Settlement**: Non-integer decimal paise amounts (e.g. `12.75 rupees`) or fractional paise expressions are flagged as `FRACTION_AMBIGUITY` rather than silently rounded, adhering to bank safety principles.
3. **Synthetic Speech Fixtures**: The evaluation metrics in `report/index.html` reflect offline benchmark simulations. Live acoustic validation across physical speakers remains outside the repository's offline verification boundary.

---

## License

Distributed under the Apache 2.0 License. See [LICENSE](LICENSE) for details.
