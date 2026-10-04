# September and October 2026 reproducibility record

Version 2 uses the preserved September study in `results/preprint_2026/` and the October review in `results/review_2026/`. September has 55 labeled batches, each with 30 runs and 300 periods. The labels `expert_noise_0.9` and `interaction_noise_0_delay_0` have identical resolved settings, seeds and output tables. They supply one shared reference, not two independent experiments: there are 54 distinct settings, 1,650 executions and 1,620 unique setting-seed combinations. The conditions were specified before execution, but the study was not preregistered. Root seed: 20260927.

The October observer follow-up declared 11 settings before execution and used the same 30 archived seeds for 300 periods. The settings vary the number of record-selected seats (0, 2, 5, 8 or 10) and final weighting, with deliberation off, plus the original baseline with deliberation on. Four settings reproduce existing September configurations (`baseline`, `lottery_only_10`, `no_deliberation`, `record_only_10`). Those 120 repeated setting-seed combinations add measurement records, not independent evidence. The 330 follow-up runs include seven new configurations; both studies together contain 61 distinct configurations. This was an exploratory response to inspection of the September results.

## Definitions and verification

`performance` is negative squared Euclidean error. The paper reports positive error, summed over dimensions and averaged within each run. Periods are not independent replications. Pointwise 95% intervals use Student's t over run means or paired differences. No multiple-comparison significance classification is claimed.

Shock effects compare post-minus-pre changes against a paired no-shock counterfactual. Electoral and component interventions reuse seeds. Changes to population composition or dimension alter draw mappings and are sensitivity comparisons, not identical-observation interventions.

`verification.json` records the independent archived-data audit: 4,455,000 period-system observations and 14,850 run-system summaries. Maximum aggregation discrepancy is below 8e-15. Matched record-based elections and selection differ by less than 1e-12 after initialization. The equal-mean analytical expectation 0.087816665 lies inside the simulated interval.

The current 21 tests cover deterministic replay, causal scoring order, random ties, independent optional streams, local-softmax underflow, the averaging identity, default eligibility, vote aggregation, and the observer's invariants and non-interference. No independent team replicated the model.

The direct-indicator empty-council representation fields are sentinels and are excluded from representation rankings. Population aggregation is unconstrained. Type-screened lottery is a sensitivity. `mean_demagogue_fraction` is label-based occupancy, not a direct measure of damage or political populism.

## October measurements and checks

The observer records council IDs and selection roles, final aggregation weights, and coefficients on original council estimates. For a realized confidence-neighborhood matrix, the latter coefficients equal `B.T @ w`; they are nonnegative, sum to one and reconstruct the returned decision. Changing estimates can also change the neighborhoods, so these coefficients are not causal derivatives or measures of political power. The reciprocal sum of squared coefficients describes concentration, not statistical sample size. The fraction of agents seated at least once describes this finite simulation, not equal selection chances.

`verify_review.py` is independent of the October production analyzers. It recalculates all 99,000 coefficient rows, all reported run means, intervals and paired contrasts; checks five matched score/equal council pairs and all four repeated September trajectories; and checks hashes of the frozen core, original runner, October observer and retrospective analyzer. Its report is `results/review_2026/independent_verification.json`. Raw coefficient CSVs do not contain the original estimates, so that CSV audit can check coefficient arithmetic but cannot independently reconstruct the policy. Reconstruction is an execution invariant, supported separately by observer tests and archived-baseline replay. The largest recorded reconstruction discrepancy was below 3e-15.

The retrospective delay and component analysis divides archived runs into startup and later windows. The 30-period cutoff was chosen after inspection to cover the largest delay (24 periods) plus a selection cycle (6 periods); periods 90–299 provide a second cutoff. Neither cutoff proves convergence. Comparisons retain the run as the uncertainty unit and pair exact run/seed identifiers. Overlapping windows are not additional experiments. An interval spanning zero does not prove equivalence.

The comparison of five record plus five lottery seats against ten record seats holds council size, score weighting and disabled deliberation fixed. Dimension comparisons also report loss per coordinate, but this only changes reporting units. Changing dimension or the number of scored coordinates affects weight magnitudes and other model features; these experiments do not isolate information quantity alone. `track_decay` affects individual record updates and election incumbent memory.

## Builds and provenance

Use the commands in README. The production model hash is checked before and after execution. Data do not silently mix core versions. `prepare_paper.py` derives numeric passages and tables from the result JSON; `build_paper.py` creates DOCX with native Word equations (requires python-docx==1.2.0). The PDF was exported from Word with tags and embedded fonts.

The October observer source is preserved byte for byte from the executed study. Its CLI supports a run subset but does not change the number of periods directly. The CI observer smoke check therefore copies the original manifest and baseline trace into a temporary directory, changes only `conditions.baseline.n_periods` to 18 in that temporary manifest, and uses the first two original seeds. The original shock period is retained so the beginning of the trajectory matches the archived baseline. These temporary smoke files are not paper evidence.

Use `python verify_review.py` for a read-only audit. `python verify_review.py --write-report` explicitly records a fresh successful audit and its input hashes; normal audits check against that report. `FILE_SHA256SUMS.txt` supplies release-wide file checksums. The September model and runner hashes are unchanged in this release.

Bibliographic metadata and primary-source checks are recorded in `references/`. Metadata alone do not verify a scientific claim. Older scripts, drafts and results are not evidence for this study and have been removed from the current release tree; their source revisions remain in Git history.
