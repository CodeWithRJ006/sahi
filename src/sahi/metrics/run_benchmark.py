"""CLI and runner for executing SAHI experimental benchmark evaluations."""

import os
import json
import logging
from typing import Dict, Any

from sahi.dataset.pilot import PILOT_DATASET
from sahi.audio.pipeline import AudioDatasetPipeline
from sahi.metrics.evaluator import EvaluationHarness
from sahi.metrics.reporter import EvaluationReporter

logger = logging.getLogger(__name__)

def run_pilot_evaluation(
    output_dir: str = "report",
    bootstrap_iterations: int = 1000,
    is_live: bool = False
) -> Dict[str, Any]:
    """
    Executes the 72-clip pilot benchmark evaluation and writes reports.
    If no live audio is provided, runs under synthetic offline simulation mode.
    """
    pipeline = AudioDatasetPipeline()
    manifest = pipeline.generate_manifest(save_audio_files=False)
    utterances_map = {u.id: u for u in PILOT_DATASET}

    harness = EvaluationHarness()
    reporter = EvaluationReporter(output_dir=output_dir)

    comparison = harness.evaluate_benchmark(
        clip_records=manifest,
        utterances_map=utterances_map,
        audio_fixtures_map=None,  # Missing audio handled honestly
        bootstrap_iterations=bootstrap_iterations
    )

    # Gather individual trials for report plotting
    b_trials = []
    g_trials = []
    for clip in manifest:
        utt = utterances_map[clip.utterance_id]
        tb, tg = harness.run_clip_trial(clip, utt, audio_bytes=None)
        b_trials.append(tb)
        g_trials.append(tg)

    paths = reporter.generate_all(
        comparison=comparison,
        trials_baseline=b_trials,
        trials_guarded=g_trials,
        is_live_measurement=is_live
    )

    return {
        "status": "COMPLETED",
        "is_live_measurement": is_live,
        "clip_count": len(manifest),
        "report_paths": paths,
        "summary": comparison.model_dump()
    }

if __name__ == "__main__":
    result = run_pilot_evaluation()
    print("Benchmark run finished:")
    print("Results JSON:", result["report_paths"]["results_json"])
    print("Report HTML:", result["report_paths"]["index_html"])
