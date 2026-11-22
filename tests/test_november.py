"""Regression checks for timing, membership, weights and replay of the November analyses."""
import unittest
import subprocess
import sys
from pathlib import Path
import numpy as np
from empirical_panels import select_panels, stable_weights, compare_fold
from adaptive_panels import generate_inputs, trajectory
import simulation_pkd_v32 as m

class NovemberChecks(unittest.TestCase):
    def test_published_summaries_and_reference_runs(self):
        root = Path(__file__).resolve().parents[1]
        subprocess.run([sys.executable, "verify_november.py"], cwd=root, check=True)

    def test_membership_and_party_quotas(self):
        rng = np.random.default_rng(8)
        party=np.arange(24)<10
        record=np.zeros(24)
        uniforms=(rng.random((128,24)), rng.random((128,24)), rng.random(128))
        top, mix, random=select_panels(record,party,*uniforms)
        np.testing.assert_array_equal(top[:,:5],mix[:,:5])
        for panel in (top,mix,random):
            self.assertTrue(all(len(set(row))==10 for row in panel))
        remaining_share=(party.sum()-party[mix[:,:5]].sum(axis=1))/19
        self.assertTrue(np.all(np.abs(party[mix[:,5:]].sum(axis=1)-5*remaining_share)<=.5+1e-12))
        np.testing.assert_allclose(stable_weights(record[mix])[:,5:].sum(axis=1),.5)

    def test_held_out_truth_and_responses_do_not_select_members_or_weights(self):
        rng=np.random.default_rng(5)
        x=rng.normal(size=(40,4))
        target=np.zeros(4)
        draws=(rng.random((128,40)),rng.random((128,40)),rng.random(128))
        party=np.arange(40)%2==0
        def compare(): return compare_fold(x,target,np.ones(4),party,1,draws)
        first=compare()
        x[:,1]=100
        target[1]=98
        second=compare()
        self.assertEqual(first["lottery_weight"],second["lottery_weight"])
        for key in ("mixed_score","mixed_equal","pool_score","record10_score"):
            self.assertAlmostEqual(second[key],4.)

    def test_private_and_forced_copy_timing(self):
        cfg=m.ModelConfig(pkd_deliberation=False)
        inputs=generate_inputs(cfg,201)
        honest=trajectory(cfg,"random","private",inputs,201)
        copy=trajectory(cfg,"random","copy",inputs,201)
        self.assertEqual(honest["copy"],0.)
        self.assertAlmostEqual(copy["copy"],294/300)
        self.assertEqual(honest["party_tv"],copy["party_tv"])
        self.assertEqual(honest["occupancy"],copy["occupancy"])

if __name__=="__main__":
    unittest.main()

