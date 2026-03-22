"""
Philosopher-King Democracy (PKD) — Agent-Based Model Simulation
================================================================
A Data-Driven Deliberative Governance Architecture:
Comparing Track-Record Selection vs Electoral Democracy
Under Populist Perturbation

Author: Aruma Harada
Date: March 2026

This simulation compares four governance systems:
  1. Autocracy        — single random agent decides
  2. Electoral Democracy — citizens vote for representatives based on "appeal"
  3. Sortition Democracy — random citizen assembly, majority vote
  4. PKD (Philosopher-King Democracy) — track-record selection + deliberation

Key findings demonstrated:
  (1) PKD is structurally resistant to demagoguery/populism
  (2) Track-record selection converges to true experts faster than elections
  (3) Feedback loop enables long-term self-improvement
  (4) Deliberation (Bayesian belief revision) reduces collective error

Requirements: numpy, matplotlib, scipy
Usage: python simulation_pkd.py
"""

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from scipy import stats


# ══════════════════════════════════════════════
# 1. WORLD MODEL
# ══════════════════════════════════════════════

class World:
    """
    The "true state" of the world that governance systems try to track.

    θ*(t) ∈ ℝ^d represents the optimal policy vector at time t.
    It evolves via slow drift + occasional regime changes (structural breaks).

    Policy performance = -||chosen_policy - θ*||²
    (closer to θ* = better outcome)
    """

    def __init__(self, n_dim: int = 5, drift_rate: float = 0.02,
                 regime_change_prob: float = 0.03, seed: int = 42):
        self.n_dim = n_dim
        self.drift_rate = drift_rate
        self.regime_change_prob = regime_change_prob
        self.rng = np.random.default_rng(seed)
        self.theta_star = self.rng.standard_normal(n_dim) * 0.5
        self.t = 0

    def step(self):
        """Advance world state by one period."""
        self.t += 1
        # Slow drift
        self.theta_star += self.rng.standard_normal(self.n_dim) * self.drift_rate
        # Occasional regime change (structural break)
        if self.rng.random() < self.regime_change_prob:
            self.theta_star = self.rng.standard_normal(self.n_dim) * 0.5

    def evaluate_policy(self, policy: np.ndarray) -> float:
        """Returns performance score. Higher = better. Max = 0."""
        return -np.sum((policy - self.theta_star) ** 2)

    def get_noisy_signal(self, noise_std: float) -> np.ndarray:
        """Observe the true state with Gaussian noise."""
        return self.theta_star + self.rng.standard_normal(self.n_dim) * noise_std


# ══════════════════════════════════════════════
# 2. AGENT MODEL
# ══════════════════════════════════════════════

@dataclass(eq=False)
class Agent:
    """
    An agent who observes the world, forms beliefs, and proposes policies.

    Attributes:
        agent_type: "citizen", "expert", or "demagogue"
        expertise_std: noise level of observation (lower = more accurate)
        appeal: charisma score (used only in electoral systems)
        bias: systematic distortion of observation (demagogues have large bias)
        political_interest: 0.0-1.0 (engagement level)
        tolerance: per-agent bounded confidence ε (AOT/Openness proxy)
            High → listens to distant opinions (intellectually open)
            Low → only listens to similar opinions (dogmatic)
        archetype: Brennan category ("IC", "II", "UC", "UI") or "expert"/"demagogue"
        track_record: exponential moving average of prediction accuracy
        belief: current belief about θ*
        specialty_dims: dimensions where this agent has local knowledge
    """
    agent_type: str
    expertise_std: float
    appeal: float
    bias: np.ndarray
    political_interest: float = 0.5
    tolerance: float = 3.0
    archetype: str = ""  # IC, II, UC, UI, expert, demagogue
    track_record: float = 0.0
    belief: np.ndarray = None
    specialty_dims: list = field(default_factory=list)
    id: int = 0

    def observe(self, world: World) -> np.ndarray:
        """Get a noisy, potentially biased observation of the world."""
        signal = world.get_noisy_signal(self.expertise_std)
        # Specialists have lower noise in their specialty dimensions
        for dim in self.specialty_dims:
            signal[dim] = world.theta_star[dim] + \
                world.rng.standard_normal() * self.expertise_std * 0.3
        # Add systematic bias (demagogues distort reality)
        signal += self.bias
        self.belief = signal
        return signal

    def propose_policy(self) -> np.ndarray:
        """Propose a policy based on current belief."""
        return self.belief.copy()

    def update_track_record(self, score: float, decay: float = 0.9):
        """Exponential moving average of performance."""
        self.track_record = decay * self.track_record + (1 - decay) * score

    @property
    def tolerance_category(self) -> str:
        """Discretize tolerance for stratification pooling."""
        if self.tolerance >= 3.0:
            return "high_tol"
        elif self.tolerance >= 1.5:
            return "mid_tol"
        else:
            return "low_tol"


