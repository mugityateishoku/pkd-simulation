import numpy as np

from simulation_pkd_v32 import (
    BASELINE_SYSTEMS,
    ModelConfig,
    SYSTEM_ELECTION,
    SYSTEM_PKD,
    run_simulation,
)


def _performance(result, system):
    return np.array(
        [record.performance for record in result.periods if record.system == system]
    )


def test_same_seed_is_bitwise_deterministic():
    config = ModelConfig(n_periods=18, shock_period=7)
    first = run_simulation(config, seed=123)
    second = run_simulation(config, seed=123)
    assert np.array_equal(first.raw_score_history, second.raw_score_history)
    assert np.array_equal(first.final_track_records, second.final_track_records)
    assert [record.votes for record in first.election_records] == [
        record.votes for record in second.election_records
    ]
    for system in BASELINE_SYSTEMS:
        assert np.array_equal(_performance(first, system), _performance(second, system))


def test_track_records_use_registered_predictions_not_deliberated_beliefs():
    base = ModelConfig(n_periods=24, shock_period=10, pkd_deliberation=True)
    without_deliberation = base.with_updates(pkd_deliberation=False)
    deliberated = run_simulation(base, seed=77)
    not_deliberated = run_simulation(without_deliberation, seed=77)
    assert np.array_equal(deliberated.raw_score_history, not_deliberated.raw_score_history)
    assert np.array_equal(
        deliberated.final_track_records, not_deliberated.final_track_records
    )


def test_one_period_updates_each_score_exactly_once():
    config = ModelConfig(n_periods=1, shock_period=99, track_decay=0.9)
    result = run_simulation(config, seed=9)
    assert np.allclose(result.final_track_records, 0.1 * result.raw_score_history[0])


def test_adding_a_comparison_system_does_not_change_baselines():
    base = ModelConfig(n_periods=18, shock_period=7)
    extended = base.with_updates(include_sortition_deliberation=True)
    first = run_simulation(base, seed=31)
    second = run_simulation(extended, seed=31)
    for system in BASELINE_SYSTEMS:
        assert np.array_equal(_performance(first, system), _performance(second, system))
    assert np.array_equal(first.final_track_records, second.final_track_records)


def test_infiltration_is_measured_for_every_system():
    config = ModelConfig(
        n_periods=3,
        n_citizens=10,
        n_experts=0,
        n_demagogues=10,
        n_expert_seats=5,
        n_citizen_seats=5,
        sortition_size=10,
        appeal_council_size=5,
        shock_period=99,
    )
    result = run_simulation(config, seed=4)
    by_system = {system: [] for system in BASELINE_SYSTEMS}
    for record in result.periods:
        by_system[record.system].append(record.demagogue_fraction)
    assert set(by_system) == set(BASELINE_SYSTEMS)
    for values in by_system.values():
        assert values and all(0.0 <= value <= 1.0 for value in values)


def test_baseline_name_does_not_claim_voter_aggregation():
    config = ModelConfig(n_periods=2, shock_period=99)
    result = run_simulation(config, seed=1)
    names = {record.system for record in result.periods}
    assert not any("Electoral Democracy" in name for name in names)
    assert SYSTEM_PKD in names


def test_pkd_citizen_seats_exclude_experts_and_demagogues():
    config = ModelConfig(n_periods=18, shock_period=7, citizen_pool="citizens_only")
    result = run_simulation(config, seed=22)
    pkd_records = [record for record in result.periods if record.system == SYSTEM_PKD]
    assert pkd_records
    assert all(record.citizen_seat_non_citizen_fraction == 0.0 for record in pkd_records)


def test_representation_diagnostics_are_bounded():
    result = run_simulation(ModelConfig(n_periods=5, shock_period=99), seed=14)
    for record in result.periods:
        assert 0.0 <= record.represented_population_share <= 1.0
        assert 0.0 <= record.representation_js_divergence <= 1.0
        assert 0.0 <= record.representation_total_variation <= 1.0


def test_shock_pair_has_identical_pre_shock_random_streams():
    shocked_config = ModelConfig(n_periods=18, shock_period=7, shock_enabled=True)
    no_shock_config = shocked_config.with_updates(shock_enabled=False)
    shocked = run_simulation(shocked_config, seed=101)
    no_shock = run_simulation(no_shock_config, seed=101)
    assert np.array_equal(
        shocked.raw_score_history[: shocked_config.shock_period],
        no_shock.raw_score_history[: shocked_config.shock_period],
    )
    shocked_appeal = np.array([agent.appeal for agent in shocked.agents])
    no_shock_appeal = np.array([agent.appeal for agent in no_shock.agents])
    non_demagogues = np.array(
        [agent.agent_type != "demagogue" for agent in shocked.agents]
    )
    demagogues = ~non_demagogues
    assert np.array_equal(shocked_appeal[non_demagogues], no_shock_appeal[non_demagogues])
    assert np.allclose(
        shocked_appeal[demagogues],
        no_shock_appeal[demagogues] * shocked_config.shock_appeal_multiplier,
    )


def test_voter_aggregated_election_records_vote_outcomes():
    config = ModelConfig(n_periods=13, shock_period=99, election_cycle=6)
    result = run_simulation(config, seed=55)
    records = [record for record in result.periods if record.system == SYSTEM_ELECTION]
    assert len(records) == config.n_periods
    assert all(record.council_size == config.election_council_size for record in records)
    assert all(0.0 <= record.electoral_demagogue_vote_share <= 1.0 for record in records)
    assert all(0.0 < record.electoral_max_candidate_vote_share <= 1.0 for record in records)
    election_count = 1 + (config.n_periods - 1) // config.election_cycle
    assert len(result.election_records) == election_count * config.population_size
    assert all(record.votes >= 0 for record in result.election_records)


def test_changing_voter_information_does_not_change_pkd_or_registered_scores():
    base = ModelConfig(n_periods=18, shock_period=7, electoral_record_weight=0.0)
    informed = base.with_updates(
        electoral_record_weight=1.0,
        electoral_information_noise=0.0,
        electoral_media_amplification=0.0,
    )
    first = run_simulation(base, seed=303)
    second = run_simulation(informed, seed=303)
    assert np.array_equal(first.raw_score_history, second.raw_score_history)
    assert np.array_equal(_performance(first, SYSTEM_PKD), _performance(second, SYSTEM_PKD))
