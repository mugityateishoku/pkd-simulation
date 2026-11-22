"""Own-history adaptive reporting and held-out representation in ten-seat panels."""
import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

import simulation_pkd_v32 as m
from empirical_panels import save_csv

PANELS = ("mixed", "record", "random")
MODES = ("private", "copy", "coin", "learn0", "learn1", "learn1_optimistic")
DEFAULT_MANIFEST = Path(__file__).parent / "results/preprint_2026/raw/baseline/manifest.json"


def high_appeal_biased_reporters(agents):
    # The frozen September model stores this operational profile under a legacy label.
    return np.array([i for i, agent in enumerate(agents) if agent.agent_type == "demagogue"], dtype=int)


def generate_inputs(config, seed):
    streams = np.random.SeedSequence(seed).spawn(16)
    agents = m.create_population(config, np.random.default_rng(streams[1]))
    world = m.World(config, np.random.default_rng(streams[0]))
    observations = np.random.default_rng(streams[2])
    states, private = [], []
    for period in range(config.n_periods):
        world.update()
        if config.shock_enabled and period == config.shock_period:
            for i in high_appeal_biased_reporters(agents):
                agent = agents[i]
                agent.bias = agent.bias * config.shock_bias_multiplier
                agent.appeal *= config.shock_appeal_multiplier
        private.append(np.array([a.register_raw_prediction(world.theta_star, observations) for a in agents]))
        states.append(world.theta_star.copy())
    return agents, np.array(states), np.array(private), streams


def council_metrics(agents, panel, target, population_party, strata, population_strata):
    seats = panel.council
    party = np.bincount([agents[i].party_id for i in seats], minlength=len(population_party)) / len(seats)
    selected = np.unique(strata[seats])
    return population_strata[selected].sum(), 0.5 * np.abs(party-population_party).sum(), np.isin(target, seats).sum()/len(seats)


def trajectory(config, panel_name, mode, inputs, seed):
    agents, states, private, streams = inputs
    if panel_name == "random":
        panel = m.Sortition(config, np.random.default_rng(streams[8]))
    else:
        count = 5 if panel_name == "mixed" else 10
        choice = config.with_updates(n_expert_seats=count, n_citizen_seats=10-count, pkd_deliberation=False)
        panel = m.PhilosopherKingDemocracy(choice, np.random.default_rng(streams[9]))
    target = high_appeal_biased_reporters(agents)
    group = [a.party_id for a in agents]
    pop_party = np.bincount(group, minlength=config.n_parties) / len(agents)
    keys = [(a.primary_specialty, a.archetype, a.tolerance_bin) for a in agents]
    mapping = {key: i for i, key in enumerate(sorted(set(keys)))}
    strata = np.array([mapping[key] for key in keys])
    pop_strata = np.bincount(strata) / len(agents)
    rng = np.random.default_rng(np.random.SeedSequence([seed, 81297]))
    q = np.zeros((len(target), 2))
    if mode == "learn1_optimistic":
        q[:, 1] = 1.0
    action = np.zeros(len(target), dtype=int)
    chooser = np.arange(len(target))
    scores = np.zeros(len(agents))
    cost = np.zeros(len(target))
    previous = None
    totals = np.zeros(6)
    for t, truth in enumerate(states):
        if t % config.rotation_cycle == 0:
            panel.select_if_due(t, agents, scores)
            coverage, party_tv, occupied = council_metrics(agents, panel, target, pop_party, strata, pop_strata)
            if t:
                mean_cost = cost / config.rotation_cycle
                reward = float(mode in ("learn1", "learn1_optimistic")) * np.isin(target, panel.council) - mean_cost / (1 + mean_cost)
                q[chooser, action] += 0.2 * (reward - q[chooser, action])
                tie, explore, coin = rng.random((3, len(target)))
                if mode in ("learn0", "learn1", "learn1_optimistic"):
                    greedy = np.where(q[:, 0] == q[:, 1], tie < .5, q[:, 1] > q[:, 0])
                    action = np.where(explore < .1, coin < .5, greedy).astype(int)
                elif mode == "coin":
                    action = (coin < .5).astype(int)
                elif mode == "copy":
                    action.fill(1)
                cost.fill(0)
        values = private[t].copy()
        copying = target[action == 1]
        if len(copying):
            values[copying] = previous
        cost += ((values[target] - private[t, target]) ** 2).mean(axis=1)
        policy, _ = panel.decide(values, agents, scores)
        previous = policy.copy()
        loss = ((policy - truth) ** 2).sum()
        scores = config.track_decay * scores - (1-config.track_decay) * ((values-truth) ** 2).sum(axis=1)
        # The copy rate is the proportion of the five eligible reporters who copy.
        totals[:5] += (loss, occupied, action.mean(), coverage, party_tv)
        if t >= 150:
            totals[5] += action.mean()
    full = totals[:5] / config.n_periods
    return dict(loss=full[0], occupancy=full[1], copy=full[2], coverage=full[3],
                party_tv=full[4], late_copy=totals[5]/(config.n_periods-150))


def one(job):
    cohort, seed, settings = job
    config = m.ModelConfig(**settings)
    assert (config.n_periods, config.proxy_noise, config.feedback_delay, config.rotation_cycle) == (300, 0, 0, 6)
    inputs = generate_inputs(config, seed)
    return [dict(cohort=cohort, seed=seed, panel=panel, mode=mode,
                 **trajectory(config, panel, mode, inputs, seed)) for panel in PANELS for mode in MODES]


def fresh_seeds():
    return [int(s.generate_state(1)[0]) for s in np.random.SeedSequence(20261122).spawn(30)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()
    manifest = json.loads(args.manifest.read_text())
    cohorts = {"archive": manifest["seeds"], "fresh": fresh_seeds()}
    assert not set(cohorts["archive"]).intersection(cohorts["fresh"])
    jobs = [(cohort, seed, manifest["config"]) for cohort, seeds in cohorts.items() for seed in seeds]
    if args.workers == 1:
        batches = list(map(one, jobs))
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as workers:
            batches = list(workers.map(one, jobs))
    save_csv(args.output, [row for rows in batches for row in rows])

