"""Retrospective four-question panel comparisons on public first-round estimates."""
import argparse
import csv
import hashlib
import io
from collections import defaultdict
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import quote

import numpy as np

SOURCE_COMMIT = "79d7658da169d9a943b0cbd221c38f47ffa7c11a"
SOURCE_NAME = "Becker Centola Porter - Wisdom of Partisan Crowds - Supplementary Dataset.csv"
SOURCE_URL = "https://raw.githubusercontent.com/joshua-a-becker/wisdom-of-partisan-crowds/" + SOURCE_COMMIT + "/" + quote(SOURCE_NAME)
SOURCE_SHA256 = "33596e95e4a02b015a9b971f44af80878d9ed9ce9fc9de0103394ce075539c97"
DRAWS = 512
TRIMS = (0.05, 0.025, 0.0)


def load_pools(data):
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError("Unexpected source file checksum")
    pools = defaultdict(dict)
    truths = {}
    for row in csv.DictReader(io.StringIO(data.decode("utf-8-sig"))):
        key = (int(row["experiment"]), row["set"], row["network"], int(row["pair_id"]))
        q = row["q"]
        truth = float(row["truth"])
        assert truths.setdefault((key[0], q), truth) == truth
        person = (row["party"], int(row["user_id"]))
        responses = pools[key].setdefault(person, {})
        if q in responses:
            raise ValueError("Duplicate participant and task")
        value = row["response_1"]
        responses[q] = float(value) if value not in ("NA", "") else np.nan
    return pools, truths


def stable_weights(scores):
    raw = np.exp(scores - scores.max(axis=-1, keepdims=True))
    return raw / raw.sum(axis=-1, keepdims=True)


def select_panels(records, party, tie, lottery, tie_quota):
    # A common random priority breaks equal records for the two record panels.
    ranks = np.lexsort((tie, np.broadcast_to(-records, tie.shape)), axis=1)
    top = ranks[:, :10]
    first = top[:, :5]
    available = np.ones(tie.shape, dtype=bool)
    np.put_along_axis(available, first, False, axis=1)
    quota = 5 * (available & party).sum(axis=1) / (len(party) - 5)
    lower = np.floor(quota)
    extra = (quota - lower > 0.5) | (np.isclose(quota - lower, 0.5) & (tie_quota < 0.5))
    n_party = (lower + extra).astype(int)
    group1 = np.argsort(np.where(available & party, lottery, np.inf), axis=1)
    group0 = np.argsort(np.where(available & ~party, lottery, np.inf), axis=1)
    slots = np.arange(5)[None, :]
    from_other = np.maximum(0, slots - n_party[:, None])
    lot = np.where(slots < n_party[:, None], group1[:, :5], np.take_along_axis(group0, from_other, axis=1))
    return top, np.concatenate((first, lot), axis=1), np.argsort(lottery, axis=1)[:, :10]


def compare_fold(values, truths, scales, party, hold, random_draws):
    other = np.arange(4) != hold
    records = -np.mean(((values[:, other] - truths[other]) / scales[other]) ** 2, axis=1)
    top, mixed, random = select_panels(records, party, *random_draws)
    estimates = values[:, hold]
    mix_w = stable_weights(records[mixed])
    estimates_by_rule = {
        "record10_score": (estimates[top] * stable_weights(records[top])).sum(axis=1),
        "mixed_score": (estimates[mixed] * mix_w).sum(axis=1),
        "mixed_equal": estimates[mixed].mean(axis=1),
        "random10_equal": estimates[random].mean(axis=1),
        "pool_equal": estimates.mean(),
        "pool_score": stable_weights(records) @ estimates,
        "pool_median": np.median(estimates),
    }
    losses = {key: float(np.mean(((v - truths[hold]) / scales[hold]) ** 2)) for key, v in estimates_by_rule.items()}
    absolute = {key + "_mae": float(np.mean(np.abs((estimates_by_rule[key] - truths[hold]) / scales[hold])))
                for key in ("mixed_score", "mixed_equal")}
    return dict(**losses, **absolute, lottery_weight=float(mix_w[:, 5:].sum(axis=1).mean()))


def analyze(data):
    pools, ground_truth = load_pools(data)
    output = []
    for ix, (key, people) in enumerate(sorted(pools.items())):
        exp, set_id, network, pair = key
        qs = sorted(q for e, q in ground_truth if e == exp)
        assert len(qs) == 4
        ids = [pid for pid in sorted(people) if all(np.isfinite(people[pid].get(q, np.nan)) for q in qs)]
        party = np.array([pid[0] == "Dem" for pid in ids])
        assert set(pid[0] for pid in ids) == {"Dem", "Repub"} and min(party.sum(), (~party).sum()) >= 10
        raw = np.array([[people[pid][q] for q in qs] for pid in ids])
        truths = np.array([ground_truth[exp, q] for q in qs])
        scales = np.subtract(*np.quantile(raw, [0.75, 0.25], axis=0))
        if np.any(scales <= 0):
            raise ValueError("The within-pool response IQR must be positive")
        for hold, question in enumerate(qs):
            rng = np.random.default_rng(np.random.SeedSequence([20261122, ix, hold]))
            draws = (rng.random((DRAWS, len(ids))), rng.random((DRAWS, len(ids))), rng.random(DRAWS))
            for trim in TRIMS:
                lower, upper = np.quantile(raw, [trim, 1.0-trim], axis=0)
                values = np.clip(raw, lower, upper)
                output.append(dict(experiment=exp, set=set_id, network=network, pair=pair, question=question,
                                   trim=trim, eligible=len(ids), observed=len(people),
                                   **compare_fold(values, truths, scales, party, hold, draws)))
    return output


def save_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        w = csv.DictWriter(stream, fieldnames=rows[0].keys(), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, help="Optional local copy of the pinned public CSV")
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    if args.input:
        data = args.input.read_bytes()
    else:
        with urlopen(SOURCE_URL, timeout=90) as response:
            data = response.read()
    save_csv(args.output, analyze(data))

