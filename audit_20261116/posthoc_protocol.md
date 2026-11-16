# Post hoc audit protocol — written before new analyses

Date: 2026-11-16. Baseline repository commit: `2dadbbd8555c5ed259f14472ec515d9a922dd87b`. These analyses were not part of the frozen F3-v1.1 plan and do not alter its thresholds, acceptance target, or primary C2/C3 outcomes.

## Matched acceptance ablation

Source: archived E2 holdout `phase3/work/E2_holdout_cases.csv`, joined by `case_id` to `phase3/F3_ssb_manifest.csv`. Primary stratum is `mask=NONE`, 2,808 cases. The frozen operating point accepts when status is OK, a candidate passes A1, stability is at least 0.5, observed fraction is at least 0.9, and relative width is finite and no greater than the frozen infinity limit. Preserve its observed acceptance count.

Comparison population is the same upstream eligible cases for every arm: status OK, A1 passes, completeness passes, finite candidate error. Report how many cases fail eligibility and why. At its native operating point, no-A2 accepts all eligible cases. For matched acceptance, retain the same number as the frozen arm using: (1) largest stability; (2) largest absolute correlation of the frozen selected candidate with its fixed IQD reference, recomputed from the frozen source cache and code; (3) uniform random selection without replacement, 1,000 independently seeded replicates (seed 20261116). Ties in scores use `case_id` ascending. Matched score thresholds are descriptive holdout quantiles, not deployment thresholds. No retuning of A1, A2, A3, A4 or candidate construction.

For each arm report acceptance over all 2,808, median and 90th-percentile relative L2 error among accepted, and risk–acceptance curves. Compare arms on the same cases and preserve station-year-month clusters. Use 2,000 cluster bootstrap draws with seed 20261117 for 95% percentile intervals on paired risk differences at matched acceptance. Random arm uncertainty includes the 1,000 random draws; report its distribution separately. The case table retains each eligibility and arm decision.

## Paired pure-null audit

Use a new bank of 100 independent 24 × 30 null matrices per reference construction (seed 20261118), plus 100 independent-reference draws. In each matrix, 24 hourly innovations follow AR(1) with rho 0.9, Gaussian marginal SD 5 nT, and independent days, with 20,000 nT constant level. Self-reference uses five sampled in-matrix days and the frozen `sq_iqd` function; independent-reference uses five separately simulated days and demeaned hourly average. Use the frozen V1 PCA, 7-candidate selection, 1,000 phase surrogates, and 200 day bootstraps with fixed reference and frozen stability cutoff 0.5. For a given case, record candidate-only A1, stability, full A1+A2, and decision transition. Report exact counts, Wilson 95% intervals per proportion, and paired transitions. Both reference constructions are separate strata. These nulls measure only this simulation, not a universal false-positive rate.

Archived 400/400/60 null runs are audited separately; they are not paired across the candidate and full-workflow outputs.