# ── Brennan's 4 citizen archetypes + tolerance distribution ──
#
#   Interested + Competent (IC): good signal, high tolerance, engaged
#   Interested + Incompetent (II): bad signal, low tolerance, dogmatic
#   Uninterested + Competent (UC): good signal, moderate tolerance, disengaged
#   Uninterested + Incompetent (UI): noise
#
# Tolerance distribution per archetype (measured via AOT scale in practice):
#   IC: mostly high tolerance (open-minded by nature)
#   II: mostly low tolerance (confident in wrong beliefs)
#   UC: spread across mid-high (open but passive)
#   UI: spread across low-mid (apathetic)

ARCHETYPES = {
    "IC": {  # Interested + Competent
        "fraction": 0.25,
        "expertise_std": 0.6,
        "political_interest": 0.9,
        "tolerance_range": (2.5, 5.0),
        "appeal_range": (0.4, 0.7),
    },
    "II": {  # Interested + Incompetent
        "fraction": 0.20,
        "expertise_std": 1.3,
        "political_interest": 0.9,
        "tolerance_range": (0.5, 1.8),
        "appeal_range": (0.5, 0.8),
    },
    "UC": {  # Uninterested + Competent
        "fraction": 0.25,
        "expertise_std": 0.5,
        "political_interest": 0.2,
        "tolerance_range": (2.0, 4.0),
        "appeal_range": (0.1, 0.3),
    },
    "UI": {  # Uninterested + Incompetent
        "fraction": 0.30,
        "expertise_std": 1.5,
        "political_interest": 0.1,
        "tolerance_range": (0.8, 2.5),
        "appeal_range": (0.1, 0.4),
    },
}


def create_population(n_citizens: int, n_experts: int, n_demagogues: int,
                      n_dim: int, rng: np.random.Generator) -> List[Agent]:
    """
    Create a heterogeneous population using Brennan's 4-type model.

    Citizens are distributed across 4 archetypes (IC, II, UC, UI),
    each with characteristic expertise, tolerance (AOT), political
    interest, and appeal distributions. This produces realistic
    heterogeneity for stratified sortition.
    """
    agents = []
    agent_id = 0

    # ── Citizens: 4 Brennan archetypes ──
    for arch_name, arch in ARCHETYPES.items():
        n_this = int(n_citizens * arch["fraction"])
        for _ in range(n_this):
            specialty = rng.choice(n_dim, size=rng.integers(1, 3), replace=False).tolist()
            tol = rng.uniform(*arch["tolerance_range"])
            agents.append(Agent(
                agent_type="citizen",
                expertise_std=arch["expertise_std"],
                appeal=rng.uniform(*arch["appeal_range"]),
                bias=np.zeros(n_dim),
                political_interest=arch["political_interest"],
                tolerance=tol,
                archetype=arch_name,
                specialty_dims=specialty,
                id=agent_id,
            ))
            agent_id += 1

    # ── Experts: low noise, high tolerance, low appeal ──
    for _ in range(n_experts):
        agents.append(Agent(
            agent_type="expert",
            expertise_std=0.3,
            appeal=rng.uniform(0.1, 0.4),
            bias=np.zeros(n_dim),
            political_interest=0.7,
            tolerance=rng.uniform(3.0, 5.0),
            archetype="expert",
            id=agent_id,
        ))
        agent_id += 1

    # ── Demagogues: biased, high appeal, low tolerance ──
    for _ in range(n_demagogues):
        bias_direction = rng.standard_normal(n_dim)
        bias_direction = bias_direction / np.linalg.norm(bias_direction) * 1.5
        agents.append(Agent(
            agent_type="demagogue",
            expertise_std=0.8,
            appeal=rng.uniform(0.8, 1.0),
            bias=bias_direction,
            political_interest=1.0,
            tolerance=rng.uniform(0.3, 1.0),  # Very dogmatic
            archetype="demagogue",
            id=agent_id,
        ))
        agent_id += 1

    return agents


