import numpy as np
import pytest

import simulation_pkd_v32 as model
from review_followup import effective_coefficients, observe_pkd_decisions


def test_no_deliberation_preserves_final_weights():
    values = np.array([[0., 1.], [2., 0.], [3., -1.]])
    scores = np.array([-1., -2., -3.])
    for weighted in [False, True]:
        w, a, matrix = effective_coefficients(values, np.ones(3), scores, .3, False, weighted)
        assert np.array_equal(matrix, np.eye(3))
        assert np.array_equal(w, a)
        assert np.allclose(a.sum(), 1.)


def test_complete_neighborhood_preserves_record_weighted_aggregate():
    values = np.array([[0., 1.], [2., 0.], [3., -1.]])
    w, a, matrix = effective_coefficients(values, np.full(3, 100.), np.array([-1., -2., -3.]), .3)
    assert np.allclose(a, w)
    assert np.allclose(matrix.sum(axis=1), 1.)
    assert np.allclose(a @ values, w @ values)


def test_asymmetric_neighborhood_weights_reproduce_original_operator():
    values = np.array([[0.], [1.], [3.]])
    tolerances = np.array([1.5, .1, 5.])
    scores = np.array([0., -1000., -1001.])
    for weighted in [False, True]:
        w, a, matrix = effective_coefficients(values, tolerances, scores, .4, True, weighted)
        post = model.bounded_confidence_deliberation(values, tolerances, scores, .4)
        assert np.allclose(matrix @ values, post)
        assert np.allclose(a @ values, w @ post)
        assert (a >= 0.).all() and np.isfinite(a).all()
        assert np.isclose(a.sum(), 1.)
        assert 1. <= 1. / np.sum(a**2) <= len(a) + 1e-12


def test_observer_does_not_change_trajectories_or_random_streams():
    config = model.ModelConfig(n_periods=18, shock_period=7, include_sortition_deliberation=True)
    plain = model.run_simulation(config, seed=1729)
    original = model.PhilosopherKingDemocracy.decide
    with observe_pkd_decisions() as rows:
        observed = model.run_simulation(config, seed=1729)
    assert model.PhilosopherKingDemocracy.decide is original
    assert np.array_equal(plain.raw_score_history, observed.raw_score_history)
    assert np.array_equal(plain.final_track_records, observed.final_track_records)
    assert plain.periods == observed.periods
    assert plain.election_records == observed.election_records
    assert len(rows) == config.n_periods
    assert max(row['policy_reconstruction_max_gap'] for row in rows) < 1e-12
    assert all(np.isclose(row['effective_record_weight'] + row['effective_lottery_weight'], 1.) for row in rows)


def test_observer_restores_method_after_exception():
    original = model.PhilosopherKingDemocracy.decide
    with pytest.raises(RuntimeError):
        with observe_pkd_decisions():
            raise RuntimeError("synthetic observer failure")
    assert model.PhilosopherKingDemocracy.decide is original
