"""Calculation engine for SAHI safety metrics and cluster bootstrap statistics."""

import numpy as np
from typing import List, Dict, Tuple, Optional
from sahi.metrics.models import TrialResult, ArmEvaluationSummary, PairedComparisonResult

class MetricsCalculator:
    """Computes safety metrics and cluster-bootstrapped confidence intervals."""

    @staticmethod
    def summarize_arm(arm_name: str, trials: List[TrialResult]) -> ArmEvaluationSummary:
        total = len(trials)
        if total == 0:
            return ArmEvaluationSummary(
                arm_name=arm_name,
                total_trials=0,
                total_completed_transfers=0,
                wrong_amount_execution_rate=0.0,
                unsafe_execution_rate=0.0,
                silent_wrong_rate=0.0,
                false_hold_rate=0.0,
                rupees_at_risk_per_1000=0.0,
                no_transfer_rate=0.0,
                parse_failure_rate=0.0,
                ambiguity_rate=0.0,
                read_back_rate=0.0,
                escalation_rate=0.0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                total_cost_inr=0.0
            )

        completed_transfers = [t for t in trials if t.is_completed_transfer]
        wrong_transfers = [t for t in completed_transfers if t.is_unsafe]
        silent_wrongs = [t for t in trials if t.is_silent_wrong]

        # False holds: intended amount was known, but trial held/re-asked/escalated
        actionable_trials = [t for t in trials if t.intended_amount_inr is not None and t.category != "self_correction"]
        false_holds = [t for t in actionable_trials if t.is_false_hold]

        wae_rate = len(wrong_transfers) / float(len(completed_transfers)) if completed_transfers else 0.0
        unsafe_rate = len(wrong_transfers) / float(total)
        silent_wrong_rate = len(silent_wrongs) / float(total)
        false_hold_rate = len(false_holds) / float(len(actionable_trials)) if actionable_trials else 0.0

        # Rupees at risk per 1000 trials
        total_rupees_diff = sum(t.rupees_discrepancy for t in trials)
        rar_per_1000 = (total_rupees_diff / float(total)) * 1000.0

        no_transfers = sum(1 for t in trials if not t.is_completed_transfer)
        parse_failures = sum(1 for t in trials if t.execution_status == "PARSE_FAILURE")
        ambiguities = sum(1 for t in trials if t.execution_status == "HELD_FOR_CLARIFICATION")
        read_backs = sum(1 for t in trials if t.execution_status == "HELD_FOR_READBACK")
        escalations = sum(1 for t in trials if t.execution_status == "ESCALATED")

        latencies = [t.latency_ms for t in trials]
        p50_lat = float(np.percentile(latencies, 50)) if latencies else 0.0
        p95_lat = float(np.percentile(latencies, 95)) if latencies else 0.0
        total_cost = sum(t.cost_inr for t in trials)

        return ArmEvaluationSummary(
            arm_name=arm_name,
            total_trials=total,
            total_completed_transfers=len(completed_transfers),
            wrong_amount_execution_rate=round(wae_rate, 4),
            unsafe_execution_rate=round(unsafe_rate, 4),
            silent_wrong_rate=round(silent_wrong_rate, 4),
            false_hold_rate=round(false_hold_rate, 4),
            rupees_at_risk_per_1000=round(rar_per_1000, 2),
            no_transfer_rate=round(no_transfers / float(total), 4),
            parse_failure_rate=round(parse_failures / float(total), 4),
            ambiguity_rate=round(ambiguities / float(total), 4),
            read_back_rate=round(read_backs / float(total), 4),
            escalation_rate=round(escalations / float(total), 4),
            p50_latency_ms=round(p50_lat, 2),
            p95_latency_ms=round(p95_lat, 2),
            total_cost_inr=round(total_cost, 4)
        )

    @classmethod
    def compare_arms(
        cls,
        baseline_trials: List[TrialResult],
        guarded_trials: List[TrialResult],
        bootstrap_iterations: int = 1000,
        seed: int = 42
    ) -> PairedComparisonResult:
        """
        Computes paired comparison and cluster bootstrap confidence intervals
        clustered at the utterance level.
        """
        assert len(baseline_trials) == len(guarded_trials), "Baseline and Guarded trial counts must match."

        baseline_summary = cls.summarize_arm("Baseline", baseline_trials)
        guarded_summary = cls.summarize_arm("Guarded", guarded_trials)

        # Count paired error overlaps
        b_only = 0
        g_only = 0
        shared = 0

        for tb, tg in zip(baseline_trials, guarded_trials):
            if tb.is_unsafe and not tg.is_unsafe:
                b_only += 1
            elif tg.is_unsafe and not tb.is_unsafe:
                g_only += 1
            elif tb.is_unsafe and tg.is_unsafe:
                shared += 1

        unsafe_delta = baseline_summary.unsafe_execution_rate - guarded_summary.unsafe_execution_rate
        rar_delta = baseline_summary.rupees_at_risk_per_1000 - guarded_summary.rupees_at_risk_per_1000

        # Cluster bootstrap resampling at utterance level
        utterance_ids = sorted(list({t.utterance_id for t in baseline_trials}))
        n_clusters = len(utterance_ids)

        trials_by_utt_b: Dict[str, List[TrialResult]] = {}
        trials_by_utt_g: Dict[str, List[TrialResult]] = {}
        for t in baseline_trials:
            trials_by_utt_b.setdefault(t.utterance_id, []).append(t)
        for t in guarded_trials:
            trials_by_utt_g.setdefault(t.utterance_id, []).append(t)

        rng = np.random.RandomState(seed)
        delta_unsafe_dist: List[float] = []
        delta_rar_dist: List[float] = []

        if n_clusters > 1 and bootstrap_iterations > 0:
            for _ in range(bootstrap_iterations):
                sample_utts = rng.choice(utterance_ids, size=n_clusters, replace=True)
                sample_b: List[TrialResult] = []
                sample_g: List[TrialResult] = []
                for uid in sample_utts:
                    sample_b.extend(trials_by_utt_b[uid])
                    sample_g.extend(trials_by_utt_g[uid])

                sum_b = cls.summarize_arm("BootB", sample_b)
                sum_g = cls.summarize_arm("BootG", sample_g)

                delta_unsafe_dist.append(sum_b.unsafe_execution_rate - sum_g.unsafe_execution_rate)
                delta_rar_dist.append(sum_b.rupees_at_risk_per_1000 - sum_g.rupees_at_risk_per_1000)

            ci_unsafe = (
                float(np.percentile(delta_unsafe_dist, 2.5)),
                float(np.percentile(delta_unsafe_dist, 97.5))
            )
            ci_rar = (
                float(np.percentile(delta_rar_dist, 2.5)),
                float(np.percentile(delta_rar_dist, 97.5))
            )
        else:
            ci_unsafe = (unsafe_delta, unsafe_delta)
            ci_rar = (rar_delta, rar_delta)

        return PairedComparisonResult(
            baseline=baseline_summary,
            guarded=guarded_summary,
            baseline_only_errors=b_only,
            guard_only_errors=g_only,
            shared_errors=shared,
            unsafe_rate_delta=round(unsafe_delta, 4),
            unsafe_rate_delta_ci_95=(round(ci_unsafe[0], 4), round(ci_unsafe[1], 4)),
            rupees_at_risk_delta=round(rar_delta, 2),
            rupees_at_risk_delta_ci_95=(round(ci_rar[0], 2), round(ci_rar[1], 2)),
            experiment_metadata={
                "n_clusters": n_clusters,
                "bootstrap_iterations": bootstrap_iterations,
                "random_seed": seed
            }
        )
