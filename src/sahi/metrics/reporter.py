"""Report generator producing results.json, HTML reports, and evaluation plots."""

import os
import json
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
from typing import Dict, Any, List

from sahi.metrics.models import PairedComparisonResult, TrialResult

class EvaluationReporter:
    """Generates machine-readable and visual reports for SAHI evaluation runs."""

    def __init__(self, output_dir: str = "report"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_all(
        self,
        comparison: PairedComparisonResult,
        trials_baseline: List[TrialResult],
        trials_guarded: List[TrialResult],
        is_live_measurement: bool = False
    ) -> Dict[str, str]:
        """Generates results.json, evaluation_run.json, index.html, and 3 plots."""
        paths = {}

        # 1. results.json
        results_data = {
            "status": "MEASURED" if is_live_measurement else "SYNTHETIC_SIMULATION",
            "baseline": comparison.baseline.model_dump(),
            "guarded": comparison.guarded.model_dump(),
            "comparison": {
                "unsafe_rate_delta": comparison.unsafe_rate_delta,
                "unsafe_rate_delta_ci_95": comparison.unsafe_rate_delta_ci_95,
                "rupees_at_risk_delta": comparison.rupees_at_risk_delta,
                "rupees_at_risk_delta_ci_95": comparison.rupees_at_risk_delta_ci_95,
                "baseline_only_errors": comparison.baseline_only_errors,
                "guard_only_errors": comparison.guard_only_errors,
                "shared_errors": comparison.shared_errors
            },
            "metadata": comparison.experiment_metadata
        }
        results_path = os.path.join(self.output_dir, "results.json")
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results_data, f, indent=2)
        paths["results_json"] = results_path

        # Also write to root results.json as requested
        with open("results.json", "w", encoding="utf-8") as f:
            json.dump(results_data, f, indent=2)
        paths["root_results_json"] = "results.json"

        # 2. evaluation_run.json
        run_data = {
            "run_id": comparison.experiment_metadata.get("run_id", "EVAL_RUN_001"),
            "measurement_status": "MEASURED" if is_live_measurement else "NOT_MEASURED_OFFLINE_SIMULATION",
            "trial_count": len(trials_baseline),
            "baseline_trials": [t.model_dump() for t in trials_baseline],
            "guarded_trials": [t.model_dump() for t in trials_guarded]
        }
        run_path = os.path.join(self.output_dir, "evaluation_run.json")
        with open(run_path, "w", encoding="utf-8") as f:
            json.dump(run_data, f, indent=2)
        paths["evaluation_run_json"] = run_path

        # 3. Plot 1: baseline_vs_guard.png
        p1_path = os.path.join(self.output_dir, "baseline_vs_guard.png")
        self._plot_baseline_vs_guard(comparison, p1_path)
        paths["baseline_vs_guard_png"] = p1_path

        # 4. Plot 2: error_by_condition.png
        p2_path = os.path.join(self.output_dir, "error_by_condition.png")
        self._plot_error_by_condition(trials_baseline, trials_guarded, p2_path)
        paths["error_by_condition_png"] = p2_path

        # 5. Plot 3: failure_taxonomy.png
        p3_path = os.path.join(self.output_dir, "failure_taxonomy.png")
        self._plot_failure_taxonomy(trials_guarded, p3_path)
        paths["failure_taxonomy_png"] = p3_path

        # 6. report/index.html
        html_path = os.path.join(self.output_dir, "index.html")
        self._generate_html(comparison, html_path, is_live_measurement)
        paths["index_html"] = html_path

        return paths

    def _plot_baseline_vs_guard(self, comp: PairedComparisonResult, out_path: str):
        metrics = ["Wrong-Amount Rate", "Unsafe Rate", "Silent-Wrong Rate", "False-Hold Rate"]
        b_vals = [
            comp.baseline.wrong_amount_execution_rate,
            comp.baseline.unsafe_execution_rate,
            comp.baseline.silent_wrong_rate,
            comp.baseline.false_hold_rate
        ]
        g_vals = [
            comp.guarded.wrong_amount_execution_rate,
            comp.guarded.unsafe_execution_rate,
            comp.guarded.silent_wrong_rate,
            comp.guarded.false_hold_rate
        ]

        x = range(len(metrics))
        width = 0.35

        fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
        ax.bar([i - width/2 for i in x], b_vals, width, label="Baseline (Unguarded)", color="#d9534f")
        ax.bar([i + width/2 for i in x], g_vals, width, label="Guarded (SahiGuard)", color="#5cb85c")

        ax.set_ylabel("Rate (0.0 to 1.0)")
        ax.set_title("SAHI Benchmark: Baseline vs. SahiGuard Safety Rates")
        ax.set_xticks(x)
        ax.set_xticklabels(metrics)
        ax.set_ylim(0, 1.0)
        ax.legend()
        ax.grid(axis="y", linestyle="--", alpha=0.7)

        plt.tight_layout()
        plt.savefig(out_path)
        plt.close(fig)

    def _plot_error_by_condition(self, b_trials: List[TrialResult], g_trials: List[TrialResult], out_path: str):
        conditions = ["CLEAN", "TELEPHONY", "TELEPHONY_NOISE"]
        b_rates = []
        g_rates = []

        for c in conditions:
            sub_b = [t for t in b_trials if t.condition == c]
            sub_g = [t for t in g_trials if t.condition == c]
            b_rates.append(sum(1 for t in sub_b if t.is_unsafe) / len(sub_b) if sub_b else 0.0)
            g_rates.append(sum(1 for t in sub_g if t.is_unsafe) / len(sub_g) if sub_g else 0.0)

        x = range(len(conditions))
        width = 0.35

        fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
        ax.bar([i - width/2 for i in x], b_rates, width, label="Baseline Unsafe Rate", color="#e67e22")
        ax.bar([i + width/2 for i in x], g_rates, width, label="Guarded Unsafe Rate", color="#27ae60")

        ax.set_ylabel("Unsafe Execution Rate")
        ax.set_title("Error Rate by Acoustic Condition")
        ax.set_xticks(x)
        ax.set_xticklabels(["Clean", "Telephony (8kHz)", "Noisy (10dB SNR)"])
        ax.set_ylim(0, 1.0)
        ax.legend()
        ax.grid(axis="y", linestyle="--", alpha=0.7)

        plt.tight_layout()
        plt.savefig(out_path)
        plt.close(fig)

    def _plot_failure_taxonomy(self, g_trials: List[TrialResult], out_path: str):
        tax_counts: Dict[str, int] = {}
        for t in g_trials:
            if t.guard_reason:
                key = str(t.guard_reason.value)
                tax_counts[key] = tax_counts.get(key, 0) + 1

        if not tax_counts:
            tax_counts["AGREEMENT_VERIFIED"] = len(g_trials)

        labels = list(tax_counts.keys())
        counts = list(tax_counts.values())

        fig, ax = plt.subplots(figsize=(9, 4.5), dpi=150)
        y_pos = range(len(labels))
        ax.barh(y_pos, counts, color="#2980b9")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels)
        ax.set_xlabel("Count of Interventions")
        ax.set_title("SahiGuard Failure Interceptions by Reason Code")
        ax.grid(axis="x", linestyle="--", alpha=0.7)

        plt.tight_layout()
        plt.savefig(out_path)
        plt.close(fig)

    def _generate_html(self, comp: PairedComparisonResult, out_path: str, is_live: bool):
        status_label = "MEASURED LIVE EXPERIMENT" if is_live else "NOT MEASURED — OFFLINE SIMULATION SUITE"
        status_color = "#27ae60" if is_live else "#e67e22"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SAHI Evaluation Report: Indic Voice Safety Benchmark</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; margin: 0; padding: 24px; background: #f8f9fa; color: #212529; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 32px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1, h2 {{ color: #1a1a1a; }}
        .badge {{ display: inline-block; padding: 6px 12px; border-radius: 4px; font-weight: bold; font-size: 14px; color: white; background: {status_color}; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #dee2e6; }}
        th {{ background: #e9ecef; }}
        .metric-card {{ display: inline-block; width: 30%; background: #f1f3f5; padding: 16px; border-radius: 6px; margin: 8px 1%; box-sizing: border-box; }}
        .metric-val {{ font-size: 24px; font-weight: bold; margin-top: 8px; }}
        .img-container {{ margin: 24px 0; text-align: center; }}
        .img-container img {{ max-width: 100%; border: 1px solid #ced4da; border-radius: 6px; }}
    </style>
</head>
<body>
<div class="container">
    <h1>SAHI: Indic Voice Agent Amount Safety Benchmark</h1>
    <div class="badge">{status_label}</div>
    <p>Reproducible evaluation comparing an unguarded Indic baseline agent (Saaras v4 + Sarvam 105B) against the deterministic <code>SahiGuard</code> architecture.</p>

    <h2>Primary Safety Metrics</h2>
    <div class="metric-card">
        <div>Unsafe Execution Reduction</div>
        <div class="metric-val" style="color: #27ae60;">Δ {comp.unsafe_rate_delta * 100:.1f}%</div>
        <small>95% CI: [{comp.unsafe_rate_delta_ci_95[0]*100:.1f}%, {comp.unsafe_rate_delta_ci_95[1]*100:.1f}%]</small>
    </div>
    <div class="metric-card">
        <div>Rupees at Risk Reduction</div>
        <div class="metric-val" style="color: #27ae60;">₹{comp.rupees_at_risk_delta:,.0f}</div>
        <small>per 1,000 trials (95% CI: [₹{comp.rupees_at_risk_delta_ci_95[0]:,.0f}, ₹{comp.rupees_at_risk_delta_ci_95[1]:,.0f}])</small>
    </div>
    <div class="metric-card">
        <div>SahiGuard False-Hold Rate</div>
        <div class="metric-val">{comp.guarded.false_hold_rate * 100:.1f}%</div>
        <small>Held for readback or clarification</small>
    </div>

    <h2>Comparison Summary</h2>
    <table>
        <thead>
            <tr>
                <th>Metric</th>
                <th>Baseline (Unguarded)</th>
                <th>Guarded (SahiGuard)</th>
                <th>Delta / Impact</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Wrong-Amount Execution Rate</strong></td>
                <td>{comp.baseline.wrong_amount_execution_rate * 100:.1f}%</td>
                <td>{comp.guarded.wrong_amount_execution_rate * 100:.1f}%</td>
                <td>-{(comp.baseline.wrong_amount_execution_rate - comp.guarded.wrong_amount_execution_rate) * 100:.1f}%</td>
            </tr>
            <tr>
                <td><strong>Unsafe Execution Rate</strong></td>
                <td>{comp.baseline.unsafe_execution_rate * 100:.1f}%</td>
                <td>{comp.guarded.unsafe_execution_rate * 100:.1f}%</td>
                <td><strong>-{(comp.unsafe_rate_delta) * 100:.1f}%</strong></td>
            </tr>
            <tr>
                <td><strong>Silent-Wrong Rate</strong></td>
                <td>{comp.baseline.silent_wrong_rate * 100:.1f}%</td>
                <td>{comp.guarded.silent_wrong_rate * 100:.1f}%</td>
                <td>-{(comp.baseline.silent_wrong_rate - comp.guarded.silent_wrong_rate) * 100:.1f}%</td>
            </tr>
            <tr>
                <td><strong>False-Hold Rate</strong></td>
                <td>{comp.baseline.false_hold_rate * 100:.1f}%</td>
                <td>{comp.guarded.false_hold_rate * 100:.1f}%</td>
                <td>+{comp.guarded.false_hold_rate * 100:.1f}%</td>
            </tr>
            <tr>
                <td><strong>Rupees at Risk (per 1k trials)</strong></td>
                <td>₹{comp.baseline.rupees_at_risk_per_1000:,.0f}</td>
                <td>₹{comp.guarded.rupees_at_risk_per_1000:,.0f}</td>
                <td><strong>-₹{comp.rupees_at_risk_delta:,.0f}</strong></td>
            </tr>
            <tr>
                <td><strong>p50 / p95 Latency</strong></td>
                <td>{comp.baseline.p50_latency_ms:.0f}ms / {comp.baseline.p95_latency_ms:.0f}ms</td>
                <td>{comp.guarded.p50_latency_ms:.0f}ms / {comp.guarded.p95_latency_ms:.0f}ms</td>
                <td>+{comp.guarded.p50_latency_ms - comp.baseline.p50_latency_ms:.0f}ms overhead</td>
            </tr>
        </tbody>
    </table>

    <h2>Visual Evaluations</h2>
    <div class="img-container">
        <h3>Baseline vs. Guarded Rates</h3>
        <img src="baseline_vs_guard.png" alt="Baseline vs Guarded">
    </div>
    <div class="img-container">
        <h3>Degradation Impact by Condition</h3>
        <img src="error_by_condition.png" alt="Error by Condition">
    </div>
    <div class="img-container">
        <h3>SahiGuard Interception Taxonomy</h3>
        <img src="failure_taxonomy.png" alt="Failure Taxonomy">
    </div>
</div>
</body>
</html>
"""
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_content)
