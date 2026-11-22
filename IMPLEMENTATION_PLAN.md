# SAHI Implementation Plan: Indic Voice Agent Amount Safety Benchmark & Deterministic Guard

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an open-source, reproducible evaluation system and deterministic guard (SahiGuard) that measures whether Indic voice agents correctly understand spoken Indian monetary amounts and prevents incorrect simulated transfers to a mock bank ledger.

**Architecture:** A modular pipeline comprising multilingual Indic amount parsing (Telugu, Hindi, Hinglish, Indian English), a deterministic safety guard (SahiGuard) that evaluates multiple readings against high-risk failure modes (power-of-ten, scale/unit, fraction, digit swap, ambiguity), a local FastAPI/SQLite mock bank with strict idempotency and audit logs, and an evaluation suite.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, SQLite3, Pytest, HTTPX, Rich.

**Spec:** Master Engineering Execution Directive (Indic Voice Agent Amount Safety Benchmark & Deterministic Guard).

---

## Global Constraints

- Never connect to real banking, UPI, or payment systems; mock ledger only.
- Deterministic local tests only for core logic — zero paid API calls without explicit authorization.
- Handle ambiguity and self-correction by returning explicit `AMBIGUOUS` or `UNRECOGNIZED` parse results rather than guessing.
- Prevent duplicate execution using cryptographic or client-provided idempotency keys in the mock bank.
- Never expose or commit secrets (`.env` is in `.gitignore`, `.env.example` provided).
- Maintain rigorous typing and test coverage for all parsing and decision paths.

---

## Review Focus: Top 5 High-Risk Failure Modes

1. **Power-of-Ten / Scale Confusion:** Conflating "lakh" (1,00,000) vs "hazar/thousand" (1,000) or extra/missing zeroes (e.g., 50,000 vs 5,00,000). SahiGuard must flag 10x/100x scale discrepancies as critical holds.
2. **Fractional Number Expression Misinterpretation:** Ambiguous or colloquial half/quarter multipliers (e.g. Hindi "साढ़े तीन हज़ार" / "dhai hazar" / "dedh lakh", Telugu "రెండున్నర వేలు" / "rendunnara velu").
3. **Spoken Self-Correction & Multi-Amount Utterances:** User changes mind mid-sentence ("send 500, no wait, 5000", "send 200 to Ramesh and 500 to Suresh"). Parser must flag multiple amounts or self-corrections as `AMBIGUOUS`.
4. **Digit Reversals / Confusables:** Phonetic or transcription confusions (e.g., 15 vs 50, 19 vs 90, 70 vs 17). SahiGuard disagreement detection must prevent auto-execution.
5. **Replay & Concurrency Attacks:** Simultaneous or duplicate simulated voice execution requests attempting double spend. Mock Bank must reject duplicate idempotency keys.

---

## Architecture Decomposition & Module Directory

```
sahi/
├── src/
│   └── sahi/
│       ├── __init__.py
│       ├── amounts/               # Amount normalization and Indic language parsing
│       │   ├── __init__.py
│       │   ├── models.py          # ParsedAmount, AmountConfidence, AmbiguityReason
│       │   ├── normalizer.py      # Script cleaners, tokenizers
│       │   ├── english.py         # Indian English & Hinglish amount parser
│       │   ├── hindi.py           # Devanagari & Latin Hindi parser
│       │   ├── telugu.py          # Telugu script & Latin Telugu parser
│       │   └── engine.py          # Unified Multilingual Amount Engine
│       ├── guard/                 # SahiGuard deterministic safety guard
│       │   ├── __init__.py
│       │   ├── models.py          # GuardDecision, ActionType, RiskCategory
│       │   ├── rules.py           # Power-of-ten, scale, fraction, conflict rules
│       │   └── engine.py          # SahiGuard verification engine
│       ├── bank/                  # Mock Bank API & SQLite ledger
│       │   ├── __init__.py
│       │   ├── database.py        # SQLite connection & schema management
│       │   ├── models.py          # TransferRequest, TransferResponse, TransactionRecord
│       │   └── app.py             # FastAPI service (POST /transfer, GET /transactions)
│       ├── dataset/               # Golden test benchmarks
│       │   ├── __init__.py
│       │   └── loader.py
│       └── metrics/               # Evaluation statistics & risk metrics
│           ├── __init__.py
│           └── calculator.py
├── tests/
│   ├── conftest.py
│   ├── test_amounts_engine.py     # Multilingual amount parsing tests
│   ├── test_guard_engine.py       # SahiGuard safety policy tests
│   ├── test_mock_bank.py          # Mock bank API & idempotency tests
│   └── test_vertical_slice.py     # End-to-end integration test of Slice 1
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
├── REPO_AUDIT.md
├── IMPLEMENTATION_PLAN.md
└── TASKS.md
```

---

## Phased Implementation Sequence

### Phase 1: Repository Scaffolding & Configuration
- Set up `.gitignore`, `.env.example`, `pyproject.toml`, base packaging structure.

### Phase 2: Amount Engine (Stage A)
- Implement `ParsedAmount` domain model with integer INR representation, status flags (`PARSED`, `AMBIGUOUS`, `UNRECOGNIZED`), and scale metadata.
- Implement language parsers:
  - Indian English (e.g. "twenty five hundred", "two and a half lakhs", "5k").
  - Hindi in Devanagari and Latin (e.g. "दो हज़ार", "dhai hazar", "dedh lakh").
  - Telugu in Telugu script and Latin (e.g. "రెండు వేలు", "rendu vela", "rendunnara velu").
- Implement multi-amount and self-correction detection.
- Unified `AmountEngine` that routes or aggregates multilingual input.

### Phase 3: SahiGuard Deterministic Safety Guard (Stage D slice)
- Implement `SahiGuard` decision engine:
  - Actions: `EXECUTE`, `READ_BACK`, `RE_ASK`, `ESCALATE`.
  - Checkers: Single reading sanity, dual/triple reading agreement, scale/power-of-ten mismatch, digit transposition, amount threshold risk policy.
  - Machine-readable decision codes (`PERFECT_MATCH`, `POWER_OF_TEN_DISCREPANCY`, `SCALE_UNIT_MISMATCH`, `MULTIPLE_AMOUNTS_DETECTED`, `HIGH_VALUE_THRESHOLD`).

### Phase 4: Mock Bank API & SQLite Ledger (Stage B)
- SQLite database schema with transactions, account balances, and idempotency key table.
- FastAPI endpoint `POST /transfer` with idempotency validation, payee format checking, and balance checking.
- Audit ledger queries `GET /transactions` and `GET /transactions/{id}`.

### Phase 5: Vertical Slice Integration & Verification
- Connect: Text input -> AmountEngine -> SahiGuard -> Mock Bank.
- Golden test dataset with positive, negative, and adversarial test cases.
- Comprehensive pytest execution with 100% passing tests.
