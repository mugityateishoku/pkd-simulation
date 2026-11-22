"""Check the new archive against earlier simulations and raw-answer analyses."""
import json
import unittest
import numpy as np

from weight_strength import DEFAULT_MANIFEST, OUT, generate_inputs, model, source_components
from analyze_weight_strength import audit


class WeightStrengthChecks(unittest.TestCase):
    def test_archived_endpoints_and_seat_invariance(self):
        _, human = audit(OUT)
        for _, pool in human.groupby(["experiment","group","network","pair","trim"]):
            # The record half outranks the lottery half on the three training questions.
            self.assertTrue((np.diff(pool.sort_values("beta").lottery_weight) <= 1e-12).all())

    def test_common_source_preserves_margins_and_shock_timing(self):
        manifest=json.loads(DEFAULT_MANIFEST.read_text())
        cfg=model.ModelConfig(**manifest["config"])
        seed=manifest["seeds"][0]
        agents,states,private,_=generate_inputs(cfg,seed)
        means,noise,common=source_components(cfg,agents,states,private,seed)
        np.testing.assert_allclose(means+noise,private,atol=1e-13)
        times=[cfg.shock_period-1,cfg.shock_period]
        for i,agent in enumerate(agents):
            before,after=(means[t,i]-states[t] for t in times)
            np.testing.assert_allclose(after,agent.bias,atol=1e-13)
            np.testing.assert_allclose(before*cfg.shock_bias_multiplier,after,atol=1e-13)
        scales=np.array([a.observation_noise*(.3 if 0 in a.specialty_dims else 1.) for a in agents])
        deviation=common[:,:,0]/scales - (common[:,0,0]/scales[0])[:,None]
        np.testing.assert_allclose(deviation,0.,atol=1e-13)
