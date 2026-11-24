# scripts/run_live_pilot.py
"""SAHI live pilot runner — complete offline dry-run planner.

Design constraints:
- Dry-run is the default; it NEVER makes network requests.
- Live execution requires --execute-live AND SARVAM_API_KEY AND all gates pass.
- Hard limit: 80 external requests, Rs.10 budget cap.
- Every external response is cached via ContentAddressedCache.
- API key is never printed.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Catalogue of valid Bulbul speaker IDs (from Sarvam docs)
# ---------------------------------------------------------------------------
VALID_SPEAKER_IDS: set[str] = {
    "simran_en_customer",   # English
    "ritu_hi_customer",     # Hindi
    "simran_enhi_customer", # Hinglish
    "kavitha_te_conversation", # Telugu
}

# ---------------------------------------------------------------------------
# Pipeline accounting constants
# ---------------------------------------------------------------------------
UTTERANCES_REQUIRED       = 8
STT_MODES_PER_UTTERANCE   = 3   # transcribe + codemix + (verbatim or translate — 3 total per pipeline)
# Per spec: 24 transcribe + 24 codemix → 2 STT calls per utterance × 8 = 16 STT
# But spec says 24 transcribe + 24 codemix = 48 STT requests.
# 48 / 8 utterances = 6 STT calls each. With 3 degraded copies × 2 modes = 6. ✓
DEGRADATIONS_PER_UTTERANCE = 2   # original + 1 degraded = 2 audio variants (×8 = 16 local transforms)
STT_MODES                 = ("transcribe", "codemix")

# 1 TTS + (3 audio variants × 2 STT modes) = 1 + 6 = 7 external requests + 3 LLM = 10 per utterance
# Spec: 8 TTS + 24 STT-transcribe + 24 STT-codemix + 24 LLM = 80. 24/8 = 3 audio variants × 2 modes + 3 LLM.
AUDIO_VARIANTS_PER_UTTERANCE = 3   # original + 2 degraded
LLM_CALLS_PER_UTTERANCE      = 3   # one per audio variant

EXPECTED_TTS_CALLS    = UTTERANCES_REQUIRED                                              # 8
EXPECTED_STT_CALLS    = UTTERANCES_REQUIRED * AUDIO_VARIANTS_PER_UTTERANCE * len(STT_MODES)  # 48? No...
# Re-read spec: 24 transcribe + 24 codemix = 48 STT. 48/8 = 6 STT per utterance.
# 6 = 3 variants × 2 modes. ✓
EXPECTED_LLM_CALLS    = UTTERANCES_REQUIRED * LLM_CALLS_PER_UTTERANCE                   # 24
EXPECTED_LOCAL_XFORMS = UTTERANCES_REQUIRED * AUDIO_VARIANTS_PER_UTTERANCE              # 24? No...
# Spec says 16 local degradation transformations.
# 16 / 8 utterances = 2 transforms each (original→SNR, original→codec).
# Audio outputs = 24 = 3 variants × 8. ✓
LOCAL_DEGRADATIONS_PER_UTTERANCE = 2   # 2 transforms applied to original → 2 degraded copies
EXPECTED_LOCAL_XFORMS = UTTERANCES_REQUIRED * LOCAL_DEGRADATIONS_PER_UTTERANCE          # 16
EXPECTED_AUDIO_OUTPUTS = UTTERANCES_REQUIRED * AUDIO_VARIANTS_PER_UTTERANCE             # 24

EXPECTED_STT_TRANSCRIBE = UTTERANCES_REQUIRED * AUDIO_VARIANTS_PER_UTTERANCE            # 24
EXPECTED_STT_CODEMIX    = UTTERANCES_REQUIRED * AUDIO_VARIANTS_PER_UTTERANCE            # 24
EXPECTED_TOTAL_REQUESTS = (
    EXPECTED_TTS_CALLS + EXPECTED_STT_TRANSCRIBE + EXPECTED_STT_CODEMIX + EXPECTED_LLM_CALLS
)  # 8 + 24 + 24 + 24 = 80

# Cost assumptions (INR)
TTS_COST_PER_1000_CHARS    = 1.00   # Rs.1 / 1,000 chars — from SarvamBulbulProvider
STT_COST_PER_MIN           = 0.75   # Rs.0.75 / minute of audio
LLM_INPUT_TOKENS_PER_CALL  = 400    # conservative estimate
LLM_OUTPUT_TOKENS_PER_CALL = 80
LLM_COST_PER_1M_INPUT      = 60.0   # Rs.60 / 1M input tokens (Sarvam 105B approx)
LLM_COST_PER_1M_OUTPUT     = 240.0  # Rs.240 / 1M output tokens
AVG_AUDIO_DURATION_SEC     = 3.0    # assumed mean TTS output per utterance
BUDGET_BUFFER_FRACTION     = 0.20   # 20% safety buffer


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def load_yaml_plan(yaml_path: Path) -> list[dict[str, Any]]:
    """Load utterance records from live_pilot_8.yaml."""
    if not yaml_path.is_file():
        raise FileNotFoundError(f"YAML plan not found: {yaml_path}")
    with yaml_path.open(encoding="utf-8") as fh:
        records = yaml.safe_load(fh)
    if not isinstance(records, list):
        raise ValueError("YAML plan must be a top-level list of utterance records.")
    return records


def validate_gates(records: list[dict[str, Any]], live: bool) -> list[str]:
    """Return list of blocking error messages; empty → all gates pass.
    In dry‑run we only enforce speaker existence; verification_status is required only for live execution.
    """
    errors: list[str] = []

    if len(records) < UTTERANCES_REQUIRED:
        errors.append(
            f"Only {len(records)} utterances found; {UTTERANCES_REQUIRED} required."
        )

    for rec in records:
        uid = rec.get("id", "<unknown>")
        speaker = rec.get("proposed_speaker", "")
        status  = rec.get("verification_status", "")

        if speaker not in VALID_SPEAKER_IDS:
            errors.append(
                f"{uid}: proposed_speaker '{speaker}' is not a known Bulbul catalogue ID."
            )
        if live and status != "VERIFIED":
            errors.append(
                f"{uid}: verification_status is '{status}'; must be VERIFIED before live execution."
            )

    if live:
        api_key = os.environ.get("SARVAM_API_KEY", "")
        if not api_key:
            errors.append("SARVAM_API_KEY is not set. Live execution requires a valid key.")

    return errors


def compute_plan(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute the full request plan without making any network calls."""
    n = len(records)

    total_chars = sum(len(r.get("utterance_native", "")) for r in records)
    tts_calls = n
    stt_transcribe = n * AUDIO_VARIANTS_PER_UTTERANCE
    stt_codemix = n * AUDIO_VARIANTS_PER_UTTERANCE
    llm_calls = n * LLM_CALLS_PER_UTTERANCE
    local_xforms = n * LOCAL_DEGRADATIONS_PER_UTTERANCE
    audio_outputs = n * AUDIO_VARIANTS_PER_UTTERANCE
    total_requests = tts_calls + stt_transcribe + stt_codemix + llm_calls
    total_audio_min = (n * AVG_AUDIO_DURATION_SEC * AUDIO_VARIANTS_PER_UTTERANCE) / 60.0

    # Cost calculations
    tts_cost = (total_chars / 1000.0) * TTS_COST_PER_1000_CHARS
    stt_cost = total_audio_min * STT_COST_PER_MIN
    llm_input_cost = (llm_calls * LLM_INPUT_TOKENS_PER_CALL / 1_000_000) * LLM_COST_PER_1M_INPUT
    llm_output_cost = (llm_calls * LLM_OUTPUT_TOKENS_PER_CALL / 1_000_000) * LLM_COST_PER_1M_OUTPUT
    llm_cost = llm_input_cost + llm_output_cost
    base_cost = tts_cost + stt_cost + llm_cost
    buffer = base_cost * BUDGET_BUFFER_FRACTION
    total_est = base_cost + buffer

    return {
        "utterances": n,
        "tts_calls": tts_calls,
        "stt_transcribe": stt_transcribe,
        "stt_codemix": stt_codemix,
        "llm_calls": llm_calls,
        "total_requests": total_requests,
        "local_xforms": local_xforms,
        "audio_outputs": audio_outputs,
        "total_chars": total_chars,
        "total_audio_min": round(total_audio_min, 3),
        "tts_cost_inr": round(tts_cost, 4),
        "stt_cost_inr": round(stt_cost, 4),
        "llm_cost_inr": round(llm_cost, 4),
        "base_cost_inr": round(base_cost, 4),
        "buffer_inr": round(buffer, 4),
        "total_est_inr": round(total_est, 4),
        "llm_input_tokens": llm_calls * LLM_INPUT_TOKENS_PER_CALL,
        "llm_output_tokens": llm_calls * LLM_OUTPUT_TOKENS_PER_CALL,
    }


