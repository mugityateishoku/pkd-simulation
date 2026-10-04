"""Post hoc observer study of council composition and effective input influence.

The September simulator is frozen. This module observes PKD decisions without
changing their return values, consuming random draws, or mutating their inputs.
Influence coefficients are conditional on the realized confidence graph; they
are linear decomposition weights, not causal derivatives or political power.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy import stats

import simulation_pkd_v32 as model


METRICS = (
    "loss", "represented_population_share", "representation_js_divergence",
    "representation_total_variation", "demagogue_fraction",
    "final_record_weight", "final_lottery_weight", "effective_record_weight",
    "effective_lottery_weight", "effective_input_count",
    "lottery_seat_share",
)


def effective_coefficients(predictions, tolerances, scores, revision_rate,
                           deliberate=True, score_weighting=True):
    """Return final aggregation weights, raw-input coefficients, and B matrix.

    For the realized confidence neighborhoods, z = B x and p = w.T z.
    Consequently a = B.T w and p = a.T x. Changing x can change the graph:
    a is not the derivative of the full nonlinear decision rule.
    """
    predictions = np.asarray(predictions, dtype=float)
    scores = np.asarray(scores, dtype=float)
    n = len(predictions)
    final_weights = model.stable_softmax(scores) if score_weighting else np.full(n, 1.0 / n)
    matrix = np.eye(n)
    if deliberate:
        for i in range(n):
            neighbors = np.linalg.norm(predictions - predictions[i], axis=1) <= tolerances[i]
            neighbors[i] = True
            matrix[i] *= 1.0 - revision_rate
            matrix[i, neighbors] += revision_rate * model.stable_softmax(scores[neighbors])
    return final_weights, matrix.T @ final_weights, matrix


@contextmanager
def observe_pkd_decisions():
    """Temporarily observe each PKD decision in this process; always restore it."""
    original = model.PhilosopherKingDemocracy.decide
    observations = []

    def observed(system, raw_predictions, agents, track_records):
        returned = original(system, raw_predictions, agents, track_records)
        ids = np.asarray(system.council)
        selected = raw_predictions[ids]
        w, coefficients, matrix = effective_coefficients(
            selected, np.array([agents[i].tolerance for i in ids]),
            track_records[ids], system.revision_rate,
            deliberate=system.deliberate, score_weighting=system.score_weighting,
        )
        gap = float(np.max(np.abs(coefficients @ selected - returned[0])))
        if not (np.isfinite(coefficients).all() and np.min(coefficients) >= -1e-14
                and abs(coefficients.sum() - 1.0) < 1e-12 and gap < 1e-12):
            raise AssertionError("observer failed convex-decomposition invariant")
        record_set = set(int(i) for i in system.expert_seats)
        record_mask = np.array([int(i) in record_set for i in ids])
        observations.append({
            "period": len(observations),
            "record_seat_ids": json.dumps([int(i) for i in system.expert_seats]),
            "lottery_seat_ids": json.dumps([int(i) for i in system.citizen_seats]),
            "council_ids": json.dumps(ids.tolist()),
            "final_weights": json.dumps(w.tolist()),
            "effective_input_coefficients": json.dumps(coefficients.tolist()),
            "final_record_weight": float(w[record_mask].sum()),
            "final_lottery_weight": float(w[~record_mask].sum()),
            "effective_record_weight": float(coefficients[record_mask].sum()),
            "effective_lottery_weight": float(coefficients[~record_mask].sum()),
            "effective_input_count": float(1.0 / np.sum(coefficients ** 2)),
            "lottery_seat_share": float((~record_mask).mean()),
            "policy_reconstruction_max_gap": gap,
        })
        return returned

    model.PhilosopherKingDemocracy.decide = observed
    try:
        yield observations
    finally:
        model.PhilosopherKingDemocracy.decide = original


def declared_conditions(baseline):
    conditions = {"baseline_observed": dict(baseline)}
    for k in [0, 2, 5, 8, 10]:
        for weighted in [False, True]:
            name = f"record_{k:02d}_{'score' if weighted else 'equal'}"
            conditions[name] = {**baseline, "n_expert_seats": k,
                                "n_citizen_seats": 10-k, "pkd_deliberation": False,
                                "pkd_score_weighting": weighted}
    return conditions


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_archived_baseline(source):
    with gzip.open(Path(source) / "raw/baseline/period_metrics.csv.gz", "rt", encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["system"] == model.SYSTEM_PKD]
    return {(int(row["seed"]), int(row["period"])): float(row["performance"]) for row in rows}


def run_condition(job):
    label, config_dict, seeds, destination, source = job
    config = model.ModelConfig.from_mapping(config_dict)
    folder = Path(destination) / "raw" / label
    folder.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    summary = []
    window_summary = []
    parity = read_archived_baseline(source) if label == "baseline_observed" else None
    parity_max = 0.0
    reconstruction_max = 0.0
    with gzip.open(folder / "period_influence.csv.gz", "wt", encoding="utf-8", newline="") as handle:
        writer = None
        for run, seed in enumerate(seeds):
            with observe_pkd_decisions() as observed:
                result = model.run_simulation(config, seed=seed, run=run)
            periods = result.system_periods(model.SYSTEM_PKD)
            assert len(observed) == len(periods) == config.n_periods
            assembled = []
            for record, weights in zip(periods, observed):
                assert record.period == weights["period"]
                row = {"run": run, "seed": seed, **asdict(record), "loss": -record.performance, **weights}
                if parity is not None:
                    parity_max = max(parity_max, abs(record.performance - parity[(seed, record.period)]))
                reconstruction_max = max(reconstruction_max, weights["policy_reconstruction_max_gap"])
                if writer is None:
                    writer = csv.DictWriter(handle, fieldnames=list(row)); writer.writeheader()
                writer.writerow(row)
                assembled.append(row)
            summary.append({"run": run, "seed": seed, "condition": label,
                            **{metric: float(np.mean([row[metric] for row in assembled])) for metric in METRICS}})
            for window, start_period in [("all_periods", 0), ("periods_30_onward", 30)]:
                subset = [row for row in assembled if row["period"] >= start_period]
                if not subset:
                    continue
                seated, lottery_seated = set(), set()
                for row in subset:
                    seated.update(json.loads(row["council_ids"]))
                    lottery_seated.update(json.loads(row["lottery_seat_ids"]))
                values = {metric: float(np.mean([row[metric] for row in subset])) for metric in METRICS}
                values["ever_seated_population_fraction"] = len(seated) / config.population_size
                values["ever_lottery_seated_population_fraction"] = len(lottery_seated) / config.population_size
                values["lottery_weight_relative_to_seat_share"] = (
                    values["effective_lottery_weight"] / values["lottery_seat_share"]
                    if values["lottery_seat_share"] else ""
                )
                window_summary.append({"run": run, "seed": seed, "condition": label,
                                       "window": window, "first_period": start_period,
                                       "last_period": config.n_periods-1, **values})
    if parity is not None and parity_max >= 1e-12:
        raise AssertionError(f"baseline observer parity failed: {parity_max}")
    model.write_csv(folder / "run_summary.csv", summary)
    model.write_csv(folder / "run_window_summary.csv", window_summary)
    details = {"condition": label, "n_runs": len(seeds), "n_periods": config.n_periods,
               "period_rows": len(seeds) * config.n_periods,
               "baseline_max_error_gap": parity_max if parity is not None else None,
               "policy_reconstruction_max_gap": reconstruction_max,
               "elapsed_seconds": time.perf_counter() - start}
    (folder / "verification.json").write_text(json.dumps(details, indent=2), encoding="utf-8")
    return details


def estimate(values):
    values = np.asarray(values, dtype=float)
    n = len(values)
    mean = float(values.mean())
    se = float(values.std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0
    half = float(stats.t.ppf(0.975, n-1)) * se if n > 1 else 0.0
    return {"mean": mean, "low": mean-half, "high": mean+half, "mcse": se, "n": n}


def analyze(destination):
    root = Path(destination)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    rows_by_condition = {}
    estimates = []
    window_estimates = []
    window_rows = {}
    for name in manifest["conditions"]:
        with (root / "raw" / name / "run_summary.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        keyed = {int(row["seed"]): row for row in rows}
        if len(rows) != len(keyed) or set(keyed) != set(manifest["seeds"]):
            raise AssertionError(f"run/seed mismatch in {name}")
        rows_by_condition[name] = [keyed[seed] for seed in manifest["seeds"]]
        for metric in METRICS:
            estimates.append({"condition": name, "metric": metric,
                              **estimate([float(row[metric]) for row in rows_by_condition[name]])})
        with (root / "raw" / name / "run_window_summary.csv").open(newline="", encoding="utf-8") as handle:
            windows = list(csv.DictReader(handle))
        for window in sorted({row["window"] for row in windows}):
            selected = [row for row in windows if row["window"] == window]
            indexed = {int(row["seed"]): row for row in selected}
            if len(selected) != len(indexed) or set(indexed) != set(manifest["seeds"]):
                raise AssertionError(f"window seed mismatch in {name}/{window}")
            window_rows[(name, window)] = [indexed[seed] for seed in manifest["seeds"]]
            for metric in (*METRICS, "ever_seated_population_fraction", "ever_lottery_seated_population_fraction",
                           "lottery_weight_relative_to_seat_share"):
                if any(row[metric] == "" for row in selected):
                    continue  # no lottery seats: weight/seat-share ratio is undefined
                window_estimates.append({"condition": name, "window": window, "metric": metric,
                                         **estimate([float(row[metric]) for row in selected])})
    pairs = [(name, "baseline_observed") for name in rows_by_condition if name != "baseline_observed"]
    pairs += [(f"record_{k:02d}_score", f"record_{k:02d}_equal") for k in [0, 2, 5, 8, 10]]
    pairs += [(f"record_{k:02d}_{mode}", f"record_10_{mode}")
              for mode in ["score", "equal"] for k in [0, 2, 5, 8]]
    contrasts = []
    for first, second in pairs:
        for metric in METRICS:
            differences = [float(a[metric])-float(b[metric]) for a, b in
                           zip(rows_by_condition[first], rows_by_condition[second])]
            contrasts.append({"first": first, "second": second, "metric": metric,
                              **estimate(differences)})
    analysis_dir = root / "analysis"; analysis_dir.mkdir(exist_ok=True)
    model.write_csv(analysis_dir / "estimates.csv", estimates)
    model.write_csv(analysis_dir / "paired_contrasts.csv", contrasts)
    window_contrasts = []
    for first, second in [("record_05_score", "record_05_equal"),
                          ("baseline_observed", "record_05_score"),
                          ("record_05_score", "record_10_score")]:
        for window in ["all_periods", "periods_30_onward"]:
            if (first, window) not in window_rows:
                continue
            for metric in (*METRICS, "ever_seated_population_fraction", "ever_lottery_seated_population_fraction"):
                diff = [float(a[metric])-float(b[metric]) for a,b in
                        zip(window_rows[(first,window)], window_rows[(second,window)])]
                window_contrasts.append({"first": first, "second": second, "window": window,
                                         "metric": metric, **estimate(diff)})
    model.write_csv(analysis_dir / "window_estimates.csv", window_estimates)
    model.write_csv(analysis_dir / "window_paired_contrasts.csv", window_contrasts)
    report = {"status": manifest["status"], "definition": manifest["influence_definition"],
              "estimates": estimates, "paired_contrasts": contrasts,
              "window_estimates": window_estimates, "window_paired_contrasts": window_contrasts}
    (analysis_dir / "results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    lookup = {(row["condition"], row["metric"]): row for row in estimates}
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for mode, color, label in [("equal", "#975524", "Equal final weights"),
                               ("score", "#176575", "Record final weights")]:
        for ax, metric in zip(axes, ["loss", "represented_population_share", "effective_lottery_weight"]):
            values = [lookup[(f"record_{k:02d}_{mode}", metric)] for k in [0, 2, 5, 8, 10]]
            ax.errorbar([0, 2, 5, 8, 10], [v["mean"] for v in values],
                        yerr=[(v["high"]-v["low"])/2 for v in values],
                        marker="o", color=color, capsize=3, label=label)
            base = lookup[("baseline_observed", metric)]
            if mode == "score":
                ax.errorbar([5], [base["mean"]], yerr=[(base["high"]-base["low"])/2],
                            marker="*", markersize=11, color="black", capsize=3,
                            linestyle="none", label="Original baseline, deliberation on")
            ax.set_xlabel("Record-selected seats (10 total)")
            ax.set_xticks([0, 2, 5, 8, 10]); ax.grid(alpha=.15)
    axes[0].set_ylabel("Mean squared Euclidean error"); axes[0].set_yscale("log")
    axes[1].set_ylabel("Nominal stratum coverage")
    axes[2].set_ylabel("Effective lottery input-weight share")
    axes[2].plot([0, 2, 5, 8, 10], [1, .8, .5, .2, 0], "--", color="gray", alpha=.7, label="Lottery seat share")
    handles, labels = axes[2].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False)
    fig.tight_layout(rect=(0, .16, 1, 1))
    fig.savefig(analysis_dir / "figure_followup.png", dpi=220)
    fig.savefig(analysis_dir / "figure_followup.pdf")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("results/preprint_2026"))
    parser.add_argument("--output", type=Path, default=Path("results/review_2026/followup"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--runs", type=int, default=None, help="Optional smoke subset; full study uses all archived seeds")
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    if args.analyze_only:
        analyze(args.output); return
    if (args.output / "manifest.json").exists():
        raise RuntimeError("Output already contains a declared study; use another directory or --analyze-only")
    source_manifest = json.loads((args.source / "study_manifest.json").read_text(encoding="utf-8"))
    core_path = Path(model.__file__)
    core_hash = sha256(core_path)
    if core_hash != source_manifest["simulation_sha256"]:
        raise RuntimeError("Frozen simulator differs from the archived September source hash")
    baseline = source_manifest["conditions"]["baseline"]
    seeds = source_manifest["seeds"][:args.runs] if args.runs else source_manifest["seeds"]
    conditions = declared_conditions(baseline)
    manifest = {
        "study": "PKD composition and conditional influence follow-up",
        "status": "post hoc exploratory follow-up; not preregistered; same archived seeds",
        "declared_before_execution_utc": datetime.now(timezone.utc).isoformat(),
        "original_manifest_sha256": sha256(args.source / "study_manifest.json"),
        "simulation_sha256": core_hash, "observer_sha256": sha256(__file__),
        "source_data": str(args.source), "seeds": seeds, "conditions": conditions,
        "n_runs": len(seeds), "n_periods": baseline["n_periods"], "workers": args.workers,
        "influence_definition": "Given the realized confidence graph, a=B.T@w decomposes the returned policy into registered council estimates; not a causal derivative, opinion legitimacy, or empirical political power.",
        "uncertainty": "Pointwise 95% Student-t Monte Carlo intervals across paired run seeds; no significance classification.",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    jobs = [(name, config, seeds, str(args.output), str(args.source)) for name, config in conditions.items()]
    verification = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_condition, job) for job in jobs]
        for future in as_completed(futures):
            result = future.result(); verification.append(result)
            print(f"{len(verification)}/{len(jobs)} {result['condition']} ({result['elapsed_seconds']:.1f}s)", flush=True)
    if sha256(core_path) != core_hash or sha256(__file__) != manifest["observer_sha256"]:
        raise RuntimeError("Study sources changed during execution")
    (args.output / "verification.json").write_text(json.dumps(verification, indent=2), encoding="utf-8")
    analyze(args.output)


if __name__ == "__main__":
    main()
