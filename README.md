# SAHI — Indic Voice Agent Amount Safety Benchmark & Deterministic Guard

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#running-tests)

**SAHI** is an open-source evaluation benchmark and deterministic safety guard designed to prevent catastrophic monetary transfer errors in Indic voice banking agents.

Indic voice banking agents frequently misunderstand spoken Indian currency figures due to power-of-ten confusion ("thousand" vs "lakh"), phonetic digit swaps (15 vs 50, 70 vs 17), colloquial fractional expressions ("dhai hazar", "rendunnara velu"), and self-corrections ("send 500, no wait 5000"). SAHI provides:

1. **Multilingual Amount Normalizer & Parser**: Parses spoken Hindi (Devanagari & Latin), Telugu (Telugu script & Latin), Hinglish, and Indian English into exact integer INR values. Returns explicit `AMBIGUOUS` or `UNRECOGNIZED` tokens rather than hallucinating amounts.
2. **SahiGuard Deterministic Safety Engine**: Compares multiple transcript readings and agent interpretations to catch scale mismatches (10x, 100x), phonetic digit swaps, high-value anomalies, and conflicting amounts before any transfer occurs.
3. **Idempotent Mock Banking Service**: A lightweight FastAPI + SQLite ledger ensuring zero real-money connections, strict transfer idempotency, and complete audit logging.
4. **Safety Benchmark Metrics**: Quantifies wrong-amount execution rate, silent-wrong rate, false-hold rate, and Rupees-at-Risk across speech variations.

---

## Architecture Pipeline

```
Spoken Audio / Transcript
         │
         ▼
┌──────────────────────────────────────┐
│       Multilingual Amount Engine     │
│  (Hindi, Telugu, Hinglish, English)   │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│               SahiGuard              │
│    Deterministic Disagreement &      │
│         Risk Policy Engine           │
└──────────────────┬───────────────────┘
                   │
       ┌───────────┴───────────┐
       ▼                       ▼
 [RE-ASK / ESCALATE]     [SAFE TO EXECUTE]
                               │
                               ▼
                ┌──────────────────────────────┐
                │       FastAPI Mock Bank      │
                │     SQLite Audit Ledger      │
                │    Idempotency Protection    │
                └──────────────────────────────┘
```

---

## Supported Language Groups

- **Telugu**: e.g., "రెండు వేల ఐదు వందలు" (2,500), "rendu lakshalu" (2,00,000), "rendunnara velu" (2,500)
- **Hindi**: e.g., "दो हज़ार पाँच सौ" (2,500), "dhai hazar" (2,500), "dedh lakh" (1,50,000)
- **Hinglish**: e.g., "send 5k", "transfer do hazar", "send 2.5 lakh"
- **Indian English**: e.g., "twenty five hundred rupees", "two and a half lakhs", "transfer 5000"

---

## Quickstart

### 1. Installation
Clone repository and install dependencies:
```bash
git clone https://github.com/CodeWithRJ006/sahi.git
cd sahi
pip install -e .
```

### 2. Running Tests
Run the deterministic local test suite:
```bash
pytest -v
```

---

## Safety Disclaimer

**SAHI is strictly an engineering benchmark and simulation harness.** It never connects to real payment gateways, UPI rails, or actual banking APIs. All transfers execute against an isolated local SQLite ledger.