def print_plan(plan: dict[str, Any], budget: float, errors: list[str]) -> None:
    """Print the structured dry-run preflight report."""
    sep = "=" * 56

    print(f"\n{sep}")
    print("  SAHI LIVE PILOT — OFFLINE DRY-RUN PREFLIGHT REPORT")
    print(sep)

    print(f"\n  Utterances loaded          : {plan['utterances']} / {UTTERANCES_REQUIRED} required")
    print(f"  Audio variants per utt.    : {AUDIO_VARIANTS_PER_UTTERANCE}")
    print(f"  WAV files planned          : {plan['audio_outputs']}")
    print(f"  Local degradation xforms   : {plan['local_xforms']}")

    print(f"\n  Requests by provider")
    print(f"    Bulbul TTS               : {plan['tts_calls']}")
    print(f"    Saaras transcribe        : {plan['stt_transcribe']}")
    print(f"    Saaras codemix           : {plan['stt_codemix']}")
    print(f"    Sarvam 105B LLM          : {plan['llm_calls']}")
    print(f"    ─────────────────────────")
    print(f"    Total external requests  : {plan['total_requests']}  (hard limit: {EXPECTED_TOTAL_REQUESTS})")

    print(f"\n  Audio estimate")
    print(f"    Assumed duration/utt.    : {AVG_AUDIO_DURATION_SEC} s")
    print(f"    Total audio              : {plan['total_audio_min']:.3f} min")

    print(f"\n  Token assumptions (LLM)")
    print(f"    Input  per call          : {LLM_INPUT_TOKENS_PER_CALL} tokens")
    print(f"    Output per call          : {LLM_OUTPUT_TOKENS_PER_CALL} tokens")
    print(f"    Total input tokens       : {plan['llm_input_tokens']}")
    print(f"    Total output tokens      : {plan['llm_output_tokens']}")

    print(f"\n  Cost estimate (INR)")
    print(f"    TTS   (Rs.{TTS_COST_PER_1000_CHARS:.2f}/1k chars, {plan['total_chars']} chars) : Rs.{plan['tts_cost_inr']:.4f}")
    print(f"    STT   (Rs.{STT_COST_PER_MIN:.2f}/min, {plan['total_audio_min']:.3f} min)     : Rs.{plan['stt_cost_inr']:.4f}")
    print(f"    LLM   (input + output tokens)             : Rs.{plan['llm_cost_inr']:.4f}")
    print(f"    Base cost                                 : Rs.{plan['base_cost_inr']:.4f}")
    print(f"    Buffer ({int(BUDGET_BUFFER_FRACTION*100)}%)                           : Rs.{plan['buffer_inr']:.4f}")
    print(f"    Total estimated                           : Rs.{plan['total_est_inr']:.4f}")

    print(f"\n  Budget cap                 : Rs.{budget:.2f}")
    over = plan['total_est_inr'] > budget
    status_str = "EXCEEDS BUDGET — live execution blocked" if over else "within budget"
    print(f"  Budget verdict             : {status_str}")

    if errors:
        print(f"\n  Gate failures ({len(errors)})")
        for e in errors:
            print(f"    [BLOCKED] {e}")
    else:
        print(f"\n  All preflight gates        : PASSED")

    print(f"\n{sep}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns exit code (0 = ok, 1 = gate failure)."""
    repo_root = Path(__file__).resolve().parent.parent
    default_yaml = repo_root / "data" / "live_pilot_8.yaml"

    parser = argparse.ArgumentParser(
        description="SAHI live pilot preflight runner."
    )
    # Primary inputs
    parser.add_argument(
        "--plan",
        type=Path,
        default=default_yaml,
        help=f"Path to utterance YAML plan (default: {default_yaml})",
    )
    parser.add_argument(
        "--budget-inr",
        type=float,
        default=10.0,
        help="Spending cap in INR (default: Rs.10).",
    )
    # Mutually exclusive execution mode flags – dry-run is default
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Run offline without making API calls (default).",
    )
    mode_group.add_argument(
        "--execute-live",
        action="store_true",
        help="Enable actual API calls after all safety gates pass.",
    )
    # Parse arguments BEFORE any access
    args = parser.parse_args(argv)
    # Determine mode – dry-run unless live is explicitly requested
    dry_run = not args.execute_live
    # Print execution mode for clarity
    print(f"Execution mode: {'dry‑run' if dry_run else 'live'}")

    # Load plan
    records = load_yaml_plan(args.plan)

    # Gate validation (always check speaker + verification; add API key check only for live)
    errors = validate_gates(records, live=args.execute_live)

    # Compute plan
    plan = compute_plan(records)

    # Hard request cap
    if plan["total_requests"] > EXPECTED_TOTAL_REQUESTS:
        errors.append(
            f"Request count {plan['total_requests']} exceeds hard limit {EXPECTED_TOTAL_REQUESTS}."
        )

    # Budget cap
    budget_exceeded = plan["total_est_inr"] > args.budget_inr
    if budget_exceeded:
        errors.append(
            f"Estimated cost Rs.{plan['total_est_inr']:.4f} exceeds budget cap Rs.{args.budget_inr:.2f}."
        )

    print_plan(plan, args.budget_inr, errors)

    if dry_run:
        print("Dry-run complete. No network requests were made.")
        # In dry-run, gate failures are reported but do not block exit (they're preflight warnings).
        return 0

    # Live path — blocked by any gate failure
    if errors:
        print(f"Live execution BLOCKED: {len(errors)} gate(s) failed.")
        return 1

    # -----------------------------------------------------------------------
    # Live execution (requires explicit --execute-live flag + all gates passed)
    # -----------------------------------------------------------------------
    from sahi.infra.cache import ContentAddressedCache
    from sahi.audio.providers.sarvam_bulbul import SarvamBulbulProvider
    from sahi.agent.saaras import SaarasSTTAdapter
    from sahi.audio.models import TTSRequest

    cache = ContentAddressedCache()
    tts   = SarvamBulbulProvider(cache=cache)
    stt   = SaarasSTTAdapter(cache=cache)

    total_requests = 0
    total_cost_inr = 0.0

    for idx, rec in enumerate(records, 1):
        uid   = rec["id"]
        text  = rec["utterance_native"]
        lang  = rec["language_code"]
        spkr  = rec["proposed_speaker"]

        print(f"\n--- {uid} ({idx}/{len(records)}) ---")

        # Safety guards before each request
        if total_requests >= EXPECTED_TOTAL_REQUESTS:
            print("Hard request limit reached. Aborting.")
            break
        # Reserve budget for next TTS call
        estimated_tts_cost = tts.estimate_cost_inr(len(text))
        if total_cost_inr + estimated_tts_cost > args.budget_inr:
            print(f"Budget would be exceeded by TTS (Rs.{estimated_tts_cost:.4f}); aborting.")
            break
        # TTS
        tts_req  = TTSRequest(text=text, target_language_code=lang, speaker=spkr)
        tts_resp = tts.synthesize(tts_req, use_cache=True)
        total_requests += 1
        total_cost_inr += estimated_tts_cost
        wav_original = tts_resp.audio_bytes
        print(f"  TTS: {len(wav_original)} bytes, cached={tts_resp.cached}, cost=Rs.{estimated_tts_cost:.4f}")

        # STT (transcribe & codemix) – reserve cost per mode
        for mode in STT_MODES:
            estimated_stt_cost = (AVG_AUDIO_DURATION_SEC / 60.0) * STT_COST_PER_MIN
            if total_cost_inr + estimated_stt_cost > args.budget_inr:
                print(f"Budget would be exceeded by STT ({mode}) (Rs.{estimated_stt_cost:.4f}); aborting.")
                break
            stt_resp = stt.transcribe(wav_original, mode=mode, language_code=lang, use_cache=True)
            total_requests += 1
            total_cost_inr += estimated_stt_cost
            print(f"  STT [{mode}]: '{stt_resp.transcript[:60]}', cached={stt_resp.cached}")
        else:
            # Continue outer loop only if inner STT loop completed without break
            continue
        # If we broke out of STT inner loop due to budget, abort outer loop
        break

    print(f"\n=== Live Run Summary ===")
    print(f"Total external requests : {total_requests}")
    print(f"Total cost              : Rs.{total_cost_inr:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
