import numpy as np
from simulation_pkd_v32 import (
    ModelConfig, create_population, VoterAggregatedElection,
    PhilosopherKingDemocracy, bounded_confidence_deliberation,
    stable_softmax, run_simulation, SYSTEM_RETROSPECTIVE,
)


def test_tied_ballots_do_not_select_last_agent_block():
    config = ModelConfig(electoral_record_weight=1, electoral_information_noise=0,
                         electoral_media_amplification=0, electoral_random_utility_noise=0)
    agents = create_population(config, np.random.default_rng(3))
    election = VoterAggregatedElection(config, np.random.default_rng(4))
    election.select_if_due(0, agents, np.zeros(len(agents)))
    votes = np.array([r['votes'] for r in election.election_rows])
    assert votes.sum() == len(agents) * config.electoral_ballot_size
    assert np.count_nonzero(votes) > 50
    assert votes.max() < len(agents)


def test_optional_system_rng_is_stable():
    config = ModelConfig(n_periods=15, retrospective_weight=1)
    a = run_simulation(config, seed=8)
    b = run_simulation(config.with_updates(include_sortition_deliberation=True), seed=8)
    assert a.system_periods(SYSTEM_RETROSPECTIVE) == b.system_periods(SYSTEM_RETROSPECTIVE)


def test_local_deliberation_underflow_and_consensus_identity():
    beliefs = np.array([[0.], [1.], [100.]])
    scores = np.array([-2000., -2001., 0.])
    local = bounded_confidence_deliberation(beliefs, np.array([2., 2., .1]), scores, .3)
    assert np.isfinite(local).all()
    complete = bounded_confidence_deliberation(beliefs, np.full(3, 200.), scores, .3)
    weights = stable_softmax(scores)
    assert np.allclose(weights @ complete, weights @ beliefs)


def test_lottery_has_no_perfect_type_screening_by_default():
    config = ModelConfig(n_expert_seats=0, n_citizen_seats=100)
    agents = create_population(config, np.random.default_rng(2))
    pkd = PhilosopherKingDemocracy(config, np.random.default_rng(7))
    pkd.select_if_due(0, agents, np.zeros(100))
    assert set(pkd.citizen_seats) == set(range(100))
    assert any(agents[i].agent_type == 'demagogue' for i in pkd.citizen_seats)


def test_clean_record_ballot_recovers_top_score_candidates():
    config = ModelConfig(electoral_record_weight=1, electoral_information_noise=0,
                         electoral_media_amplification=0, electoral_random_utility_noise=0)
    agents = create_population(config, np.random.default_rng(3))
    election = VoterAggregatedElection(config, np.random.default_rng(4))
    election.select_if_due(0, agents, np.arange(len(agents), dtype=float))
    assert set(election.council) == set(range(95, 100))