# ══════════════════════════════════════════════
# 3. DELIBERATION MECHANISM
# ══════════════════════════════════════════════

def deliberate(participants: List[Agent], weights: np.ndarray = None,
               epsilon: float = None, revision_rate: float = 0.6) -> np.ndarray:
    """
    Per-Agent Bounded-Confidence Deliberation.

    Each agent i has their own tolerance ε_i (from AOT/personality).
    Agent i only revises toward agent j if ||belief_i - belief_j|| ≤ ε_i.

    This means:
    - High-tolerance agents (IC type) integrate diverse views → better signal
    - Low-tolerance agents (II type) form echo chambers → amplify own error
    - The SAME council produces different outcomes depending on composition

    If epsilon is provided, it overrides per-agent tolerance (for backwards compat).
    """
    beliefs = np.array([a.belief for a in participants])
    n = len(participants)

    if weights is None:
        raw_weights = np.ones(n)
    else:
        raw_weights = np.exp(weights - np.max(weights))

    # Per-agent tolerance
    if epsilon is not None:
        tolerances = np.full(n, epsilon)
    else:
        tolerances = np.array([a.tolerance for a in participants])

    # --- Per-agent bounded-confidence belief revision ---
    new_beliefs = beliefs.copy()
    for i in range(n):
        distances = np.linalg.norm(beliefs - beliefs[i], axis=1)
        neighbors = distances <= tolerances[i]
        neighbors[i] = True

        if neighbors.sum() <= 1:
            continue

        neighbor_weights = raw_weights[neighbors].copy()
        neighbor_weights /= neighbor_weights.sum()
        local_consensus = np.average(beliefs[neighbors], axis=0, weights=neighbor_weights)

        new_beliefs[i] = (1 - revision_rate) * beliefs[i] + revision_rate * local_consensus

    for i, agent in enumerate(participants):
        agent.belief = new_beliefs[i]

    global_weights = raw_weights / raw_weights.sum()
    policy = np.average(new_beliefs, axis=0, weights=global_weights)
    return policy


# ══════════════════════════════════════════════
# 4. GOVERNANCE SYSTEMS
# ══════════════════════════════════════════════

class GovernanceSystem:
    """Base class for governance systems."""

    def __init__(self, name: str):
        self.name = name
        self.performance_history = []

    def select_and_decide(self, world: World, population: List[Agent]) -> np.ndarray:
        raise NotImplementedError

    def step(self, world: World, population: List[Agent]):
        # Everyone observes the world
        for agent in population:
            agent.observe(world)
        # System makes a decision
        policy = self.select_and_decide(world, population)
        # Evaluate
        score = world.evaluate_policy(policy)
        self.performance_history.append(score)
        return score


