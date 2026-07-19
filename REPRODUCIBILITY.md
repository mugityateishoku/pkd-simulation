# Reproducibility protocol

## Version boundary

The public repository previously contained only `simulation_pkd_v3.py` and two
legacy images. The original code and run-level data for the manuscript's
historical v3.2 numbers were not present. The current implementation is a
specification-aligned reconstruction with the corrected raw-prediction scoring
order. It must not be cited as proof that the historical v3.2 numbers have been
reproduced exactly.

Table 3 therefore combines regenerated results with a clearly labelled v3.1
reference transcribed from the manuscript. Those reference rows are not raw
data and are marked `reference_only` in the CSV. Exact model docking requires
the original v3.1 code and run outputs.

## Deterministic random streams

Each run has a published integer seed. `numpy.random.SeedSequence` creates
separate streams for:

1. world dynamics;
2. population traits;
3. registered observations;
4. public scoring indicators;
5. strategic reports;
6. each governance system's selection mechanism.

Condition seeds are deterministically derived from the manifest `base_seed`
and the condition label. Adding a comparison system does not consume an
existing system's random draws.

## Artifact correspondence

| Artifact | Generator | Manifest conditions | Raw output |
|---|---|---|---|
| Table 1 | `Reproducer.baseline` | `baseline` | `raw/baseline/run_summary.csv` |
| Table 2 | `Reproducer.baseline` | `baseline` | `raw/baseline/final_agent_state.csv` |
| Table 3 | `Reproducer.baseline` | baseline + labelled reference rows | `tables/table3_model_docking.csv` |
| Table 4 | `Reproducer.baseline` | paired baseline runs | `raw/baseline/run_summary.csv` |
| Figure 1 | `figures_1_and_2` | declared single seed | `raw/figure1_single_run/` |
| Figure 2 | `figures_1_and_2` | `baseline` | `raw/baseline/period_metrics.csv` |
| Figures 3-4 | `sensitivity` | seven explicit one-factor grids | `raw/sensitivity_*/` |
| Figure 5 | `bias_sweep` | explicit bias grid | `raw/bias_*/` |
| Figure 6 | `scoring_channel` | proxy, delay, projection grids | `raw/scoring_*/` |
| Figure 7 | `appeal_feedback` | collective and individual score grids | condition raw folders |
| Figure 8 | `gaming` | honest, herding, targeting, firewall | `raw/gaming_*/` |

The generated `artifact_map.csv` repeats this mapping in machine-readable form.
The manuscript did not preserve every exact grid point and seed for these
secondary analyses. `configs/reproduce_manuscript.json` therefore declares the
values chosen for this reconstruction; it does not imply that they are the
unrecoverable historical settings.

## Registered prediction invariant

At period `t`, `raw_prediction_i(t)` is copied immediately after observation.
Every system reads that same array. PKD's
`post_deliberation_belief_i(t)` is a local array and never mutates an `Agent`.
Feedback compares the registered raw array with the period's scoring target.
The tests require final track records to be bitwise identical when deliberation
is switched on or off under the same seed.

## Statistical analysis

The primary comparisons in Table 4 are paired by run seed. The table reports
the mean paired difference, its 95% t interval, a paired t test, Wilcoxon
signed-rank test, and within-pair standardized effect `d_z`. Run-level CSV is
the unit of analysis; time points are not treated as independent replications.

## Environment

- Python 3.12.3
- NumPy 2.2.6
- SciPy 1.15.3
- Matplotlib 3.10.3
- single process; no parallel workers
- Linux reference runner in GitHub Actions

The code is written for Python 3.10+, but the locked versions and CI runner are
the reference environment for artifact reproduction.
