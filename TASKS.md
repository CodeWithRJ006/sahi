# SAHI Tasks & Execution Checklist

## Status Summary
- **Current Phase:** Session 1 — Architecture & Core Vertical Slice
- **Overall Goal:** Functional local slice (Amount Engine -> SahiGuard -> Mock Bank Ledger) with zero paid API costs, 100% test pass rate, and full git reproducibility.

---

## Task List

### Phase 1: Foundation & Scaffolding
- [x] Audit workspace and verify empty state of `CodeWithRJ006/sahi`
- [x] Produce `REPO_AUDIT.md`, `IMPLEMENTATION_PLAN.md`, `TASKS.md`
- [ ] Initialize repository files: `.gitignore`, `.env.example`, `pyproject.toml`, `README.md`
- [ ] Verify test runner (`pytest`) runs in the project structure

### Phase 2: Stage A — Amount Engine (Indic Parsing to Integer INR)
- [ ] Define data models in `src/sahi/amounts/models.py` (`ParsedAmount`, `ParseStatus`, `AmbiguityReason`, `LanguageGroup`)
- [ ] Implement Indian English & Hinglish amount parser (`src/sahi/amounts/english.py`)
- [ ] Implement Hindi parser for Devanagari and Latin transliteration (`src/sahi/amounts/hindi.py`)
- [ ] Implement Telugu parser for Telugu script and Latin transliteration (`src/sahi/amounts/telugu.py`)
- [ ] Implement self-correction and multi-amount detector (`src/sahi/amounts/ambiguity.py`)
- [ ] Build unified `AmountEngine` (`src/sahi/amounts/engine.py`)
- [ ] Create test suite `tests/test_amounts_engine.py` covering all 4 language groups, fractions, self-corrections, and lakh/crore scales

### Phase 3: Stage D (Early Slice) — SahiGuard Deterministic Safety Guard
- [ ] Define decision models in `src/sahi/guard/models.py` (`GuardDecision`, `GuardAction`, `ReasonCode`, `RiskLevel`)
- [ ] Implement safety rules (`src/sahi/guard/rules.py`):
  - Power-of-ten ratio checks (e.g. 10x, 100x discrepancy)
  - Digit swap / phonetic confusable checks
  - High value threshold escalation (> Rs. 50,000 requires explicit read-back / OTP step)
  - Multi-reading consensus logic
- [ ] Implement `SahiGuard` engine (`src/sahi/guard/engine.py`)
- [ ] Create test suite `tests/test_guard_engine.py` testing disagreements, edge cases, and reason codes

### Phase 4: Stage B — Mock Bank Service & SQLite Ledger
- [ ] Build SQLite persistence layer in `src/sahi/bank/database.py` with tables for `accounts`, `transactions`, and `idempotency_keys`
- [ ] Define bank schemas in `src/sahi/bank/models.py` (`TransferRequest`, `TransferResult`, `AccountState`)
- [ ] Implement FastAPI mock bank service in `src/sahi/bank/app.py`:
  - `POST /transfer` with idempotency validation and atomic execution
  - `GET /accounts/{id}`
  - `GET /transactions`
- [ ] Create test suite `tests/test_mock_bank.py` testing transfer execution, balance deductions, duplicate idempotency rejections, and invalid requests

### Phase 5: Vertical Slice Integration & Verification
- [ ] Implement vertical slice orchestrator `execute_pipeline()` in `src/sahi/pipeline.py`
- [ ] Implement comprehensive golden test cases in `tests/test_vertical_slice.py`
- [ ] Run full pytest suite, verify 100% pass rate
- [ ] Commit verified changes with clear commit messages

### Phase 6: Next Stages Roadmap (Subsequent Sessions)
- [ ] Stage C: Saaras v4 and Sarvam 105B API adapters with response caching and rate limits
- [ ] Stage E: Evaluation benchmark pipeline and dataset runner
- [ ] Stage F: Interactive CLI demo & reporting dashboard