class Autocracy(GovernanceSystem):
    """Single randomly-chosen agent decides. No accountability."""

    def __init__(self, rng: np.random.Generator):
        super().__init__("Autocracy")
        self.rng = rng
        self.ruler_idx = None

    def select_and_decide(self, world, population):
        if self.ruler_idx is None or world.t % 48 == 0:  # Change every 48 periods
            self.ruler_idx = self.rng.integers(0, len(population))
        return population[self.ruler_idx].propose_policy()


class ElectoralDemocracy(GovernanceSystem):
    """
    Citizens vote for representatives based on APPEAL (charisma).
    Vulnerable to demagogues who have high appeal but biased beliefs.
    Election every 12 periods. Council of 5 decides by majority.
    """

    def __init__(self, rng: np.random.Generator, council_size: int = 5,
                 election_cycle: int = 12):
        super().__init__("Electoral Democracy")
        self.rng = rng
        self.council_size = council_size
        self.election_cycle = election_cycle
        self.council: List[Agent] = []

    def _run_election(self, population: List[Agent]):
        """
        Citizens vote for candidates. Vote probability ∝ appeal + noise.
        This is the structural vulnerability: demagogues win elections
        because appeal ≠ competence.
        """
        candidates = population  # Everyone can run
        # Voting: probability proportional to appeal (with noise)
        appeals = np.array([a.appeal for a in candidates])
        # Add noise to simulate bounded rationality of voters
        vote_scores = appeals + self.rng.standard_normal(len(candidates)) * 0.2
        # Top council_size candidates win
        winners_idx = np.argsort(vote_scores)[-self.council_size:]
        self.council = [candidates[i] for i in winners_idx]

    def select_and_decide(self, world, population):
        if world.t % self.election_cycle == 1 or not self.council:
            self._run_election(population)
        # Council decides by averaging proposals (no deliberation weighting)
        proposals = np.array([a.propose_policy() for a in self.council])
        return proposals.mean(axis=0)


class SortitionDemocracy(GovernanceSystem):
    """
    Random citizen assembly. No expertise weighting.
    Resistant to demagoguery (random selection ignores appeal)
    but lacks expertise concentration.
    """

    def __init__(self, rng: np.random.Generator, assembly_size: int = 10,
                 rotation_cycle: int = 6):
        super().__init__("Sortition Democracy")
        self.rng = rng
        self.assembly_size = assembly_size
        self.rotation_cycle = rotation_cycle
        self.assembly: List[Agent] = []

    def select_and_decide(self, world, population):
        if world.t % self.rotation_cycle == 1 or not self.assembly:
            idx = self.rng.choice(len(population), size=self.assembly_size, replace=False)
            self.assembly = [population[i] for i in idx]
        # Simple average (no track-record weighting)
        proposals = np.array([a.propose_policy() for a in self.assembly])
        return proposals.mean(axis=0)


