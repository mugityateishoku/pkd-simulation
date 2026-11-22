"""Matched weight-strength experiments on synthetic reports and human answers."""
import argparse
import csv
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from urllib.request import urlopen

import numpy as np

import simulation_pkd_v32 as model
from adaptive_panels import DEFAULT_MANIFEST, generate_inputs
from empirical_panels import (DRAWS, SOURCE_URL, TRIMS, load_pools, save_csv,
                              select_panels, stable_weights)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results/weight_strength"
BETAS = np.array([0, .125, .25, .5, 1, 2, 4])
CORRELATIONS = (0, .25, .5, .75)
SIM_METRICS = ("loss", "lottery_weight", "coverage", "seat_party_tv", "weighted_party_tv")
HUMAN_METRICS = ("loss", "absolute_error", "lottery_weight", "seat_party_tv", "weighted_party_tv", "pool_median_loss")


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def source_components(config, agents, states, private, seed):
    """Decompose the archived observation into its conditional mean and noise."""
    bias = np.array([a.bias for a in agents])
    means = states[:, None, :] + bias
    if config.shock_enabled:
        # generate_inputs returns each agent after the scheduled bias shock.
        if config.shock_period < len(states):
            means[:config.shock_period] = states[:config.shock_period, None, :] + bias / config.shock_bias_multiplier
    scales = np.repeat([[a.observation_noise for a in agents]], config.n_dim, axis=0).T.copy()
    for i, agent in enumerate(agents):
        scales[i, list(agent.specialty_dims)] *= .3
    rng = np.random.default_rng(np.random.SeedSequence([seed, 20261123]))
    common = rng.normal(size=states.shape)[:, None, :] * scales[None, :, :]
    return means, private - means, common


def simulation(job):
    seed, settings = job
    cfg = model.ModelConfig(**settings)
    agents, states, private, streams = generate_inputs(cfg, seed)
    means, residual, common = source_components(cfg, agents, states, private, seed)
    parties = np.array([a.party_id for a in agents])
    party_indicators = np.eye(cfg.n_parties)[parties]
    pop_party = party_indicators.mean(axis=0)
    tolerance = np.array([a.tolerance for a in agents])
    strata_key = [(a.primary_specialty, a.archetype, a.tolerance_bin) for a in agents]
    strata_map = {k:i for i,k in enumerate(sorted(set(strata_key)))}
    strata = np.array([strata_map[k] for k in strata_key])
    pop_strata = np.bincount(strata)/len(agents)
    output = []
    for corr in CORRELATIONS:
        reports = private if corr == 0 else means + np.sqrt(1-corr)*residual + np.sqrt(corr)*common
        panel = model.PhilosopherKingDemocracy(cfg, np.random.default_rng(streams[9]))
        scores = np.zeros(len(agents))
        totals = np.zeros((2, len(BETAS), len(SIM_METRICS)))
        for t, (truth, x) in enumerate(zip(states, reports)):
            panel.select_if_due(t, agents, scores)
            ids = panel.council
            selected = x[ids]
            scaled = BETAS[:, None] * scores[ids]
            final = stable_weights(scaled)
            near = np.linalg.norm(selected[:, None] - selected, axis=2) <= tolerance[ids, None]
            local = stable_weights(np.where(near[None, :, :], scaled[:, None, :], -np.inf))
            revised = (1-cfg.revision_rate)*final + cfg.revision_rate*np.einsum("bi,bij->bj", final, local)
            coverage = pop_strata[np.unique(strata[ids])].sum()
            seat_tv = .5*abs(party_indicators[ids].mean(axis=0)-pop_party).sum()
            for i, coeff in enumerate((final, revised)):
                totals[i, :, 0] += ((coeff @ selected - truth)**2).sum(axis=1)
                totals[i, :, 1] += coeff[:, cfg.n_expert_seats:].sum(axis=1)
                totals[i, :, 2] += coverage
                totals[i, :, 3] += seat_tv
                totals[i, :, 4] += .5*abs(coeff @ party_indicators[ids]-pop_party).sum(axis=1)
            scores = cfg.track_decay*scores - (1-cfg.track_decay)*((x-truth)**2).sum(axis=1)
        for i, rule in enumerate(("direct", "local")):
            for beta, metrics in zip(BETAS, totals[i]/len(states)):
                output.append(dict(seed=seed, corr=corr, rule=rule, beta=beta, **dict(zip(SIM_METRICS, metrics))))
    return output


