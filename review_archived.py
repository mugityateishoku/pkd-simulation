"""Post hoc review of archived September runs; historical outputs stay unchanged.

Every confidence interval uses independent runs (n=30), never periods as
replications. Paired contrasts join exact run and seed identifiers. The window
choices were made after the original results were inspected: they are an
interpretive sensitivity analysis, not a preregistered confirmatory test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PKD = "PKD"
WINDOWS = [(0, 300), (0, 6), (6, 30), (0, 30), (30, 300), (90, 300)]
KEYS = ["run", "seed"]


def estimate(values):
    x = np.asarray(values, dtype=float)
    assert len(x) == 30 and np.isfinite(x).all()
    mean = float(x.mean())
    mcse = float(x.std(ddof=1) / np.sqrt(len(x)))
    half = float(t.ppf(.975, len(x)-1) * mcse)
    return {"mean": mean, "low": mean-half, "high": mean+half,
            "mcse": mcse, "n_runs": len(x)}


def paired(left, right):
    assert left.index.is_unique and right.index.is_unique
    assert set(left.index) == set(right.index)
    joined = pd.concat([left.rename("left"), right.rename("right")], axis=1).sort_index()
    assert not joined.isna().any().any()
    return estimate(joined.left - joined.right)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/preprint_2026"))
    parser.add_argument("--output", type=Path, default=Path("results/review_2026/archived_analysis"))
    args = parser.parse_args()
    root, out = args.input, args.output
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((root/"study_manifest.json").read_text(encoding="utf-8"))
    assert manifest["n_runs"] == 30 and manifest["n_periods"] == 300
    expected = pd.MultiIndex.from_tuples(list(enumerate(manifest["seeds"])), names=KEYS)
    summaries = {}
    groups = {}
    for label, config in manifest["conditions"].items():
        canonical = json.dumps(config, sort_keys=True, separators=(",", ":"))
        groups.setdefault(canonical, []).append(label)
        summary = pd.read_csv(root/"raw"/label/"run_summary.csv")
        for system, frame in summary.groupby("system"):
            index = pd.MultiIndex.from_frame(frame[KEYS])
            assert index.is_unique and set(index) == set(expected), (label, system)
        summaries[label] = summary
    mapping = []
    for number, (canonical, labels) in enumerate(groups.items(), 1):
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        for label in labels:
            mapping.append({"label": label, "distinct_setting_id": number,
                            "config_sha256": digest, "representative_label": labels[0],
                            "labels_for_setting": len(labels)})
    pd.DataFrame(mapping).to_csv(out/"condition_identity.csv", index=False)
    duplicate_checks = []
    for labels in groups.values():
        for label in labels[1:]:
            a, b = labels[0], label
            # Compare decompressed content: gzip timestamps are irrelevant.
            af = pd.read_csv(root/"raw"/a/"period_metrics.csv.gz")
            bf = pd.read_csv(root/"raw"/b/"period_metrics.csv.gz")
            pd.testing.assert_frame_equal(af, bf, check_exact=True)
            pd.testing.assert_frame_equal(summaries[a], summaries[b], check_exact=True)
            duplicate_checks.append({"first": a, "duplicate": b,
                                     "period_tables_exactly_identical": True,
                                     "summary_tables_exactly_identical": True,
                                     "period_rows_per_label": len(af)})

    labels = ["baseline", "feedback_delay_3", "feedback_delay_12", "feedback_delay_24",
              "no_deliberation", "record_only_10", "record_only_5", "lottery_only_10",
              "uniform_lottery", "equal_weights", "frozen_after_100"]
    # Keep only PKD after checking every run/period is present exactly once.
    period_frames = {}
    for label in labels:
        all_periods = pd.read_csv(root/"raw"/label/"period_metrics.csv.gz")
        frame = all_periods[all_periods.system == PKD].copy()
        assert len(frame) == 30*300
        assert not frame.duplicated(KEYS+["period"]).any()
        assert set(pd.MultiIndex.from_frame(frame[KEYS].drop_duplicates())) == set(expected)
        for _, run in frame.groupby(KEYS):
            assert set(run.period) == set(range(300))
        frame["loss"] = -frame.performance
        period_frames[label] = frame

    def run_means(label, start, stop, metric="loss"):
        frame = period_frames[label]
        selected = frame[(frame.period >= start) & (frame.period < stop)]
        return selected.groupby(KEYS)[metric].mean().sort_index()

    window_rows, window_run_rows = [], []
    for label in labels:
        for start, stop in WINDOWS:
            values = run_means(label, start, stop)
            base = run_means("baseline", start, stop)
            row = {"condition": label, "system": PKD, "start_inclusive": start,
                   "stop_exclusive": stop, "periods_per_run": stop-start,
                   **estimate(values),
                   **{"paired_vs_baseline_"+k: v for k, v in paired(values, base).items()}}
            window_rows.append(row)
            for (run, seed), value in values.items():
                window_run_rows.append({"condition": label, "run": int(run), "seed": int(seed),
                                        "start_inclusive": start, "stop_exclusive": stop,
                                        "mean_loss": value})
    pd.DataFrame(window_rows).to_csv(out/"initialization_window_estimates.csv", index=False)
    pd.DataFrame(window_run_rows).to_csv(out/"initialization_window_run_means.csv", index=False)
    delay_rows = [r for r in window_rows if r["condition"] in labels[:4]
                  and (r["start_inclusive"],r["stop_exclusive"]) in [(0,30),(30,300),(90,300)]]
    pd.DataFrame(delay_rows).to_csv(out/"delay_window_estimates.csv", index=False)

    composition = []
    for start, stop in [(0,300),(30,300),(90,300)]:
        for metric in ["loss", "represented_population_share", "representation_js_divergence"]:
            hybrid = run_means("no_deliberation", start, stop, metric)
            record = run_means("record_only_10", start, stop, metric)
            composition.append({"contrast": "5 record + 5 stratified lottery minus 10 record seats; both without deliberation",
                                "metric": metric, "start_inclusive": start, "stop_exclusive": stop,
                                "hybrid_mean": float(hybrid.mean()), "record_only_mean": float(record.mean()),
                                "relative_change_of_means_percent": float((hybrid.mean()/record.mean()-1)*100),
                                **paired(hybrid, record)})
    pd.DataFrame(composition).to_csv(out/"matched_composition_contrasts.csv", index=False)

    dimension_rows = []
    for label in ["n_dim_2", "baseline", "n_dim_20"]:
        dimension = manifest["conditions"][label]["n_dim"]
        for system, frame in summaries[label].groupby("system"):
            dimension_rows.append({"condition": label, "system": system, "n_dim": dimension,
                                   "metric": "mean squared error per coordinate",
                                   **estimate(-frame.mean_performance/dimension)})
    pd.DataFrame(dimension_rows).to_csv(out/"dimension_per_coordinate_estimates.csv", index=False)

    caption = ("Post hoc decomposition of the feedback-delay comparison. Each point is the mean "
               "of 30 run-specific mean squared Euclidean errors; bars are two-sided 95% Student-t "
               "Monte Carlo intervals across runs. The panels share an error scale. The first 30 "
               "periods cover the largest 24-period delay plus the six-period selection cycle; "
               "the window was chosen after inspecting the original results. The later window "
               "contains periods 30–299. Results using periods 90–299 are also tabulated. "
               "Intervals measure simulation uncertainty conditional on this model, not uncertainty "
               "about real societies; periods are not independent replications. All delays use "
               "identical run seeds, and paired differences are supplied separately.")
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.3), sharey=True)
    for ax, (start, stop), title in zip(axes, [(0,30),(30,300)], ["A  Initial periods 0–29", "B  Later periods 30–299"]):
        rows = [next(r for r in delay_rows if r["condition"] == label and r["start_inclusive"] == start
                     and r["stop_exclusive"] == stop) for label in labels[:4]]
        means = np.array([r["mean"] for r in rows])
        ax.errorbar([0,3,12,24], means,
                    yerr=[means-np.array([r["low"] for r in rows]), np.array([r["high"] for r in rows])-means],
                    fmt="o-", capsize=3, color="#176575")
        ax.set_xticks([0,3,12,24]); ax.set_xlabel("Feedback delay (periods)")
        ax.set_title(title); ax.grid(axis="y", alpha=.2)
    axes[0].set_ylabel("Mean squared Euclidean error")
    axes[0].set_ylim(0, .88)
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(out/f"delay_initialization.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)
    (out/"figure_caption.txt").write_text(caption+"\n", encoding="utf-8")

    report = {
        "status": "post hoc reanalysis of archived simulation data; no new simulations",
        "historical_manifest_sha256": sha256(root/"study_manifest.json"),
        "analysis_script_sha256": sha256(Path(__file__)),
        "design": {"labeled_batches": len(manifest["conditions"]), "distinct_configurations": len(groups),
                   "executed_condition_runs": len(manifest["conditions"])*30,
                   "unique_setting_seed_pairs": len(groups)*30, "independent_runs_per_setting": 30,
                   "same_seeds_reused_across_settings": True, "duplicate_checks": duplicate_checks},
        "window_rationale": "Exploratory/post hoc: 30 periods equals max delay24 plus rotation6; 90-period exclusion checks a later cutoff. Neither cutoff is a confirmed convergence criterion.",
        "uncertainty": "Two-sided 95% Student-t intervals over independent run means. Paired estimates use exact run-seed joins. Windows overlap and are not independent experiments; no multiple-testing claims.",
        "delay_windows": delay_rows, "component_windows": window_rows,
        "matched_composition": composition, "dimension_per_coordinate": dimension_rows,
        "dimension_caution": "Per-coordinate loss fixes the reporting scale only. Changing dimension also changes score magnitudes, weighting sharpness, confidence neighborhoods and the mapping of random draws.",
        "figure_caption": caption,
    }
    (out/"claims.json").write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({"output": str(out.resolve()), "design": report["design"],
                      "delay_after30": [r for r in delay_rows if r["start_inclusive"] == 30],
                      "composition_allperiods": [r for r in composition if r["start_inclusive"] == 0]}, indent=2))


if __name__ == "__main__":
    main()