class PhilosopherKingDemocracy(GovernanceSystem):
    """
    The PKD system: track-record selection + stratified lottery + deliberation.

    Key mechanisms:
    1. Expert seats: filled by top track-record holders (no election)
    2. Citizen seats: stratified random lottery from specialty pools
       (Van Reybrouck-style: proportional representation across domains)
    3. Deliberation: bounded-confidence Bayesian belief revision
       (Hegselmann-Krause: only listen to nearby opinions)
    4. Feedback: policy outcomes update everyone's track record
    """

    def __init__(self, rng: np.random.Generator,
                 n_expert_seats: int = 5, n_citizen_seats: int = 5,
                 rotation_cycle: int = 6, n_dim: int = 5):
        super().__init__("PKD (Philosopher-King)")
        self.rng = rng
        self.n_expert_seats = n_expert_seats
        self.n_citizen_seats = n_citizen_seats
        self.rotation_cycle = rotation_cycle
        self.n_dim = n_dim
        self.council: List[Agent] = []

    def _select_council(self, population: List[Agent]):
        """
        3-Axis Stratified Sortition + Track-Record Expert Selection.

        Expert seats: top track records (meritocratic, appeal-blind).
        Citizen seats: stratified across 3 axes to ensure diversity:
          Axis 1: Specialty dimension (domain knowledge)
          Axis 2: Archetype (Brennan's IC/II/UC/UI)
          Axis 3: Tolerance category (high/mid/low, measured via AOT)

        The stratification prevents pathological councils:
          - All IC → groupthink among the "good" type
          - All II → echo chamber of confident incompetents
          - All one specialty → blind to other policy dimensions
          - All low tolerance → no belief revision occurs
        """
        # === Expert seats: top track records ===
        sorted_by_record = sorted(population, key=lambda a: a.track_record, reverse=True)
        expert_seats = sorted_by_record[:self.n_expert_seats]
        expert_set = set(id(a) for a in expert_seats)

        # === Citizen seats: 3-axis stratified sortition ===
        remaining = [a for a in population if id(a) not in expert_set]

        # Build stratification pools: (specialty_dim, archetype, tolerance_cat) → [agents]
        pools = {}
        for agent in remaining:
            if not agent.specialty_dims:
                dim_key = "none"
            else:
                dim_key = agent.specialty_dims[0]
            tol_key = agent.tolerance_category
            arch_key = agent.archetype if agent.archetype else "other"
            pool_key = (dim_key, arch_key, tol_key)
            pools.setdefault(pool_key, []).append(agent)

        # Strategy: pick 1 from each non-empty pool (round-robin) until seats filled
        citizen_seats = []
        pool_keys = list(pools.keys())
        # Shuffle pool order for fairness
        perm = self.rng.permutation(len(pool_keys))
        pool_keys = [pool_keys[i] for i in perm]

        # Round 1: one from each pool
        for key in pool_keys:
            if len(citizen_seats) >= self.n_citizen_seats:
                break
            pool = pools[key]
            if pool:
                idx = self.rng.integers(0, len(pool))
                chosen = pool.pop(idx)
                citizen_seats.append(chosen)

        # Round 2: if still need more, pick from largest remaining pools
        if len(citizen_seats) < self.n_citizen_seats:
            already = set(id(a) for a in citizen_seats)
            leftovers = [a for a in remaining if id(a) not in already]
            n_still = self.n_citizen_seats - len(citizen_seats)
            if leftovers and n_still > 0:
                idx = self.rng.choice(len(leftovers),
                                      size=min(n_still, len(leftovers)), replace=False)
                citizen_seats.extend([leftovers[i] for i in idx])

        self.council = expert_seats + citizen_seats

    def select_and_decide(self, world, population):
        if world.t % self.rotation_cycle == 1 or not self.council:
            self._select_council(population)

        # Deliberation with track-record weighting + per-agent tolerance
        weights = np.array([a.track_record for a in self.council])
        policy = deliberate(self.council, weights)  # uses each agent's own ε
        return policy

    def post_step_feedback(self, world: World, population: List[Agent], score: float):
        """
        Update track records for ALL agents based on how close
        their beliefs were to the true optimal policy.
        This is the self-improvement feedback loop.
        """
        for agent in population:
            if agent.belief is not None:
                individual_score = -np.sum((agent.belief - world.theta_star) ** 2)
                agent.update_track_record(individual_score)


# ══════════════════════════════════════════════
# 5. SIMULATION ENGINE
# ══════════════════════════════════════════════

