"""Audit archived period data independently of the production summarizer."""
from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd
from simulation_pkd_v32 import SYSTEM_PKD, SYSTEM_ELECTION, SYSTEM_POOL_EQUAL, SYSTEM_INDICATOR

root=Path('results/preprint_2026')
manifest=json.loads((root/'study_manifest.json').read_text())
assert hashlib.sha256(Path('simulation_pkd_v32.py').read_bytes()).hexdigest()==manifest['simulation_sha256']
total=0; largest_discrepancy=0.; checks={}
for condition in manifest['conditions']:
    folder=root/'raw'/condition
    p=pd.read_csv(folder/'period_metrics.csv.gz')
    s=pd.read_csv(folder/'run_summary.csv')
    assert len(p)==30*300*9, (condition,len(p))
    assert len(s)==30*9
    assert not p.isna().any().any()
    assert np.isfinite(p.select_dtypes('number')).all().all()
    assert (p.performance<=1e-14).all()
    observed=p.groupby(['run','seed','system']).performance.mean()
    reported=s.set_index(['run','seed','system']).mean_performance
    discrepancy=float((observed-reported).abs().max())
    largest_discrepancy=max(largest_discrepancy,discrepancy)
    assert discrepancy<1e-12, (condition,discrepancy)
    if condition=='matched_record_selection':
        pivot=p[p.period>=6].pivot(index=['run','period'],columns='system',values='performance')
        gap=float((pivot[SYSTEM_PKD]-pivot[SYSTEM_ELECTION]).abs().max())
        assert gap<1e-12
        checks['matched_record_post_initialization_max_error_gap']=gap
    if condition=='baseline':
        baseline=p
        expected=(97.79*(10-.91*1.5)+5*(2.25/3+9*2/3))/10000
        report=json.loads((root/'analysis/results.json').read_text())['baseline'][SYSTEM_POOL_EQUAL]['loss']
        assert report['low']<expected<report['high']
        checks['analytic_equal_pool_expected_error']=expected
        checks['analytic_equal_pool_interval_contains_expectation']=True
    if condition=='shock_absent':
        pre=p[p.period<100].reset_index(drop=True)
        assert np.array_equal(pre.performance.values,baseline[baseline.period<100].performance.values)
        checks['paired_shock_identical_pre_periods']=True
    if condition.startswith('regime_change_prob_'):
        # Translation-invariant estimation should ignore exogenous state drift.
        assert np.allclose(p.performance,baseline.performance,rtol=0,atol=1e-12)
    if condition.startswith('election_weight_') or condition.startswith('electoral_'):
        assert np.array_equal(p[p.system==SYSTEM_PKD].performance.values,baseline[baseline.system==SYSTEM_PKD].performance.values)
    if condition in ['baseline','proxy_noise_0.5','proxy_noise_1','proxy_noise_2']:
        sigma=manifest['conditions'][condition]['proxy_noise']
        expectation=10*sigma*sigma
        runs=-p[p.system==SYSTEM_INDICATOR].groupby('run').performance.mean()
        assert abs(runs.mean()-expectation)<=max(.12*expectation,1e-14)
    total+=len(p)
checks.update(conditions=len(manifest['conditions']),condition_runs=55*30,period_system_rows=total,
              largest_summary_recalculation_error=largest_discrepancy,source_hash_matches=True)
(root/'verification.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print(json.dumps(checks,indent=2))
