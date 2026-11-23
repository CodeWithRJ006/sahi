# SAHI Tasks & Execution Checklist

## Status Summary
- **Current Phase:** Session 1 — Architecture & Core Vertical Slice
- **Overall Goal:** Functional local slice (Amount Engine -> SahiGuard -> Mock Bank Ledger) with zero paid API costs, 100% test pass rate, and full git reproducibility.

---

## Task List

### Phase 1: Foundation & Scaffolding
- [x] Audit workspace and verify empty state of `CodeWithRJ006/sahi`
- [x] Produce `REPO_AUDIT.md`, `IMPLEMENTATION_PLAN.md`, `TASKS.md`
- [x] Initialize repository files: `.gitignore`, `.env.example`, `pyproject.toml`, `README.md`
- [x] Verify test runner (`pytest`) runs in the project structure

### Phase 2: Stage A — Amount Engine (Indic Parsing to Integer INR)
- [x] Define data models in `src/sahi/amounts/models.py` (`ParsedAmount`, `ParseStatus`, `AmbiguityReason`, `LanguageGroup`)
- [x] Implement Indian English & Hinglish amount parser (`src/sahi/amounts/english.py`)
- [x] Implement Hindi parser for Devanagari and Latin transliteration (`src/sahi/amounts/hindi.py`)
- [x] Implement Telugu parser for Telugu script and Latin transliteration (`src/sahi/amounts/telugu.py`)
- [x] Implement self-correction and multi-amount detector (`src/sahi/amounts/normalizer.py` and `src/sahi/amounts/engine.py`)
- [x] Build unified `AmountEngine` (`src/sahi/amounts/engine.py`)
- [x] Create test suite `tests/test_amounts_engine.py` covering all 4 language groups, fractions, self-corrections, and lakh/crore scales

### Phase 3: Stage D (Early Slice) — SahiGuard Deterministic Safety Guard
- [x] Define decision models in `src/sahi/guard/models.py` (`GuardDecision`, `GuardAction`, `ReasonCode`, `RiskLevel`)
- [x] Implement safety rules (`src/sahi/guard/rules.py`):
  - Power-of-ten ratio checks (e.g. 10x, 100x discrepancy)
  - Digit swap / phonetic confusable checks
  - High value threshold escalation (> Rs. 50,000 requires explicit read-back)
  - Multi-reading consensus logic
- [x] Implement `SahiGuard` engine (`src/sahi/guard/engine.py`)
- [x] Create test suite `tests/test_guard_engine.py` testing disagreements, edge cases, and reason codes

### Phase 4: Stage B — Mock Bank Service & SQLite Ledger
- [x] Build SQLite persistence layer in `src/sahi/bank/database.py` with tables for `accounts`, `transactions`, and `idempotency_keys`
- [x] Define bank schemas in `src/sahi/bank/models.py` (`TransferRequest`, `TransferResponse`, `AccountBalance`, `TransactionRecord`)
- [x] Implement FastAPI mock bank service in `src/sahi/bank/app.py`:
  - `POST /transfer` with idempotency validation and atomic execution
  - `GET /accounts/{id}`
  - `GET /transactions`
- [x] Create test suite `tests/test_mock_bank.py` testing transfer execution, balance deductions, duplicate idempotency rejections, and invalid requests

### Phase 5: Vertical Slice Integration & Verification
- [x] Implement vertical slice orchestrator `SahiPipeline` in `src/sahi/pipeline.py`
- [x] Implement comprehensive golden test cases in `tests/test_vertical_slice.py`
- [x] Run full pytest suite, verify 100% pass rate (34 passed, 93% line coverage)
- [x] Commit and push verified changes to `origin main`

### Phase 8: Stage E — Experimental Evaluation Engine
- [x] Create pre-registration protocol defining metrics, exclusions, and limitations (`PREREG.md`)
- [x] Implement evaluation data models (`TrialResult`, `ArmEvaluationSummary`, `PairedComparisonResult`) in `src/sahi/metrics/models.py`
- [x] Implement safety metrics calculator with utterance-level cluster bootstrap (10,000 resamples) in `src/sahi/metrics/calculator.py`
- [x] Implement benchmark evaluation harness with strict ground-truth isolation and isolated mock bank ledgers in `src/sahi/metrics/evaluator.py`
- [x] Implement reporting generator producing `results.json`, `evaluation_run.json`, `report/index.html`, and matplotlib plots in `src/sahi/metrics/reporter.py`
- [x] Implement unit and integration tests in `tests/test_evaluation_engine.py` (67 passed, 1 skipped)
- [x] Execute benchmark runner producing verified reports and visual charts (`report/` and root `results.json`)
