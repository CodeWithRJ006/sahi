# SAHI Dataset Card: Indic Voice Agent Amount Benchmark (Pilot-24)

## 1. Dataset Summary

The SAHI Pilot Dataset consists of **24 hand-curated base utterances** spanning **4 language groups**:
- **Indian English** (6 utterances)
- **Hindi** (6 utterances)
- **Telugu** (6 utterances)
- **Hinglish** (6 utterances)

Each base utterance is paired with ground truth monetary intent in integer INR and evaluated across **3 audio conditions** (producing **72 benchmark clips** total):
1. `CLEAN`: High-fidelity synthetic speech.
2. `TELEPHONY`: Standard telecom conditions (8,000 Hz, mono, 300–3400 Hz bandpass, G.711 μ-law companding).
3. `TELEPHONY_NOISE`: Telephony condition degraded with calibrated Gaussian noise at **10 dB SNR**.

---

## 2. Benchmark Categories & Linguistic Coverage

Across each language group, the pilot exercises six high-risk failure modes:

| Category | Linguistic Characteristic | Example (Hindi/Telugu/English) | Key Risk Tested |
| :--- | :--- | :--- | :--- |
| **Plain Amount** | Standard numerals / number words | "रमेश को पाँच हज़ार रुपये भेजो" (₹5,000) | Baseline parsing accuracy |
| **Lakh / Crore** | Indian numbering scale markers | "सुरेश को डेढ़ लाख रुपये भेज दो" (₹1,50,000) | Power-of-ten scale confusion (10x, 100x) |
| **Fractional** | Colloquial multipliers (dedh, dhai, sadhe, rendunnara) | "రెండున్నర వేలు ట్రాన్స్‌ఫర్ చేయి" (₹2,500) | Half/quarter math error |
| **Confusable** | Phonetically adjacent pairs (15 vs 50, 17 vs 70) | "పదిహేను వేల రూపాయలు పంపించు" (₹15,000 vs ₹50,000) | Phonetic transposition error |
| **Code-Mixing** | Mixed Indic and English tokens | "Please pay do lakh पचास हज़ार via UPI" (₹2,50,000) | Multi-script token parsing |
| **Self-Correction** | Mid-utterance change of mind | "Send 500 rupees, no wait, make that 5000" | Preventing premature auto-execution |

---

## 3. Provenance & Distinction

> [!IMPORTANT]
> **Synthetic vs. Real-Human Audio:**
> The current pilot dataset clips are generated via synthetic TTS providers (Sarvam Bulbul v4 Flash and AI4Bharat Indic Parler-TTS stub) coupled with deterministic DSP degradation. They are designed for stress-testing and baseline calibration. They do NOT represent organic production telephony call traffic.

---

## 4. TTS Providers & Dry-Run Cost Analysis

1. **Sarvam Bulbul v4 Flash (`bulbul:v4-flash`):**
   - Published rate: ₹1.00 per 1,000 characters (₹20 per 10,000 characters).
   - Pilot dataset character count: **846 characters**.
   - Estimated synthesis cost for entire pilot: **₹0.85 INR** (under $0.02 USD).
2. **AI4Bharat Indic Parler-TTS:**
   - License: Apache 2.0 (open source).
   - Weight size: ~2.45 GB.
   - External API cost: ₹0.00.
   - Status: Evaluated and stubbed locally; weights not downloaded without explicit approval.
