"""Specification-aligned PKD agent-based model (corrected v3.2 series).

The implementation keeps three channels separate in every period:

1. ``raw_prediction`` is registered once, before any council deliberation.
2. ``post_deliberation_belief`` exists only inside a governance system.
3. Track records are updated exactly once from ``raw_prediction``.

This separation makes track-record scores independent of council membership.
The comparison formerly called "Electoral Democracy" is deliberately named
``Appeal-based selection baseline`` because it ranks candidates by appeal plus
noise; it does not simulate voters or aggregate ballots.

The module depends only on NumPy. Plotting and inferential statistics live in
``reproduce_all.py`` so the core model remains easy to test in CI.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import csv
import json

import numpy as np


SYSTEM_AUTOCRACY = "Autocracy"
SYSTEM_APPEAL = "Appeal-based selection baseline"
SYSTEM_SORTITION = "Sortition"
SYSTEM_SORTITION_DELIBERATION = "Sortition + deliberation"
SYSTEM_PKD = "PKD"
SYSTEM_RETROSPECTIVE = "Collective-retrospective appeal baseline"
SYSTEM_SCORE_INFORMED = "Score-informed appeal baseline"

BASELINE_SYSTEMS = (
    SYSTEM_AUTOCRACY,
    SYSTEM_APPEAL,
    SYSTEM_SORTITION,
    SYSTEM_PKD,
)


@dataclass(frozen=True)
class ModelConfig:
    """All model inputs required to reproduce a run."""

    n_periods: int = 300
    n_citizens: int = 80
    n_experts: int = 15
    n_demagogues: int = 5
    n_dim: int = 10
    drift_rate: float = 0.02
    regime_change_prob: float = 0.03
    shock_period: int = 100
    shock_appeal_multiplier: float = 1.5
    shock_bias_multiplier: float = 2.0
    track_decay: float = 0.9
    revision_rate: float = 0.3
    appeal_ranking_noise: float = 0.2
    autocracy_cycle: int = 48
    appeal_cycle: int = 12
    rotation_cycle: int = 6
    appeal_council_size: int = 5
    sortition_size: int = 10
    n_expert_seats: int = 5
    n_citizen_seats: int = 5
    expert_noise: float = 0.3
    demagogue_noise: float = 0.8
    demagogue_bias_norm: float = 1.5
    pkd_deliberation: bool = True
    include_sortition_deliberation: bool = False
    proxy_noise: float = 0.0
    feedback_delay: int = 0
    scored_dimensions: int | None = None
    freeze_scores_at: int | None = None
    strategic_mode: str = "none"
    strategic_noise: float = 0.1
    retrospective_weight: float | None = None
    retrospective_memory: float = 0.5
    score_informed_weight: float | None = None

    @property
    def population_size(self) -> int:
        return self.n_citizens + self.n_experts + self.n_demagogues

    def validate(self) -> None:
        positive_ints = {
            "n_periods": self.n_periods,
            "n_dim": self.n_dim,
            "population_size": self.population_size,
            "autocracy_cycle": self.autocracy_cycle,
            "appeal_cycle": self.appeal_cycle,
            "rotation_cycle": self.rotation_cycle,
        }
        for name, value in positive_ints.items():
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if not 0.0 <= self.track_decay < 1.0:
            raise ValueError("track_decay must be in [0, 1)")
        if not 0.0 <= self.revision_rate <= 1.0:
            raise ValueError("revision_rate must be in [0, 1]")
        if self.proxy_noise < 0 or self.feedback_delay < 0:
            raise ValueError("proxy_noise and feedback_delay must be non-negative")
        if self.scored_dimensions is not None and not (
            1 <= self.scored_dimensions <= self.n_dim
        ):
            raise ValueError("scored_dimensions must be between 1 and n_dim")
        if self.n_expert_seats + self.n_citizen_seats > self.population_size:
            raise ValueError("PKD council cannot exceed the population")
        if self.sortition_size > self.population_size:
            raise ValueError("sortition_size cannot exceed the population")
        allowed = {
            "none",
            "independent_herding",
            "coordinated_herding",
            "indicator_targeting",
            "indicator_targeting_firewall",
        }
        if self.strategic_mode not in allowed:
            raise ValueError(f"strategic_mode must be one of {sorted(allowed)}")

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "ModelConfig":
        config = cls(**dict(values))
        config.validate()
        return config

    @classmethod
    def from_json(cls, path: str | Path) -> "ModelConfig":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.from_mapping(json.load(handle))

    def with_updates(self, **updates: Any) -> "ModelConfig":
        config = replace(self, **updates)
        config.validate()
        return config


@dataclass(eq=False)
class Agent:
    id: int
    agent_type: str
    archetype: str
    observation_noise: float
    appeal: float
    bias: np.ndarray
    political_interest: float
    tolerance: float
    specialty_dims: tuple[int, ...]
    track_record: float = 0.0

    @property
    def tolerance_bin(self) -> str:
        if self.tolerance >= 3.0:
            return "high"
        if self.tolerance >= 1.5:
            return "mid"
        return "low"

    @property
    def primary_specialty(self) -> int:
        return self.specialty_dims[0]

    def register_raw_prediction(
        self, theta_star: np.ndarray, rng: np.random.Generator
    ) -> np.ndarray:
        scales = np.full(theta_star.shape, self.observation_noise, dtype=float)
        scales[list(self.specialty_dims)] *= 0.3
        return theta_star + self.bias + rng.normal(0.0, scales)


ARCHETYPES: dict[str, dict[str, Any]] = {
    "IC": {
        "fraction": 0.25,
        "noise": 0.6,
        "interest": 0.9,
        "tolerance": (2.5, 5.0),
        "appeal": (0.3, 0.7),
    },
    "II": {
        "fraction": 0.20,
        "noise": 1.3,
        "interest": 0.9,
        "tolerance": (0.5, 1.8),
        "appeal": (0.4, 0.8),
    },
    "UC": {
        "fraction": 0.25,
        "noise": 0.5,
        "interest": 0.2,
        "tolerance": (2.0, 4.0),
        "appeal": (0.2, 0.5),
    },
    "UI": {
        "fraction": 0.30,
        "noise": 1.5,
        "interest": 0.1,
        "tolerance": (0.8, 2.5),
        "appeal": (0.1, 0.4),
    },
}


def _allocate_archetype_counts(n_citizens: int) -> dict[str, int]:
    raw = {name: n_citizens * spec["fraction"] for name, spec in ARCHETYPES.items()}
    counts = {name: int(np.floor(value)) for name, value in raw.items()}
    remainder = n_citizens - sum(counts.values())
    order = sorted(raw, key=lambda name: raw[name] - counts[name], reverse=True)
    for name in order[:remainder]:
        counts[name] += 1
    return counts


def _specialties(n_dim: int, rng: np.random.Generator) -> tuple[int, ...]:
    n_specialties = int(rng.integers(1, min(2, n_dim) + 1))
    return tuple(int(x) for x in rng.choice(n_dim, n_specialties, replace=False))


def create_population(config: ModelConfig, rng: np.random.Generator) -> list[Agent]:
    """Create one population shared by every system within a run."""

    agents: list[Agent] = []
    next_id = 0
    for archetype, count in _allocate_archetype_counts(config.n_citizens).items():
        spec = ARCHETYPES[archetype]
        for _ in range(count):
            agents.append(
                Agent(
                    id=next_id,
                    agent_type="citizen",
                    archetype=archetype,
                    observation_noise=float(spec["noise"]),
                    appeal=float(rng.uniform(*spec["appeal"])),
                    bias=np.zeros(config.n_dim),
                    political_interest=float(spec["interest"]),
                    tolerance=float(rng.uniform(*spec["tolerance"])),
                    specialty_dims=_specialties(config.n_dim, rng),
                )
            )
            next_id += 1

    for _ in range(config.n_experts):
        agents.append(
            Agent(
                id=next_id,
                agent_type="expert",
                archetype="expert",
                observation_noise=config.expert_noise,
                appeal=float(rng.uniform(0.5, 0.8)),
                bias=np.zeros(config.n_dim),
                political_interest=1.0,
                tolerance=float(rng.uniform(3.0, 5.0)),
                specialty_dims=_specialties(config.n_dim, rng),
            )
        )
        next_id += 1

    for _ in range(config.n_demagogues):
        direction = rng.normal(size=config.n_dim)
        direction /= np.linalg.norm(direction)
        agents.append(
            Agent(
                id=next_id,
                agent_type="demagogue",
                archetype="demagogue",
                observation_noise=config.demagogue_noise,
                appeal=float(rng.uniform(0.8, 1.0)),
                bias=direction * config.demagogue_bias_norm,
                political_interest=1.0,
                tolerance=float(rng.uniform(0.3, 1.0)),
                specialty_dims=_specialties(config.n_dim, rng),
            )
        )
        next_id += 1

    return agents


class World:
    def __init__(self, config: ModelConfig, rng: np.random.Generator):
        self.config = config
        self.rng = rng
        self.theta_star = rng.normal(0.0, 0.5, size=config.n_dim)

    def update(self) -> None:
        if self.rng.random() < self.config.regime_change_prob:
            self.theta_star = self.rng.normal(0.0, 1.0, size=self.config.n_dim)
        else:
            self.theta_star = self.theta_star + self.rng.normal(
                0.0, self.config.drift_rate, size=self.config.n_dim
            )

    def evaluate(self, policy: np.ndarray) -> float:
        return -float(np.sum((policy - self.theta_star) ** 2))


def stable_softmax(values: np.ndarray) -> np.ndarray:
    shifted = np.asarray(values, dtype=float) - float(np.max(values))
    weights = np.exp(shifted)
    total = float(weights.sum())
    if not np.isfinite(total) or total <= 0:
        return np.full(len(values), 1.0 / len(values))
    return weights / total


def randomized_top_k(
    values: Sequence[float], k: int, rng: np.random.Generator
) -> np.ndarray:
    """Sort descending and break exact ties uniformly at random."""

    values_array = np.asarray(values, dtype=float)
    tie_breakers = rng.random(len(values_array))
    order = np.lexsort((tie_breakers, -values_array))
    return order[:k]


def bounded_confidence_deliberation(
    registered_predictions: np.ndarray,
    tolerances: np.ndarray,
    precision_scores: np.ndarray,
    revision_rate: float,
) -> np.ndarray:
    """Return local post-deliberation beliefs without mutating agents."""

    beliefs = np.asarray(registered_predictions, dtype=float)
    precision_weights = stable_softmax(precision_scores)
    post = beliefs.copy()
    for i in range(len(beliefs)):
        distances = np.linalg.norm(beliefs - beliefs[i], axis=1)
        neighbors = distances <= tolerances[i]
        neighbors[i] = True
        local_weights = precision_weights[neighbors]
        local_weights = local_weights / local_weights.sum()
        consensus = np.average(beliefs[neighbors], axis=0, weights=local_weights)
        post[i] = (1.0 - revision_rate) * beliefs[i] + revision_rate * consensus
    return post


class GovernanceSystem:
    def __init__(self, name: str, rng: np.random.Generator):
        self.name = name
        self.rng = rng
        self.council: np.ndarray = np.array([], dtype=int)
        self.expert_seats: np.ndarray = np.array([], dtype=int)

    def select_if_due(
        self, period: int, agents: Sequence[Agent], track_records: np.ndarray
    ) -> None:
        raise NotImplementedError

    def decide(
        self,
        raw_predictions: np.ndarray,
        agents: Sequence[Agent],
        track_records: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        selected = raw_predictions[self.council]
        return selected.mean(axis=0), selected.copy()

    def record_feedback(self, policy: np.ndarray, public_indicator: np.ndarray) -> None:
        del policy, public_indicator


class Autocracy(GovernanceSystem):
    def __init__(self, config: ModelConfig, rng: np.random.Generator):
        super().__init__(SYSTEM_AUTOCRACY, rng)
        self.cycle = config.autocracy_cycle

    def select_if_due(self, period, agents, track_records) -> None:
        del track_records
        if len(self.council) == 0 or period % self.cycle == 0:
            self.council = np.array([self.rng.integers(0, len(agents))], dtype=int)


class AppealBasedSelection(GovernanceSystem):
    """Candidate ranking by appeal plus noise; no voter aggregation."""

    def __init__(
        self,
        config: ModelConfig,
        rng: np.random.Generator,
        name: str = SYSTEM_APPEAL,
    ):
        super().__init__(name, rng)
        self.cycle = config.appeal_cycle
        self.council_size = config.appeal_council_size
        self.noise = config.appeal_ranking_noise

    def candidate_scores(self, agents: Sequence[Agent], track_records: np.ndarray) -> np.ndarray:
        del track_records
        return np.array([agent.appeal for agent in agents])

    def before_selection(self) -> None:
        pass

    def select_if_due(self, period, agents, track_records) -> None:
        if len(self.council) == 0 or period % self.cycle == 0:
            self.before_selection()
            scores = self.candidate_scores(agents, track_records)
            scores = scores + self.rng.normal(0.0, self.noise, size=len(agents))
            self.council = randomized_top_k(scores, self.council_size, self.rng)


class Sortition(GovernanceSystem):
    def __init__(
        self,
        config: ModelConfig,
        rng: np.random.Generator,
        deliberate: bool = False,
    ):
        name = SYSTEM_SORTITION_DELIBERATION if deliberate else SYSTEM_SORTITION
        super().__init__(name, rng)
        self.cycle = config.rotation_cycle
        self.size = config.sortition_size
        self.deliberate = deliberate
        self.revision_rate = config.revision_rate

    def select_if_due(self, period, agents, track_records) -> None:
        del track_records
        if len(self.council) == 0 or period % self.cycle == 0:
            self.council = self.rng.choice(len(agents), self.size, replace=False)

    def decide(self, raw_predictions, agents, track_records):
        selected = raw_predictions[self.council]
        if self.deliberate:
            post = bounded_confidence_deliberation(
                selected,
                np.array([agents[i].tolerance for i in self.council]),
                np.zeros(len(self.council)),
                self.revision_rate,
            )
        else:
            post = selected.copy()
        return post.mean(axis=0), post


class PhilosopherKingDemocracy(GovernanceSystem):
    def __init__(self, config: ModelConfig, rng: np.random.Generator):
        super().__init__(SYSTEM_PKD, rng)
        self.cycle = config.rotation_cycle
        self.n_expert = config.n_expert_seats
        self.n_citizen = config.n_citizen_seats
        self.deliberate = config.pkd_deliberation
        self.revision_rate = config.revision_rate

    def _stratified_seats(
        self, agents: Sequence[Agent], eligible: np.ndarray
    ) -> np.ndarray:
        pools: dict[tuple[int, str, str], list[int]] = {}
        for idx in eligible:
            agent = agents[int(idx)]
            key = (agent.primary_specialty, agent.archetype, agent.tolerance_bin)
            pools.setdefault(key, []).append(int(idx))

        keys = list(pools)
        if keys:
            keys = [keys[i] for i in self.rng.permutation(len(keys))]
        selected: list[int] = []
        for key in keys:
            if len(selected) >= self.n_citizen:
                break
            pool = pools[key]
            choice_position = int(self.rng.integers(0, len(pool)))
            selected.append(pool.pop(choice_position))

        while len(selected) < self.n_citizen:
            nonempty = [key for key, pool in pools.items() if pool]
            if not nonempty:
                break
            sizes = np.array([len(pools[key]) for key in nonempty])
            key = nonempty[int(randomized_top_k(sizes, 1, self.rng)[0])]
            pool = pools[key]
            selected.append(pool.pop(int(self.rng.integers(0, len(pool)))))
        return np.asarray(selected, dtype=int)

    def select_if_due(self, period, agents, track_records) -> None:
        if len(self.council) != 0 and period % self.cycle != 0:
            return
        self.expert_seats = randomized_top_k(track_records, self.n_expert, self.rng)
        expert_set = set(int(i) for i in self.expert_seats)
        eligible = np.array(
            [i for i in range(len(agents)) if i not in expert_set], dtype=int
        )
        citizen_seats = self._stratified_seats(agents, eligible)
        self.council = np.concatenate((self.expert_seats, citizen_seats))

    def decide(self, raw_predictions, agents, track_records):
        selected = raw_predictions[self.council]
        selected_scores = track_records[self.council]
        if self.deliberate:
            post = bounded_confidence_deliberation(
                selected,
                np.array([agents[i].tolerance for i in self.council]),
                selected_scores,
                self.revision_rate,
            )
        else:
            post = selected.copy()
        policy = np.average(post, axis=0, weights=stable_softmax(selected_scores))
        return policy, post


class CollectiveRetrospectiveAppeal(AppealBasedSelection):
    def __init__(self, config: ModelConfig, rng: np.random.Generator):
        super().__init__(config, rng, SYSTEM_RETROSPECTIVE)
        self.weight = float(config.retrospective_weight or 0.0)
        self.memory = config.retrospective_memory
        self.reputations = np.zeros(config.population_size)
        self.expected_outcome = 0.0
        self.term_outcomes: list[float] = []

    def before_selection(self) -> None:
        if len(self.council) == 0 or not self.term_outcomes:
            return
        outcome = float(np.mean(self.term_outcomes))
        surprise = outcome - self.expected_outcome
        self.reputations[self.council] = (
            self.memory * self.reputations[self.council]
            + (1.0 - self.memory) * surprise
        )
        self.expected_outcome = (
            self.memory * self.expected_outcome + (1.0 - self.memory) * outcome
        )
        self.term_outcomes.clear()

    def candidate_scores(self, agents, track_records):
        del track_records
        appeals = np.array([agent.appeal for agent in agents])
        return appeals + self.weight * self.reputations

    def record_feedback(self, policy, public_indicator) -> None:
        self.term_outcomes.append(-float(np.sum((policy - public_indicator) ** 2)))


class ScoreInformedAppeal(AppealBasedSelection):
    def __init__(self, config: ModelConfig, rng: np.random.Generator):
        super().__init__(config, rng, SYSTEM_SCORE_INFORMED)
        self.weight = float(config.score_informed_weight or 0.0)

    def candidate_scores(self, agents, track_records):
        appeals = np.array([agent.appeal for agent in agents])
        return appeals + self.weight * track_records


@dataclass
class PeriodRecord:
    run: int
    seed: int
    period: int
    system: str
    performance: float
    demagogue_fraction: float
    council_size: int
    expert_demagogue_fraction: float


@dataclass
class AgentRecord:
    run: int
    seed: int
    agent_id: int
    agent_type: str
    archetype: str
    observation_noise: float
    appeal: float
    tolerance: float
    track_record: float
    specialty_dims: str


@dataclass
class RunResult:
    run: int
    seed: int
    config: ModelConfig
    periods: list[PeriodRecord]
    agents: list[AgentRecord]
    raw_score_history: np.ndarray
    final_track_records: np.ndarray

    def system_periods(self, system: str) -> list[PeriodRecord]:
        return [record for record in self.periods if record.system == system]


def _make_systems(
    config: ModelConfig, seeds: Sequence[np.random.SeedSequence]
) -> list[GovernanceSystem]:
    generators = [np.random.default_rng(seed) for seed in seeds]
    systems: list[GovernanceSystem] = [
        Autocracy(config, generators[0]),
        AppealBasedSelection(config, generators[1]),
        Sortition(config, generators[2]),
        PhilosopherKingDemocracy(config, generators[3]),
    ]
    cursor = 4
    if config.include_sortition_deliberation:
        systems.append(Sortition(config, generators[cursor], deliberate=True))
        cursor += 1
    if config.retrospective_weight is not None:
        systems.append(CollectiveRetrospectiveAppeal(config, generators[cursor]))
        cursor += 1
    if config.score_informed_weight is not None:
        systems.append(ScoreInformedAppeal(config, generators[cursor]))
    return systems


def _apply_strategy(
    config: ModelConfig,
    raw_predictions: np.ndarray,
    agents: Sequence[Agent],
    pkd: PhilosopherKingDemocracy,
    previous_pkd_policy: np.ndarray | None,
    public_indicator: np.ndarray,
    previous_indicator: np.ndarray | None,
    rng: np.random.Generator,
) -> None:
    mode = config.strategic_mode
    if mode == "none":
        return
    demagogues = [i for i, agent in enumerate(agents) if agent.agent_type == "demagogue"]
    council = set(int(i) for i in pkd.council)
    if mode in {"independent_herding", "coordinated_herding"}:
        if previous_pkd_policy is None:
            return
        shared_noise = rng.normal(0.0, config.strategic_noise, size=config.n_dim)
        for idx in demagogues:
            if idx in council:
                continue
            noise = (
                shared_noise
                if mode == "coordinated_herding"
                else rng.normal(0.0, config.strategic_noise, size=config.n_dim)
            )
            raw_predictions[idx] = previous_pkd_policy + noise
    elif mode == "indicator_targeting":
        raw_predictions[demagogues] = public_indicator
    elif mode == "indicator_targeting_firewall" and previous_indicator is not None:
        raw_predictions[demagogues] = previous_indicator


def run_simulation(
    config: ModelConfig | None = None,
    *,
    seed: int = 42,
    run: int = 0,
) -> RunResult:
    """Run all configured systems on one shared world and observation stream."""

    config = config or ModelConfig()
    config.validate()
    root_seed = np.random.SeedSequence(seed)
    children = root_seed.spawn(16)
    world = World(config, np.random.default_rng(children[0]))
    agents = create_population(config, np.random.default_rng(children[1]))
    observation_rng = np.random.default_rng(children[2])
    proxy_rng = np.random.default_rng(children[3])
    strategy_rng = np.random.default_rng(children[4])
    systems = _make_systems(config, children[5:13])
    pkd = next(system for system in systems if isinstance(system, PhilosopherKingDemocracy))

    period_records: list[PeriodRecord] = []
    raw_score_history = np.empty((config.n_periods, len(agents)))
    feedback_queue: list[tuple[np.ndarray, np.ndarray]] = []
    previous_pkd_policy: np.ndarray | None = None
    previous_indicator: np.ndarray | None = None

    for period in range(config.n_periods):
        world.update()
        if period == config.shock_period:
            for agent in agents:
                if agent.agent_type == "demagogue":
                    agent.appeal = agent.appeal * config.shock_appeal_multiplier
                    agent.bias = agent.bias * config.shock_bias_multiplier

        raw_predictions = np.vstack(
            [
                agent.register_raw_prediction(world.theta_star, observation_rng)
                for agent in agents
            ]
        )
        public_indicator = world.theta_star + proxy_rng.normal(
            0.0, config.proxy_noise, size=config.n_dim
        )
        _apply_strategy(
            config,
            raw_predictions,
            agents,
            pkd,
            previous_pkd_policy,
            public_indicator,
            previous_indicator,
            strategy_rng,
        )
        registered_raw_predictions = raw_predictions.copy()
        track_records = np.array([agent.track_record for agent in agents])

        for system in systems:
            system.select_if_due(period, agents, track_records)
            policy, _post_deliberation_belief = system.decide(
                registered_raw_predictions, agents, track_records
            )
            performance = world.evaluate(policy)
            system.record_feedback(policy, public_indicator)
            council_types = [agents[int(i)].agent_type for i in system.council]
            demagogue_fraction = (
                council_types.count("demagogue") / len(council_types)
                if council_types
                else 0.0
            )
            expert_demagogue_fraction = 0.0
            if len(system.expert_seats):
                expert_types = [agents[int(i)].agent_type for i in system.expert_seats]
                expert_demagogue_fraction = expert_types.count("demagogue") / len(
                    expert_types
                )
            period_records.append(
                PeriodRecord(
                    run=run,
                    seed=seed,
                    period=period,
                    system=system.name,
                    performance=performance,
                    demagogue_fraction=demagogue_fraction,
                    council_size=len(system.council),
                    expert_demagogue_fraction=expert_demagogue_fraction,
                )
            )
            if system is pkd:
                previous_pkd_policy = policy.copy()

        scored_dims = config.scored_dimensions or config.n_dim
        scores_now = -np.sum(
            (registered_raw_predictions[:, :scored_dims] - public_indicator[:scored_dims])
            ** 2,
            axis=1,
        )
        raw_score_history[period] = scores_now
        feedback_queue.append((registered_raw_predictions.copy(), public_indicator.copy()))
        if len(feedback_queue) > config.feedback_delay:
            delayed_predictions, delayed_indicator = feedback_queue.pop(0)
            delayed_scores = -np.sum(
                (
                    delayed_predictions[:, :scored_dims]
                    - delayed_indicator[:scored_dims]
                )
                ** 2,
                axis=1,
            )
            scores_frozen = (
                config.freeze_scores_at is not None
                and period >= config.freeze_scores_at
            )
            if not scores_frozen:
                for agent, score in zip(agents, delayed_scores):
                    agent.track_record = (
                        config.track_decay * agent.track_record
                        + (1.0 - config.track_decay) * float(score)
                    )
        previous_indicator = public_indicator.copy()

    agent_records = [
        AgentRecord(
            run=run,
            seed=seed,
            agent_id=agent.id,
            agent_type=agent.agent_type,
            archetype=agent.archetype,
            observation_noise=agent.observation_noise,
            appeal=agent.appeal,
            tolerance=agent.tolerance,
            track_record=agent.track_record,
            specialty_dims=";".join(str(dim) for dim in agent.specialty_dims),
        )
        for agent in agents
    ]
    final_track_records = np.array([agent.track_record for agent in agents])
    return RunResult(
        run=run,
        seed=seed,
        config=config,
        periods=period_records,
        agents=agent_records,
        raw_score_history=raw_score_history,
        final_track_records=final_track_records,
    )


def run_ensemble(
    config: ModelConfig | None = None,
    *,
    n_runs: int = 30,
    base_seed: int = 20260301,
) -> list[RunResult]:
    config = config or ModelConfig()
    if n_runs <= 0:
        raise ValueError("n_runs must be positive")
    seed_sequence = np.random.SeedSequence(base_seed)
    run_seeds = [int(child.generate_state(1, dtype=np.uint32)[0]) for child in seed_sequence.spawn(n_runs)]
    return [
        run_simulation(config, seed=seed, run=index)
        for index, seed in enumerate(run_seeds)
    ]


def summarize_runs(results: Sequence[RunResult]) -> list[dict[str, Any]]:
    """Return unaggregated run-level rows for statistical analysis."""

    rows: list[dict[str, Any]] = []
    for result in results:
        systems = sorted({record.system for record in result.periods})
        for system in systems:
            records = result.system_periods(system)
            performances = np.array([record.performance for record in records])
            infiltrations = np.array([record.demagogue_fraction for record in records])
            shock = min(result.config.shock_period, len(performances))
            pre = performances[:shock]
            post = performances[shock:]
            rows.append(
                {
                    "run": result.run,
                    "seed": result.seed,
                    "system": system,
                    "mean_performance": float(performances.mean()),
                    "pre_shock_performance": float(pre.mean()) if len(pre) else "",
                    "post_shock_performance": float(post.mean()) if len(post) else "",
                    "post_minus_pre": (
                        float(post.mean() - pre.mean()) if len(pre) and len(post) else ""
                    ),
                    "mean_demagogue_fraction": float(infiltrations.mean()),
                }
            )
    return rows


def write_csv(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> None:
    rows = list(rows)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def export_run_data(results: Sequence[RunResult], output_dir: str | Path) -> None:
    """Write period, run, and final-agent data with an exact config snapshot."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        output_dir / "period_metrics.csv",
        (asdict(record) for result in results for record in result.periods),
    )
    write_csv(output_dir / "run_summary.csv", summarize_runs(results))
    write_csv(
        output_dir / "final_agent_state.csv",
        (asdict(agent) for result in results for agent in result.agents),
    )
    manifest = {
        "model": "simulation_pkd_v32.py",
        "score_source": "raw_prediction",
        "comparison_baseline": SYSTEM_APPEAL,
        "n_runs": len(results),
        "seeds": [result.seed for result in results],
        "config": asdict(results[0].config),
    }
    with (output_dir / "run_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/model_smoke.json")
    )
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--base-seed", type=int, default=20260301)
    parser.add_argument("--output", type=Path, default=Path("outputs/smoke"))
    args = parser.parse_args()
    selected_config = ModelConfig.from_json(args.config)
    selected_results = run_ensemble(
        selected_config, n_runs=args.runs, base_seed=args.base_seed
    )
    export_run_data(selected_results, args.output)
    for row in summarize_runs(selected_results):
        print(
            f"{row['system']}: mean={row['mean_performance']:.4f}, "
            f"demagogue_fraction={row['mean_demagogue_fraction']:.3f}"
        )