def empirical(data):
    pools, truths = load_pools(data)
    reference = {(int(r["experiment"]),r["set"],r["network"],int(r["pair"]),r["question"],float(r["trim"])):r
                 for r in read_csv(ROOT/"results/november_2026/empirical_folds.csv")}
    output = []
    for index,(key, people) in enumerate(sorted(pools.items())):
        exp, group, network, pair = key
        qs = sorted(q for e,q in truths if e==exp)
        ids = [p for p in sorted(people) if all(np.isfinite(people[p].get(q,np.nan)) for q in qs)]
        party = np.array([p[0]=="Dem" for p in ids])
        raw = np.array([[people[p][q] for q in qs] for p in ids])
        truth = np.array([truths[exp,q] for q in qs])
        scale = np.subtract(*np.quantile(raw,[.75,.25],axis=0))
        for trim in TRIMS:
            vals = np.clip(raw,*np.quantile(raw,[trim,1-trim],axis=0))
            totals = np.zeros((len(BETAS),len(HUMAN_METRICS)))
            for hold,q in enumerate(qs):
                train = np.arange(len(qs))!=hold
                record = -(((vals[:,train]-truth[train])/scale[train])**2).mean(axis=1)
                rng = np.random.default_rng(np.random.SeedSequence([20261122,index,hold]))
                _,panel,_ = select_panels(record,party,rng.random((DRAWS,len(ids))),rng.random((DRAWS,len(ids))),rng.random(DRAWS))
                weights = stable_weights(BETAS[:,None,None]*record[panel][None,:,:])
                preds = (weights*vals[panel,hold]).sum(axis=-1)
                errors = (preds-truth[hold])/scale[hold]
                median_error = (np.median(vals[:,hold])-truth[hold])/scale[hold]
                metrics = np.column_stack(((errors**2).mean(axis=1),abs(errors).mean(axis=1),
                    weights[:,:,5:].sum(axis=-1).mean(axis=1),
                    np.full(len(BETAS),abs(party[panel].mean(axis=1)-party.mean()).mean()),
                    abs((weights*party[panel]).sum(axis=-1)-party.mean()).mean(axis=1),
                    np.full(len(BETAS),median_error**2)))
                ref = reference[(*key,q,trim)]
                for b,prefix in ((0,"mixed_equal"),(1,"mixed_score")):
                    row = metrics[BETAS==b][0]
                    np.testing.assert_allclose(row[:3], [float(ref[prefix]),float(ref[prefix+"_mae"]),
                                               .5 if b==0 else float(ref["lottery_weight"])], rtol=1e-11, atol=1e-12)
                totals += metrics
            for beta, metrics in zip(BETAS, totals/len(qs)):
                output.append(dict(experiment=exp,group=group,network=network,pair=pair,trim=trim,beta=beta,
                                   **dict(zip(HUMAN_METRICS,metrics))))
    return output


if __name__=="__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("study",choices=("simulation","human"))
    ap.add_argument("--input", type=Path, help="Local public human CSV")
    ap.add_argument("--output",type=Path,default=OUT)
    ap.add_argument("--workers",type=int,default=1)
    args = ap.parse_args()
    if args.study=="human":
        if args.input:
            data=args.input.read_bytes()
        else:
            with urlopen(SOURCE_URL,timeout=90) as stream:
                data=stream.read()
        save_csv(args.output/"human_pools.csv",empirical(data))
    else:
        manifest=json.loads(DEFAULT_MANIFEST.read_text())
        with ProcessPoolExecutor(max_workers=args.workers) as workers:
            batches=workers.map(simulation,[(s,manifest["config"]) for s in manifest["seeds"]])
            save_csv(args.output/"simulation_runs.csv",[row for batch in batches for row in batch])
