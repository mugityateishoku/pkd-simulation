import numpy as np

from simulation_pkd_v32 import (
    BASELINE_SYSTEMS,
    ModelConfig,
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
        n_citizens=0,
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
        assert values and all(value == 1.0 for value in values)


def test_baseline_name_does_not_claim_voter_aggregation():
    config = ModelConfig(n_periods=2, shock_period=99)
    result = run_simulation(config, seed=1)
    names = {record.system for record in result.periods}
    assert not any("Electoral Democracy" in name for name in names)
    assert SYSTEM_PKD in names
