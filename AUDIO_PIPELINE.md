# SAHI Audio Generation & Degradation Pipeline

## 1. Architectural Overview

```
Base Utterance (Text)
         │
         ▼
┌─────────────────────────────────┐
│     TTS Engine (Bulbul v4)      │
│      Base64 PCM Decode          │
└────────────────┬────────────────┘
                 │
                 ▼
          [Condition: CLEAN]
                 │
                 ├──────────────────────────────────────┐
                 ▼                                      ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│      Telephony Degradation      │   │    Telephony + Noise Engine     │
│   - Resample to 8,000 Hz        │   │   - Telephony pipeline          │
│   - 300 - 3,400 Hz Band-pass    │   │   - Deterministic 10 dB SNR     │
│   - G.711 μ-law Companding      │   │     Gaussian Noise Injection    │
└────────────────┬────────────────┘   └────────────────┬────────────────┘
                 ▼                                      ▼
       [Condition: TELEPHONY]                 [Condition: NOISY]
```

---

## 2. DSP Implementation Details

### A. Telephony Condition
- **Resampling:** High-precision Fourier/polyphase resampling via `scipy.signal.resample` down to **8,000 Hz**.
- **Bandpass Filtering:** 4th-order Butterworth filter with cutoffs at $f_{low} = 300\text{ Hz}$ and $f_{high} = 3400\text{ Hz}$ implemented in Second-Order Sections (SOS) for numerical stability.
- **ITU-T G.711 μ-law Companding:** 16-bit linear PCM compressed to 8-bit non-linear logarithmic curve ($y = \text{sgn}(x)\frac{\ln(1 + \mu|x|)}{\ln(1 + \mu)}$ with $\mu = 255$) and decompressed back to linear PCM to reproduce authentic mobile/landline quantization distortion.

### B. Telephony Noise Condition (Calibrated 10 dB SNR)
- Signal power measured: $P_{\text{signal}} = \frac{1}{N}\sum_{i=1}^N x_i^2$
- Target noise variance: $P_{\text{noise}} = \frac{P_{\text{signal}}}{10^{\text{SNR} / 10}}$ with $\text{SNR} = 10.0\text{ dB}$
- Noise generation: Deterministic Gaussian generator seeded with fixed state (`seed=42`).
- Verification: Measured SNR confirmed to be within **$\pm 0.5\text{ dB}$** of target across all generated clips.

---

## 3. Caching & Provenance Tracking

- **Key Derivation:** Deterministic SHA-256 hash computed over `(provider, model, action, payload, parameters)`.
- **Atomic Persistence:** Temporary file staging with atomic file replacement (`os.replace`) prevents corrupt reads during concurrent test execution.
- **Zero Secret Ingress:** Credentials, tokens, and authorization headers are systematically stripped before key calculation or payload caching.
