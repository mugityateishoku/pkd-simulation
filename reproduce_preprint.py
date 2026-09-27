"""Frozen September 2026 study. All conditions are declared before execution.

Each condition uses the same 30 run seeds and 300 periods. Confidence intervals
quantify Monte Carlo variation conditional on this model, not societal effects.
Workers parallelize independent conditions; seeds never depend on worker order.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import importlib.metadata
import json
import platform
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
import numpy as np
from simulation_pkd_v32 import ModelConfig, run_simulation, summarize_runs, write_csv


def conditions():
    jobs = {'baseline': {}, 'shock_absent': {'shock_enabled': False}}
    jobs.update({
        'no_deliberation': {'pkd_deliberation': False},
        'record_only_10': {'n_expert_seats': 10, 'n_citizen_seats': 0, 'pkd_deliberation': False},
        'record_only_5': {'n_expert_seats': 5, 'n_citizen_seats': 0, 'pkd_deliberation': False},
        'lottery_only_10': {'n_expert_seats': 0, 'n_citizen_seats': 10, 'pkd_deliberation': False},
        'uniform_lottery': {'lottery_sampling': 'uniform'},
        'screened_lottery': {'citizen_pool': 'citizens_only'},
        'equal_weights': {'pkd_score_weighting': False},
        'frozen_after_100': {'freeze_scores_at': 100},
    })
    for w in [0., .25, .5, .75, 1.]:
        jobs[f'election_weight_{w:g}'] = dict(electoral_record_weight=w, electoral_information_noise=0., electoral_media_amplification=0.)
    for field, vals in [('electoral_information_noise', [.25, 1., 2.]), ('electoral_media_amplification', [.25, 1., 2.])]:
        for v in vals:
            jobs[f'{field}_{v:g}'] = dict(electoral_record_weight=.75, electoral_information_noise=0., electoral_media_amplification=0.)
            jobs[f'{field}_{v:g}'][field] = v
    jobs['matched_record_selection'] = dict(n_expert_seats=5, n_citizen_seats=0,
        pkd_deliberation=False, pkd_score_weighting=False, election_cycle=6,
        electoral_record_weight=1., electoral_information_noise=0.,
        electoral_media_amplification=0., electoral_random_utility_noise=0.)
    for field, values in {
        'proxy_noise': [.5, 1., 2.], 'feedback_delay': [3, 12, 24],
        'scored_dimensions': [1, 3, 5], 'expert_noise': [.6, .9],
        'track_decay': [.5, .99], 'n_dim': [2, 20],
        'regime_change_prob': [0., .1], 'demagogue_bias_norm': [0., 3.],
    }.items():
        for v in values:
            jobs[f'{field}_{v:g}'] = {field: v}
    for fraction in [.15, .30]:
        jobs[f'demagogue_fraction_{fraction:g}'] = {'n_demagogues': round(100*fraction), 'n_citizens': 85-round(100*fraction)}
    for mode in ['independent_herding', 'coordinated_herding']:
        jobs[mode] = {'strategic_mode': mode}
    for mode in ['indicator_targeting', 'indicator_targeting_firewall']:
        for noise in [0., .5, 1.]:
            jobs[f'{mode}_{noise:g}'] = {'strategic_mode': mode, 'proxy_noise': noise}
    for noise in [0., 1.]:
        for delay in [0, 12]:
            jobs[f'interaction_noise_{noise:g}_delay_{delay}'] = {'proxy_noise': noise, 'feedback_delay': delay, 'expert_noise': .9}
    return jobs


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_condition(job):
    label, config_dict, seeds, destination, source_hash = job
    config = ModelConfig.from_mapping(config_dict)
    folder = Path(destination) / 'raw' / label
    folder.mkdir(parents=True, exist_ok=True)
    summary = []
    start = time.perf_counter()
    with gzip.open(folder / 'period_metrics.csv.gz', 'wt', encoding='utf-8', newline='') as handle:
        writer = None
        for run, seed in enumerate(seeds):
            result = run_simulation(config, seed=seed, run=run)
            summary.extend(summarize_runs([result]))
            for period in result.periods:
                row = asdict(period)
                if writer is None:
                    writer = csv.DictWriter(handle, fieldnames=list(row))
                    writer.writeheader()
                writer.writerow(row)
            if label == 'baseline':
                for name, records in [('election_results', result.election_records), ('final_agents', result.agents)]:
                    rows = [asdict(x) for x in records]
                    with gzip.open(folder / f'{name}_{run:02d}.csv.gz', 'wt', encoding='utf-8', newline='') as extra:
                        ew = csv.DictWriter(extra, fieldnames=list(rows[0])); ew.writeheader(); ew.writerows(rows)
                np.savez_compressed(folder / f'registered_scores_{run:02d}.npz', scores=result.raw_score_history, final_track_records=result.final_track_records)
    write_csv(folder / 'run_summary.csv', summary)
    (folder / 'manifest.json').write_text(json.dumps({'condition': label, 'config': config_dict, 'seeds': seeds, 'simulation_sha256': source_hash}, indent=2), encoding='utf-8')
    return label, time.perf_counter()-start


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('results/preprint_2026'))
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--runs', type=int, default=30)
    parser.add_argument('--periods', type=int, default=300)
    parser.add_argument('--only', default='all')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    base = ModelConfig(n_periods=args.periods, shock_period=min(100, args.periods//3), include_sortition_deliberation=True)
    seeds = [int(s.generate_state(1, dtype=np.uint32)[0]) for s in np.random.SeedSequence(20260927).spawn(args.runs)]
    selected = conditions()
    if args.only != 'all':
        selected = {name: selected[name] for name in args.only.split(',')}
    source_hash = file_hash(Path(__file__).with_name('simulation_pkd_v32.py'))
    resolved = {name: asdict(base.with_updates(**updates)) for name, updates in selected.items()}
    manifest = {'study': 'PKD preprint 2026-09-27', 'status': 'new exploratory simulation; not preregistered or historical replication',
                'n_runs': args.runs, 'n_periods': args.periods, 'seed_root': 20260927, 'seeds': seeds,
                'simulation_sha256': source_hash, 'runner_sha256': file_hash(__file__), 'conditions': resolved,
                'python': sys.version, 'platform': platform.platform(), 'workers': args.workers,
                'packages': {x: importlib.metadata.version(x) for x in ['numpy','scipy','matplotlib','pytest']}}
    (args.output / 'study_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    jobs = [(label, config, seeds, str(args.output), source_hash) for label, config in resolved.items()]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_condition, job) for job in jobs]
        for i, future in enumerate(as_completed(futures), 1):
            label, elapsed = future.result()
            print(f'{i}/{len(jobs)} completed {label} ({elapsed:.1f}s)', flush=True)
    # Source identity is checked after execution to prevent mixing code revisions.
    if file_hash(Path(__file__).with_name('simulation_pkd_v32.py')) != source_hash:
        raise RuntimeError('Core source changed while experiments were running')


if __name__ == '__main__':
    main()
