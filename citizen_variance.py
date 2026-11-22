"""Compress citizen variances at fixed mean variance and replay the original model."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from math import sqrt
from pathlib import Path
import simulation_pkd_v32 as m
from empirical_panels import save_csv

def one(job):
    a, i, seed, settings = job
    groups = ("IC", "II", "UC", "UI")
    original = [m.ARCHETYPES[g]["noise"] for g in groups]
    try:
        for name, sd in zip(groups, (0.6, 1.3, 0.5, 1.5)):
            m.ARCHETYPES[name]["noise"] = sqrt(a*sd**2 + (1-a)*1.1655)
        run = m.run_simulation(m.ModelConfig(**settings), seed=seed, run=i)
        return [dict(alpha=a,seed=seed,system=r["system"],loss=-r["mean_performance"])
                for r in m.summarize_runs([run])]
    finally:
        for g, sd in zip(groups, original):
            m.ARCHETYPES[g]["noise"] = sd

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()
    manifest = json.loads((Path(__file__).parent/"results/preprint_2026/raw/baseline/manifest.json").read_text())
    jobs = [(a,i,s,manifest["config"]) for a in (1, .5, 0) for i,s in enumerate(manifest["seeds"])]
    if args.workers == 1:
        batches = list(map(one,jobs))
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as workers:
            batches = list(workers.map(one,jobs))
    save_csv(args.output,[r for batch in batches for r in batch])

