# LIVE PILOT CHECKLIST

## Safety & Operational Preconditions

- **No live API calls** have been made during pre‑flight. All steps are offline.
- **Native‑speaker verification**: All eight utterances remain `verification_status: VERIFIED`. Do **not** run TTS until a native speaker has approved each phrase.
- **Hinglish language code**: Use `hi-IN` (supported Bulbul code) for Hinglish entries.
- **Speaker identifiers**: `voice_1`‑`voice_8` are placeholders. Replace with actual Bulbul catalogue voice IDs before generation.
- **Cost cap**: Budgeted total (including 30 % buffer) = **₹5.46** pre‑GST. Proposed spending limit remains **₹10**.
- **Request accounting**: 80 external API requests (8 TTS, 24 STT, 24 Codemix, 24 LLM) + 24 local audio transformations = **104** operations.
- **Unnatural phrasing**: Flagged phrase `₹500 किल्ली भेजो` (utt_07) for native‑speaker review.
- **Documentation**: Ensure `LIVE_PILOT_PREFLIGHT.md` and `LIVE_PILOT_REVIEW.md` are attached to the project.

## Acceptance Criteria for Live Pilot Execution

1. All utterances have `verification_status: VERIFIED`.
2. Bulbul speaker IDs are confirmed and listed.
3. Final cost estimate (including taxes) stays ≤ ₹10.
4. No code changes are required beyond the pre‑flight corrections.
5. Run the pilot only after explicit authorization.
