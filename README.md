# PKD simulation replication package

This repository contains an auditable implementation of the agent-based model
used to compare track-record selection, sortition, autocracy, and an
appeal-based candidate-ranking baseline.

## Release status and provenance

`simulation_pkd_v32.py` is a **same-author, from-specification reconstruction**
of the v3.2 model description, corrected to implement the manuscript's stated
causal ordering. It is not presented as the missing historical source snapshot
that produced previously reported numbers. Regenerate the results before using
them in a manuscript, and report the commit hash and resolved manifest.

The corrected period schedule is:

1. Update the world and apply any scheduled shock.
2. Every agent registers one immutable `raw_prediction`.
3. Each governance system selects and decides from the same registered inputs.
4. PKD may create system-local `post_deliberation_belief` values.
5. Evaluate policies.
6. Update every track record once, using `raw_prediction` only.

Council membership and deliberation therefore cannot change the score being
used to select future expert seats. The code has regression tests for this
invariant.

The old class called `ElectoralDemocracy` ranked candidates once by
`appeal + Normal(0, 0.2)` and did not model voters, turnout, or ballot
aggregation. The corrected implementation and all outputs call this mechanism
**Appeal-based selection baseline**. Two feedback variants are likewise named
**Collective-retrospective appeal baseline** and **Score-informed appeal
baseline**; neither is claimed to be a model of democracy in general.

## Quick start

The reference environment is Python 3.12.3 on Ubuntu 24.04 x86_64, running in
one process. Exact package versions are in `requirements-lock.txt`.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
python -m pip install -r requirements-lock.txt
python -m pytest -q
python reproduce_all.py \
  --manifest configs/reproduce_smoke.json \
  --output-dir reproduction_output
```

The smoke manifest follows every Tables 1-4 / Figures 1-8 code path with small
run counts. To run the declared manuscript-scale experiment matrix:

```bash
python reproduce_all.py \
  --manifest configs/reproduce_manuscript.json \
  --output-dir reproduction_output_manuscript
```

This can be computationally expensive. It is single-process by design so the
random-number stream assignment is transparent and invariant to worker order.
Where the manuscript did not record an exact sensitivity grid or seed, the
manifest makes the reconstruction choice explicit; those values are declared
inputs, not recovered historical settings.

For a core-model-only smoke run:

```bash
python simulation_pkd_v32.py \
  --config configs/model_smoke.json \
  --runs 1 \
  --base-seed 20260301 \
  --output smoke_output
```

## Outputs

`reproduce_all.py` writes:

- `raw/<condition>/period_metrics.csv`: every system-period observation;
- `raw/<condition>/run_summary.csv`: unaggregated run-level statistics;
- `raw/<condition>/final_agent_state.csv`: final agent/track-record state;
- `raw/<condition>/run_manifest.json`: exact configuration and run seeds;
- `tables/table1_*.csv` through `tables/table4_*.csv`;
- `figures/figure1_*` through `figures/figure8_*` as 300-dpi PNG and vector PDF;
- `artifact_map.csv`: figure/table-to-input mapping.

See `REPRODUCIBILITY.md` for the full correspondence table and the limitations
of the docking reference.

## Repository map

- `simulation_pkd_v32.py` - corrected model and CSV exporters
- `reproduce_all.py` - all table, figure, sensitivity, proxy, and gaming entrypoints
- `configs/model_baseline.json` - baseline model parameters
- `configs/reproduce_manuscript.json` - full experiment grid and run counts
- `configs/reproduce_smoke.json` - fast end-to-end verification grid
- `tests/` - causal-order and deterministic reproducibility tests
- `.github/workflows/repro-smoke.yml` - deterministic CI smoke test
- `simulation_pkd_v3.py` - legacy historical script, not the current model
- `PKD_paper_draft_JASSS.md` and root PNG files - legacy submission artifacts

## Reproducibility guarantees

- One shared observation vector per agent-period across all systems.
- Independent named `SeedSequence` streams for the world, traits,
  observations, proxy indicators, strategy, and each selection mechanism.
- Adding the sortition-deliberation comparison cannot alter any baseline.
- Exact-tie expert selection is random but seeded.
- Configs, run seeds, per-period values, and final agent states are exported.
- CI checks deterministic replay and raw/post-deliberation score separation.

## Scope

This is a stylized mechanism-comparison model. It does not model voter-level
preferences, parties, campaigns, rights, legitimacy, or real institutional
outcomes. Its appeal baseline supports claims about appeal-dependent candidate
ranking under the stated assumptions, not about democracy as a whole.

## License

MIT; see `LICENSE`.