def run_simulation(
    n_periods: int = 300,
    n_citizens: int = 80,
    n_experts: int = 15,
    n_demagogues: int = 5,
    n_dim: int = 5,
    seed: int = 42,
    demagogue_injection_period: int = 100,
) -> Dict:
    """
    Run a full comparative simulation.

    demagogue_injection_period: at this period, demagogues become more
    aggressive (appeal increases, bias increases) to simulate a populist wave.
    """
    rng = np.random.default_rng(seed)
    world = World(n_dim=n_dim, seed=seed)
    population = create_population(n_citizens, n_experts, n_demagogues, n_dim, rng)

    systems = {
        "Autocracy": Autocracy(rng),
        "Electoral Democracy": ElectoralDemocracy(rng),
        "Sortition Democracy": SortitionDemocracy(rng),
        "PKD": PhilosopherKingDemocracy(rng, n_dim=n_dim),
    }

    # Track demagogue infiltration rate
    demagogue_in_council = {name: [] for name in systems}
    # Track average track record of council members
    council_expertise = {name: [] for name in systems}

    for t in range(n_periods):
        world.step()

        # === Populist wave injection ===
        if t == demagogue_injection_period:
            for agent in population:
                if agent.agent_type == "demagogue":
                    agent.appeal = min(agent.appeal * 1.5, 1.0)
                    agent.bias *= 2.0

        # Run each governance system
        for name, system in systems.items():
            score = system.step(world, population)

            # PKD-specific: update all track records via feedback loop
            if isinstance(system, PhilosopherKingDemocracy):
                system.post_step_feedback(world, population, score)

            # Measure demagogue infiltration
            if hasattr(system, 'council') and system.council:
                n_demagogues_in = sum(1 for a in system.council if a.agent_type == "demagogue")
                demagogue_in_council[name].append(n_demagogues_in / len(system.council))
                avg_expertise = np.mean([-a.expertise_std for a in system.council])
                council_expertise[name].append(avg_expertise)
            else:
                demagogue_in_council[name].append(0)
                council_expertise[name].append(0)

    return {
        "systems": systems,
        "world": world,
        "population": population,
        "demagogue_rates": demagogue_in_council,
        "council_expertise": council_expertise,
        "n_periods": n_periods,
        "injection_period": demagogue_injection_period,
    }


# ══════════════════════════════════════════════
# 6. ROBUSTNESS: MONTE CARLO ENSEMBLE
# ══════════════════════════════════════════════

def run_ensemble(n_runs: int = 50, n_periods: int = 300, **kwargs) -> Dict:
    """
    Run multiple simulations with different seeds for statistical robustness.
    Returns mean ± SE performance trajectories.
    """
    all_results = {name: [] for name in
                   ["Autocracy", "Electoral Democracy", "Sortition Democracy", "PKD"]}
    all_demagogue_rates = {name: [] for name in all_results}

    for run in range(n_runs):
        result = run_simulation(n_periods=n_periods, seed=run * 137, **kwargs)
        for name, system in result["systems"].items():
            all_results[name].append(system.performance_history)
            all_demagogue_rates[name].append(result["demagogue_rates"][name])

        if (run + 1) % 10 == 0:
            print(f"  Ensemble run {run + 1}/{n_runs} complete")

    # Compute statistics
    ensemble_stats = {}
    for name in all_results:
        arr = np.array(all_results[name])
        dem_arr = np.array(all_demagogue_rates[name])
        ensemble_stats[name] = {
            "mean": arr.mean(axis=0),
            "se": arr.std(axis=0) / np.sqrt(n_runs),
            "demagogue_mean": dem_arr.mean(axis=0),
            "demagogue_se": dem_arr.std(axis=0) / np.sqrt(n_runs),
            "cumulative_mean": np.cumsum(arr, axis=1).mean(axis=0),
        }

    return ensemble_stats


# ══════════════════════════════════════════════
# 7. VISUALIZATION
# ══════════════════════════════════════════════

COLORS = {
    "Autocracy": "#95a5a6",
    "Electoral Democracy": "#e74c3c",
    "Sortition Democracy": "#3498db",
    "PKD": "#2ecc71",
}

LABELS_JP = {
    "Autocracy": "独裁制",
    "Electoral Democracy": "選挙制民主主義",
    "Sortition Democracy": "抽選制民主主義",
    "PKD": "哲人王民主制 (PKD)",
}


