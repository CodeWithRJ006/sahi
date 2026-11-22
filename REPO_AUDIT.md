# SAHI — Repository Audit Report

**Date:** 2026-11-23  
**Auditor:** Principal Software Engineer & AI Systems Architect  
**Target Repository:** `https://github.com/CodeWithRJ006/sahi`  
**Workspace Path:** `c:\Users\bokin\Downloads\sahi`  

---

## 1. Executive Summary

A comprehensive pre-implementation audit was conducted on the workspace and GitHub repository prior to creating files or changing code. The workspace was confirmed to be an empty directory designated for the new SAHI project. The target remote `CodeWithRJ006/sahi` was checked via GitHub CLI and verified to exist as an empty repository.

No existing code or unrelated projects were present in the workspace, ensuring a clean slate with zero legacy technical debt or collision risks.

---

## 2. Environment & Dependency Audit

- **Operating System:** Windows 11
- **Python Version:** `Python 3.13.5`
- **Git State:**
  - Initialized local repository: `main` branch.
  - Remote: `origin -> https://github.com/CodeWithRJ006/sahi.git`
  - Git Committer: `CodeWithRJ006 <bokinalarj@gmail.com>`
  - GitHub Authentication: Valid (`gh auth status` confirmed active login for `CodeWithRJ006`).
- **Core Installed Python Packages Verified:**
  - `fastapi` (v0.135.3)
  - `uvicorn` (v0.53.0)
  - `pydantic` (v2.12.5)
  - `pytest` (v9.2.0)
  - `pytest-cov` (v7.1.0)
  - `httpx` (v0.28.1)
  - `python-dotenv` (v1.2.4)
  - `requests` (v2.33.1)
  - `rich` (v14.3.3)
  - `torch` (v2.11.0)
- **Tooling Notes:**
  - `ruff` and `mypy` CLI binaries are not globally installed; code style and typing will be verified with standard Python typing checks and pytest suites.

---

## 3. Scope & Architectural Alignment

The project objective is to build **SAHI: Indic Voice Agent Amount Safety Benchmark and Deterministic Guard**.
Core Pipeline:
```
Audio -> Saaras v4 -> Sarvam 105B -> Amount extraction -> SahiGuard -> Mock Bank -> Evaluation Report
```

Supported Language Groups:
- **Telugu** (e.g., "రెండు వేల ఐదు వందలు", "2 vela 5 vandalu", "rendu vela")
- **Hindi** (e.g., "दो हज़ार पाँच सौ", "do hazar panch sau", "dhai hazar")
- **Hinglish** (e.g., "send 5k", "transfer do hazar", "send 2.5 lakh")
- **Indian English** (e.g., "twenty five hundred rupees", "two and a half lakhs", "transfer 5000")

Key Constraint:
- Zero connection to real banking or payment rails. All execution connects strictly to a local mock ledger with idempotency controls.

---

## 4. Immediate Action Items

1. Create initial project scaffolding: `.gitignore`, `.env.example`, `pyproject.toml`, and README.
2. Formulate `IMPLEMENTATION_PLAN.md` and `TASKS.md` covering Stages A through F.
3. Implement the Stage 1 vertical slice:
   - Multilingual text amount parser into integer INR with explicit unrecognised/ambiguous states.
   - Deterministic SahiGuard rule verification.
   - Local FastAPI / SQLite Mock Bank with idempotency and audit ledger.
   - Comprehensive unit and integration test suite executing 100% locally with zero paid API costs.
