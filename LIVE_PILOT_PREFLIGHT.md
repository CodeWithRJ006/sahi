# LIVE PILOT PREFLIGHT (FINAL CORRECTIONS)

**Purpose** – Exploratory eight‑utterance pilot to collect real audio evidence for SAHI. This is *not* a statistically powered benchmark.

## Service cost estimates (pre‑flight)

| Service | Unit cost | Units (estimated) | Cost (₹) |
|---------|-----------|-------------------|----------|
| **Bulbul v4 Flash (TTS)** | ₹1 per 1,000 characters | 240 characters ≈ 0.24 k chars | **0.24** |
| **Saaras STT (transcribe)** | ₹0.49 per minute | 24 clips × 2 modes × ≤5 s = 4 min | **1.96** |
| **Saaras Codemix** (same endpoint as STT, billed per second) | ₹0.49 per minute | 24 clips × 2 modes = 4 min | **1.96** |
| **Sarvam 105B (LLM)** | ₹15 per million input tokens, ₹60 per million output tokens | 24 requests × (≈ 18 input + 25 output) tokens ≈ 1,032 tokens total | **0.042** |
| **Subtotal** | | | **4.20** |
| **30 % safety buffer** | | | **1.26** |
| **Total (pre‑GST)** | | | **5.46** |

The buffer is generous; the **proposed spending cap is ₹10** to comfortably accommodate any token‑count variance and tax.

## Request accounting

- **External API calls:** 8 TTS + 24 STT + 24 Codemix + 24 LLM = **80**
- **Local audio transformations:** 24 degraded wavs (clean → telephony → noisy) = **24**
- **Total operations:** **104**

## Language & speaker notes

- Hinglish entries now use the supported Bulbul language code **`hi-IN`** (mixed Hindi‑English text).
- Speaker identifiers `voice_1` … `voice_8` are **place‑holder IDs**. Replace them with actual Bulbul catalogue IDs before generation.

## Verification status

All eight utterances are marked `verification_status: UNVERIFIED`. Native‑speaker review is required before any live TTS production.

---

*No live API calls have been made. This document is for budgeting and planning only.*