def plot_single_run(result: Dict, save_path: str = None):
    """Plot results from a single simulation run."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        "Philosopher-King Democracy: Single Run Comparison\n"
        "Governance Performance Under Populist Perturbation",
        fontsize=14, fontweight="bold"
    )

    injection = result["injection_period"]

    # (1) Performance over time (smoothed)
    ax = axes[0, 0]
    window = 20
    for name, system in result["systems"].items():
        perf = np.array(system.performance_history)
        smoothed = np.convolve(perf, np.ones(window) / window, mode="valid")
        ax.plot(smoothed, color=COLORS[name], lw=2, label=name, alpha=0.9)
    ax.axvline(injection, color="red", ls="--", alpha=0.5, label="Populist wave")
    ax.set_xlabel("Period")
    ax.set_ylabel("Policy Performance (higher = better)")
    ax.set_title("(A) Policy Performance Over Time")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.2)

    # (2) Cumulative performance
    ax = axes[0, 1]
    for name, system in result["systems"].items():
        cumsum = np.cumsum(system.performance_history)
        ax.plot(cumsum, color=COLORS[name], lw=2, label=name)
    ax.axvline(injection, color="red", ls="--", alpha=0.5)
    ax.set_xlabel("Period")
    ax.set_ylabel("Cumulative Performance")
    ax.set_title("(B) Cumulative Performance (Long-Term)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.2)

    # (3) Demagogue infiltration rate
    ax = axes[1, 0]
    for name in result["demagogue_rates"]:
        rates = result["demagogue_rates"][name]
        if len(rates) > 0:
            smoothed = np.convolve(rates, np.ones(window) / window, mode="valid")
            ax.plot(smoothed, color=COLORS[name], lw=2, label=name)
    ax.axvline(injection, color="red", ls="--", alpha=0.5, label="Populist wave")
    ax.set_xlabel("Period")
    ax.set_ylabel("Fraction of Demagogues in Council")
    ax.set_title("(C) Demagogue Infiltration Rate")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.2)
    ax.set_ylim(-0.05, 1.05)

    # (4) Track record distribution at end
    ax = axes[1, 1]
    for atype, color in [("citizen", "#3498db"), ("expert", "#2ecc71"), ("demagogue", "#e74c3c")]:
        records = [a.track_record for a in result["population"] if a.agent_type == atype]
        if records:
            ax.hist(records, bins=20, alpha=0.5, color=color, label=atype, density=True)
    ax.set_xlabel("Track Record Score")
    ax.set_ylabel("Density")
    ax.set_title("(D) Track Record Distribution by Agent Type")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"✅ Saved: {save_path}")
    plt.show()


def plot_ensemble(stats: Dict, n_periods: int = 300,
                  injection_period: int = 100, save_path: str = None):
    """Plot ensemble (Monte Carlo) results with confidence bands."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))
    fig.suptitle(
        "Philosopher-King Democracy: Monte Carlo Ensemble (n=50 runs)\n"
        "Mean ± SE Across Random Seeds",
        fontsize=13, fontweight="bold"
    )

    t = np.arange(n_periods)
    window = 20

    # (1) Smoothed mean performance ± SE
    ax = axes[0]
    for name in stats:
        mean = np.convolve(stats[name]["mean"], np.ones(window) / window, mode="valid")
        se = np.convolve(stats[name]["se"], np.ones(window) / window, mode="valid")
        t_smooth = np.arange(len(mean))
        ax.plot(t_smooth, mean, color=COLORS[name], lw=2, label=name)
        ax.fill_between(t_smooth, mean - 2 * se, mean + 2 * se,
                        color=COLORS[name], alpha=0.15)
    ax.axvline(injection_period, color="red", ls="--", alpha=0.5, label="Populist wave")
    ax.set_xlabel("Period")
    ax.set_ylabel("Policy Performance")
    ax.set_title("(A) Performance (Mean ± 2SE)")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.2)

    # (2) Cumulative performance
    ax = axes[1]
    for name in stats:
        ax.plot(t, stats[name]["cumulative_mean"], color=COLORS[name], lw=2, label=name)
    ax.axvline(injection_period, color="red", ls="--", alpha=0.5)
    ax.set_xlabel("Period")
    ax.set_ylabel("Cumulative Performance")
    ax.set_title("(B) Cumulative Performance")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.2)

    # (3) Demagogue infiltration
    ax = axes[2]
    for name in stats:
        mean = np.convolve(stats[name]["demagogue_mean"],
                           np.ones(window) / window, mode="valid")
        se = np.convolve(stats[name]["demagogue_se"],
                         np.ones(window) / window, mode="valid")
        t_smooth = np.arange(len(mean))
        ax.plot(t_smooth, mean, color=COLORS[name], lw=2, label=name)
        ax.fill_between(t_smooth, mean - 2 * se, mean + 2 * se,
                        color=COLORS[name], alpha=0.15)
    ax.axvline(injection_period, color="red", ls="--", alpha=0.5, label="Populist wave")
    ax.set_xlabel("Period")
    ax.set_ylabel("Demagogue Fraction in Council")
    ax.set_title("(C) Populism Resistance")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.2)
    ax.set_ylim(-0.05, 0.8)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"✅ Saved: {save_path}")
    plt.show()


