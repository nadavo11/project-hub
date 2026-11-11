"""Evaluate the frozen M09-v2 scores without retuning them."""

import json

import numpy as np

from .targeted_science import OUT, save


def auc(labels, scores):
    y = np.asarray(labels, dtype=bool)
    if not y.any() or y.all():
        return None
    score = np.array([np.inf if x is None else x for x in scores])
    positive, negative = score[y, None], score[~y][None, :]
    return float(np.mean((positive > negative) + .5 * (positive == negative)))


def main():
    assert auc([False, True], [0, 1]) == 1
    assert auc([False, True], [1, 0]) == 0
    assert auc([False, True], [1, 1]) == .5
    all_rows = [json.loads(line) for line in (OUT / "experiment-rows.jsonl").read_text().splitlines()]
    rows = [r for r in all_rows if r["solved"]]
    assert len(all_rows) == 120
    keys = list(rows[0]["scores"])

    def table(records):
        labels = [r["failure"] for r in records]
        return {key: auc(labels, [r["scores"][key] for r in records]) for key in keys}

    scores = table(rows)
    baselines = [k for k in keys if k != "switch_excess" and scores[k] is not None]
    best = max(baselines, key=lambda k: scores[k])
    gap = scores["switch_excess"] - scores[best]
    rng, gaps = np.random.default_rng(731), []
    for _ in range(2000):
        selected = rng.choice(8, 8, replace=True)
        sample = [r for block in selected for r in rows if r["draw"] == block]
        values = table(sample)
        if values["switch_excess"] is not None and values[best] is not None:
            gaps.append(values["switch_excess"] - values[best])
    ci = np.quantile(gaps, [.025, .975]).tolist()
    derivative = json.loads((OUT / "derivative-checks.json").read_text())
    derivative_pass = all(r["relative_derivative_difference"] <= .05 for r in derivative["checks"])
    successful = gap >= .05 and ci[0] > 0 and derivative_pass
    values = {
        "trials": len(all_rows), "solvable_trials": len(rows),
        "failures_over_1m_on_solvable_trials": sum(r["failure"] for r in rows),
        "baseline_unsolved_trials": len(all_rows) - len(rows),
        "held_out_crossdomain_baseline": "No PnP solution; remains a pipeline failure, not repaired or counted as a scored uncertainty success",
        "auc": scores, "strongest_declared_baseline": best,
        "switch_excess_minus_baseline": gap, "paired_draw_block_bootstrap_95pct": ci,
        "valid_bootstrap_replicates": len(gaps), "derivative_check_passed": derivative_pass,
        "prospective_performance_gate_passed": successful,
        "per_amplitude": {str(a): table([r for r in rows if r["amplitude"] == a]) for a in [0, .25, .5, 1, 2]},
        "per_support": {s: table([r for r in rows if r["support"] == s]) for s in ["all", "random55", "concentrated55"]},
        "probe_failure_counts": {k: sum(r["probe_failures"][k] for r in rows) for k in rows[0]["probe_failures"]},
        "maximum_zero_switch_excess_m": max(r["max_zero_switch_excess"] or 0 for r in rows),
        "mean_consensus_change": float(np.mean([r["mean_consensus_change"] for r in rows if r["mean_consensus_change"] is not None])),
        "minimum_positive_depth_fraction": min(r["positive_depth_fraction"] for r in rows),
        "scope": "Conditional on one real scene, fixed real SIFT matches and stipulated synthetic map-error distribution. Eight paired random-error blocks, not120 independent scenes. Bootstrap is not scene-generalization evidence.",
        "decision": "No promotion from this measurement alone; independent interpretation and prior-art review required.",
    }
    save("experiment-analysis.json", values)
    print(json.dumps(values, indent=2))


if __name__ == "__main__":
    main()
