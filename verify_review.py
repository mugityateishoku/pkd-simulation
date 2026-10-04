"""Independently audit October raw data, numerical claims, and source provenance.

This audit does not import either October analysis script. It recomputes run
means, Monte Carlo intervals and paired contrasts from the archived CSV files.
It verifies attribution arithmetic, not the empirical validity of the model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t

KEYS = ["run", "seed"]
METRICS = (
    "loss", "represented_population_share", "representation_js_divergence",
    "representation_total_variation", "demagogue_fraction", "final_record_weight",
    "final_lottery_weight", "effective_record_weight", "effective_lottery_weight",
    "effective_input_count", "lottery_seat_share",
)
EXTRA = ("ever_seated_population_fraction", "ever_lottery_seated_population_fraction",
         "lottery_weight_relative_to_seat_share")
TOL = 2e-12


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def close(actual, expected, context):
    if not np.allclose(actual, expected, rtol=2e-12, atol=TOL, equal_nan=False):
        raise AssertionError(f"numerical mismatch: {context}")


def interval(values):
    values = np.asarray(values, dtype=float)
    assert len(values) > 1 and np.isfinite(values).all()
    mean = values.mean()
    se = values.std(ddof=1) / np.sqrt(len(values))
    half = t.ppf(.975, len(values)-1) * se
    return {"mean": mean, "low": mean-half, "high": mean+half, "mcse": se}


def check_estimate(row, values, prefix=""):
    for key, expected in interval(values).items():
        close(row[prefix+key], expected, f"{row.get('condition', row.get('first'))}/{prefix}{key}")
    sample_key = prefix + ("n_runs" if prefix+"n_runs" in row else "n")
    assert row[sample_key] == len(values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-report", action="store_true",
                        help="Record a fresh audit report after successful validation")
    args = parser.parse_args()
    old = Path("results/preprint_2026")
    review = Path("results/review_2026")
    follow = review / "followup"
    archived = review / "archived_analysis"
    report_path = review / "independent_verification.json"
    inputs = {}

    def register(path):
        path = Path(path)
        inputs[path.as_posix()] = digest(path)
        return path

    def read_json(path):
        return json.loads(register(path).read_text(encoding="utf-8"))

    def read_csv(path):
        return pd.read_csv(register(path))

    source = read_json(old / "study_manifest.json")
    manifest = read_json(follow / "manifest.json")
    claims = read_json(archived / "claims.json")
    results = read_json(follow / "analysis/results.json")
    for path, expected in [
        ("simulation_pkd_v32.py", source["simulation_sha256"]),
        ("reproduce_preprint.py", source["runner_sha256"]),
        ("review_followup.py", manifest["observer_sha256"]),
        ("review_archived.py", claims["analysis_script_sha256"]),
    ]:
        assert digest(register(path)) == expected, f"source hash changed: {path}"
    assert manifest["simulation_sha256"] == source["simulation_sha256"]
    assert manifest["original_manifest_sha256"] == digest(old / "study_manifest.json")
    assert claims["historical_manifest_sha256"] == digest(old / "study_manifest.json")
    assert manifest["seeds"] == source["seeds"]
    assert manifest["n_runs"] == source["n_runs"] == 30
    assert manifest["n_periods"] == source["n_periods"] == 300
    assert len(manifest["conditions"]) == 11
    expected_index = pd.MultiIndex.from_tuples(list(enumerate(manifest["seeds"])), names=KEYS)
    expected_periods = pd.MultiIndex.from_tuples(
        [(run, seed, period) for run, seed in enumerate(manifest["seeds"]) for period in range(300)],
        names=KEYS+["period"],
    )
    old_cache = {}

    def original(label):
        if label not in old_cache:
            frame = read_csv(old / "raw" / label / "period_metrics.csv.gz")
            old_cache[label] = frame[frame.system == "PKD"].set_index(KEYS+["period"]).sort_index()
            assert old_cache[label].index.equals(expected_periods)
        return old_cache[label]

    groups = {}
    for label, config in source["conditions"].items():
        groups.setdefault(json.dumps(config, sort_keys=True), []).append(label)
    assert len(source["conditions"]) == 55 and len(groups) == 54
    assert claims["design"]["distinct_configurations"] == 54
    identity = read_csv(archived / "condition_identity.csv").set_index("label")
    assert identity.index.is_unique and set(identity.index) == set(source["conditions"])
    for labels in groups.values():
        for label in labels:
            canonical = json.dumps(source["conditions"][label], sort_keys=True, separators=(",", ":"))
            assert identity.loc[label, "config_sha256"] == hashlib.sha256(canonical.encode()).hexdigest()
            assert identity.loc[label, "representative_label"] == labels[0]
            assert identity.loc[label, "labels_for_setting"] == len(labels)
    for labels in groups.values():
        for duplicate in labels[1:]:
            for filename in ["period_metrics.csv.gz", "run_summary.csv"]:
                first = read_csv(old / "raw" / labels[0] / filename)
                second = read_csv(old / "raw" / duplicate / filename)
                pd.testing.assert_frame_equal(first, second, check_exact=True)

    frames, means, windows = {}, {}, {}
    overlap = []
    largest_summary_gap = 0.0
    largest_reconstruction_gap = 0.0
    for label, config in manifest["conditions"].items():
        population_size = sum(config[name] for name in ["n_citizens", "n_experts", "n_demagogues"])
        folder = follow / "raw" / label
        frame = read_csv(folder / "period_influence.csv.gz").set_index(KEYS+["period"]).sort_index()
        assert frame.index.is_unique and frame.index.equals(expected_periods)
        assert not frame.isna().any().any()
        assert np.isfinite(frame.select_dtypes("number")).all().all()
        close(frame.loss, -frame.performance, label+" loss sign")
        assert (frame.loss >= -TOL).all()
        ids = np.array([json.loads(value) for value in frame.council_ids])
        records = [json.loads(value) for value in frame.record_seat_ids]
        lotteries = [json.loads(value) for value in frame.lottery_seat_ids]
        assert ids.shape == (9000, 10)
        assert np.all((ids >= 0) & (ids < population_size))
        for council, record, lottery in zip(ids, records, lotteries):
            assert len(set(council)) == 10
            assert len(record) == config["n_expert_seats"] and len(lottery) == config["n_citizen_seats"]
            assert record+lottery == council.tolist() and not set(record).intersection(lottery)
        record_mask = np.array([[member in record for member in council] for council, record in zip(ids, records)])
        final = np.array([json.loads(value) for value in frame.final_weights])
        effective = np.array([json.loads(value) for value in frame.effective_input_coefficients])
        assert final.shape == effective.shape == (9000, 10)
        for weights in [final, effective]:
            assert np.isfinite(weights).all() and weights.min() >= -TOL
            close(weights.sum(axis=1), np.ones(9000), label+" convex weights")
        close(frame.final_record_weight, (final*record_mask).sum(axis=1), label+" record final")
        close(frame.final_lottery_weight, (final*(~record_mask)).sum(axis=1), label+" lottery final")
        close(frame.effective_record_weight, (effective*record_mask).sum(axis=1), label+" record input")
        close(frame.effective_lottery_weight, (effective*(~record_mask)).sum(axis=1), label+" lottery input")
        close(frame.effective_input_count, 1 / (effective**2).sum(axis=1), label+" effective count")
        close(frame.lottery_seat_share, (~record_mask).mean(axis=1), label+" seat share")
        if not config["pkd_deliberation"]:
            close(effective, final, label+" no-deliberation identity")
        if not config["pkd_score_weighting"]:
            close(final, np.full((9000, 10), .1), label+" equal final weights")
        largest_reconstruction_gap = max(largest_reconstruction_gap, frame.policy_reconstruction_max_gap.max())
        assert frame.policy_reconstruction_max_gap.max() < TOL
        frames[label] = frame
        actual = frame.groupby(level=KEYS)[list(METRICS)].mean().reindex(expected_index)
        reported = read_csv(folder / "run_summary.csv").set_index(KEYS).sort_index()
        assert reported.index.equals(expected_index) and (reported.condition == label).all()
        close(actual, reported[list(METRICS)], label+" run summaries")
        largest_summary_gap = max(largest_summary_gap, np.abs(actual-reported[list(METRICS)]).to_numpy().max())
        means[label] = actual
        reported_windows = read_csv(folder / "run_window_summary.csv").set_index(["window"]+KEYS).sort_index()
        assert reported_windows.index.is_unique and len(reported_windows) == 60
        assert set(reported_windows.index.get_level_values("window")) == {"all_periods", "periods_30_onward"}
        for window, start in [("all_periods", 0), ("periods_30_onward", 30)]:
            subset = frame[frame.index.get_level_values("period") >= start]
            run_means = subset.groupby(level=KEYS)[list(METRICS)].mean().reindex(expected_index)
            for key, run in subset.groupby(level=KEYS):
                for column, metric in [("council_ids", EXTRA[0]), ("lottery_seat_ids", EXTRA[1])]:
                    seated = {i for value in run[column] for i in json.loads(value)}
                    run_means.loc[key, metric] = len(seated)/population_size
            if config["n_citizen_seats"]:
                run_means[EXTRA[2]] = run_means.effective_lottery_weight/run_means.lottery_seat_share
            claimed = reported_windows.xs(window).reindex(expected_index)
            assert (claimed.condition == label).all() and (claimed.first_period == start).all()
            assert (claimed.last_period == 299).all()
            close(run_means, claimed[run_means.columns], label+" "+window)
            windows[label, window] = run_means
        for old_label, old_config in source["conditions"].items():
            if config == old_config:
                previous = original(old_label)
                # All shared numerical fields, not just mean loss, must replay.
                common = frame.select_dtypes("number").columns.intersection(previous.select_dtypes("number").columns)
                close(frame[common], previous[common], label+" archived trajectory")
                overlap.append({"followup": label, "september": old_label})
    assert len(overlap) == 4
    assert len(results["estimates"]) == 121
    assert len(results["paired_contrasts"]) == 253
    assert len(results["window_estimates"]) == 304
    assert len(results["window_paired_contrasts"]) == 78
    for k in [0, 2, 5, 8, 10]:
        left, right = frames[f"record_{k:02d}_score"], frames[f"record_{k:02d}_equal"]
        for field in ["council_ids", "record_seat_ids", "lottery_seat_ids"]:
            assert np.array_equal(left[field], right[field]), f"matched composition changed: {k}/{field}"
        close(left.represented_population_share, right.represented_population_share, f"matched coverage {k}")
    for row in results["estimates"]:
        check_estimate(row, means[row["condition"]][row["metric"]])
    for row in results["paired_contrasts"]:
        check_estimate(row, means[row["first"]][row["metric"]]-means[row["second"]][row["metric"]])
    for row in results["window_estimates"]:
        check_estimate(row, windows[row["condition"], row["window"]][row["metric"]])
    for row in results["window_paired_contrasts"]:
        check_estimate(row, windows[row["first"], row["window"]][row["metric"]]
                       - windows[row["second"], row["window"]][row["metric"]])
    for key in ["estimates", "paired_contrasts", "window_estimates", "window_paired_contrasts"]:
        pd.testing.assert_frame_equal(read_csv(follow / "analysis" / (key+".csv")),
                                      pd.DataFrame(results[key]), check_exact=False, rtol=2e-12, atol=TOL)

    def period_means(label, start, stop, metric="loss"):
        frame = original(label)
        period = frame.index.get_level_values("period")
        selected = frame[(period >= start) & (period < stop)]
        values = -selected.performance if metric == "loss" else selected[metric]
        return values.groupby(level=KEYS).mean().reindex(expected_index)

    for row in claims["component_windows"] + claims["delay_windows"]:
        start, stop = row["start_inclusive"], row["stop_exclusive"]
        values = period_means(row["condition"], start, stop)
        check_estimate(row, values)
        check_estimate(row, values-period_means("baseline", start, stop), "paired_vs_baseline_")
    archived_runs = read_csv(archived / "initialization_window_run_means.csv")
    run_keys = ["condition", "start_inclusive", "stop_exclusive"]
    assert not archived_runs.duplicated(run_keys+KEYS).any()
    assert len(archived_runs) == len(claims["component_windows"])*30 == 1980
    for key, rows in archived_runs.groupby(run_keys):
        indexed = rows.set_index(KEYS).sort_index()
        assert indexed.index.equals(expected_index)
        close(indexed.mean_loss, period_means(*key), "archived window run means")
    for row in claims["matched_composition"]:
        start, stop, metric = row["start_inclusive"], row["stop_exclusive"], row["metric"]
        hybrid = period_means("no_deliberation", start, stop, metric)
        record = period_means("record_only_10", start, stop, metric)
        check_estimate(row, hybrid-record)
        close(row["hybrid_mean"], hybrid.mean(), "composition hybrid")
        close(row["record_only_mean"], record.mean(), "composition record")
        close(row["relative_change_of_means_percent"], (hybrid.mean()/record.mean()-1)*100, "composition relative")
    for row in claims["dimension_per_coordinate"]:
        frame = read_csv(old / "raw" / row["condition"] / "run_summary.csv")
        values = -frame[frame.system == row["system"]].set_index(KEYS).reindex(expected_index).mean_performance/row["n_dim"]
        assert row["n_dim"] == source["conditions"][row["condition"]]["n_dim"]
        check_estimate(row, values)
    for filename, key in [
        ("initialization_window_estimates.csv", "component_windows"),
        ("delay_window_estimates.csv", "delay_windows"),
        ("matched_composition_contrasts.csv", "matched_composition"),
        ("dimension_per_coordinate_estimates.csv", "dimension_per_coordinate"),
    ]:
        pd.testing.assert_frame_equal(read_csv(archived / filename), pd.DataFrame(claims[key]),
                                      check_exact=False, rtol=2e-12, atol=TOL)
    report = {
        "audit_script_sha256": digest(__file__), "source_hashes_match": True,
        "followup_conditions": 11, "followup_runs": 330, "followup_period_rows": 99000,
        "september_labeled_batches": 55, "september_distinct_configurations": 54,
        "september_duplicate_tables_identical": True, "overlapping_configurations": overlap,
        "matched_score_equal_councils_identical": True,
        "largest_run_summary_recalculation_gap": float(largest_summary_gap),
        "largest_recorded_policy_reconstruction_gap": float(largest_reconstruction_gap),
        "attribution_rows_and_all_reported_intervals_verified": True,
        "limitation": "Raw coefficients do not archive agent estimates. Policy reconstruction is a recorded execution invariant, checked separately by observer tests and unchanged-source replay; this CSV audit verifies coefficient arithmetic, aggregation, pairing, and provenance.",
        "input_sha256": dict(sorted(inputs.items())),
    }
    if report_path.exists() and not args.write_report:
        recorded = json.loads(report_path.read_text(encoding="utf-8"))
        assert recorded["input_sha256"] == report["input_sha256"], "audited input file hashes changed"
        assert recorded["audit_script_sha256"] == report["audit_script_sha256"], "audit script changed"
    if args.write_report:
        report_path.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "input_sha256"}, indent=2))


if __name__ == "__main__":
    main()