def print_summary_statistics(stats: Dict, n_periods: int, injection_period: int):
    """Print publication-ready summary statistics."""
    print("\n" + "=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)

    # Pre- vs post-populist wave performance
    for name in stats:
        pre = stats[name]["mean"][:injection_period]
        post = stats[name]["mean"][injection_period:]
        total = stats[name]["mean"]

        print(f"\n{name}:")
        print(f"  Overall mean performance:     {total.mean():.3f} ± {total.std():.3f}")
        print(f"  Pre-populist wave (t<{injection_period}):  {pre.mean():.3f}")
        print(f"  Post-populist wave (t≥{injection_period}): {post.mean():.3f}")
        print(f"  Performance drop:             {post.mean() - pre.mean():.3f}"
              f"  ({'degraded' if post.mean() < pre.mean() else 'improved/stable'})")
        print(f"  Final cumulative:             {stats[name]['cumulative_mean'][-1]:.1f}")

    # Pairwise comparison: PKD vs Electoral
    print("\n" + "-" * 70)
    pkd_mean = stats["PKD"]["mean"].mean()
    elec_mean = stats["Electoral Democracy"]["mean"].mean()
    diff = pkd_mean - elec_mean
    print(f"PKD vs Electoral Democracy: Δ = {diff:.3f} "
          f"({'PKD superior' if diff > 0 else 'Electoral superior'})")

    # Post-wave demagogue infiltration
    print("\n--- Demagogue Infiltration (post-wave mean) ---")
    for name in stats:
        post_dem = stats[name]["demagogue_mean"][injection_period:]
        print(f"  {name:30s}: {post_dem.mean():.3f}")


# ══════════════════════════════════════════════
# 8. MAIN
# ══════════════════════════════════════════════

if __name__ == "__main__":
    import os
    os.makedirs("figures", exist_ok=True)

    print("=" * 60)
    print("Philosopher-King Democracy — Agent-Based Model")
    print("Comparative Governance Simulation")
    print("=" * 60)

    # --- Single run (detailed view) ---
    print("\n[1/3] Running single simulation (300 periods)...")
    result = run_simulation(n_periods=300, seed=42)
    plot_single_run(result, save_path="figures/pkd_single_run.png")

    # --- Monte Carlo ensemble (statistical robustness) ---
    print("\n[2/3] Running Monte Carlo ensemble (50 runs × 300 periods)...")
    ensemble = run_ensemble(n_runs=50, n_periods=300)
    plot_ensemble(ensemble, save_path="figures/pkd_ensemble.png")

    # --- Summary statistics ---
    print("\n[3/3] Computing summary statistics...")
    print_summary_statistics(ensemble, n_periods=300, injection_period=100)

    print("\n✅ Simulation complete. Figures saved to figures/")
