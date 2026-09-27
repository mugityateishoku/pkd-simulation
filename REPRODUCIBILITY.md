# September 2026 reproducibility record

The manuscript uses only `results/preprint_2026/`. Each of 55 conditions has 30 runs and 300 periods. Conditions were specified before this run, but the study was not preregistered. Root seed: 20260927. The manifest records all run seeds and resolved model fields.

## Definitions and verification

`performance` is negative squared Euclidean error. The paper reports positive error, summed over dimensions and averaged within each run. Periods are not independent replications. Pointwise 95% intervals use Student's t over run means or paired differences. No multiple-comparison significance classification is claimed.

Shock effects compare post-minus-pre changes against a paired no-shock counterfactual. Electoral and component interventions reuse seeds. Changes to population composition or dimension alter draw mappings and are sensitivity comparisons, not identical-observation interventions.

`verification.json` records the independent archived-data audit: 4,455,000 period-system observations and 14,850 run-system summaries. Maximum aggregation discrepancy is below 8e-15. Matched record-based elections and selection differ by less than 1e-12 after initialization. The equal-mean analytical expectation 0.087816665 lies inside the simulated interval.

The 16 tests check deterministic replay, causal scoring order, random ties, independent optional streams, local-softmax underflow, the averaging identity, default eligibility and vote aggregation. No independent team replicated the model.

The direct-indicator empty-council representation fields are sentinels and are excluded from representation rankings. Population aggregation is unconstrained. Type-screened lottery is a sensitivity. `mean_demagogue_fraction` is label-based occupancy, not a direct measure of damage or political populism.

## Builds and provenance

Use the commands in README. The production model hash is checked before and after execution. Data do not silently mix core versions. `prepare_paper.py` derives numeric passages and tables from the result JSON; `build_paper.py` creates DOCX with native Word equations (requires python-docx==1.2.0). The PDF was exported from Word with tags and embedded fonts.

Bibliographic metadata and primary-source checks are recorded in `references/`. Metadata alone do not verify a scientific claim. Older scripts, drafts and results are not evidence for this study and have been removed from the current release tree; their source revisions remain in Git history.
