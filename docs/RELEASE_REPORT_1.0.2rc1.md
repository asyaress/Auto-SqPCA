# Auto-SqPCA 1.0.2rc1 reproducibility report

17 November 2026. This candidate follows historical baseline `2dadbbd` and the 1.0.1rc1 audit. The historical `audit_20261116/audit_closure.md`, frozen Phase 1/2 files, original Phase 3 scripts/configurations, and archived results remain intact. No DOI, immutable tag, GitHub Release, journal submission, or new preregistration is claimed.

## Scope and environment

The input was the preserved research snapshot, not a new provider download. A separate Python 3.12.6 virtual environment installed NumPy 2.5.4, pandas 2.3.3, pyDIFI 8.1.5, geomaglib 1.2.4, ppigrf 1.1.0, Matplotlib 3.10.8, requests 2.34.2, and pytest 9.2.0. The portable staging wrapper copied 3,890 input files by SHA-256 into a separate output root. Frozen preflight verified 161 files and the Phase 1 minute archives. The authenticated inventory covered 276 station-months (232 E1 eligible, 253 E2 eligible); 276 regenerated monthly caches matched the original hashes. The DIFI/SSB preparation produced 162 source months and 8,748 injection cases, with manifest SHA-256 `e3b64a35f725dd4a43a02cf0884621cb7e35b46966e418bd4d8ddafda10737d7`, equal to the frozen manifest. E3b preparation matched its 166-month inventory SHA-256 `591320420f8d601e349db15de011ec1e598da7c69431ebdfc7057a77e0ada111`.

The original E1 reader searches `phase2a/raw/gfz` for all years, although the validated GFZ 2018 file resides in `phase3/raw/gfz`. The forensic rerun preserved the incomplete preliminary result, then applied the already documented 2018 correction to 20 months. The first resume attempt emitted the original error `RuntimeError: Holdout recovery incomplete: months=129, truth notes=447`; the completed recovery and correction are recorded separately. The new `repro/portable_pipeline.py` stages a byte-identical GFZ 2018 file at the legacy lookup path in its **output root only**, after verifying the source hash `bc9e68409a1fdbc9765bc351db47a51a993f18fa52e3698673cfce1c64b84738`. Its lookup and frozen preflight were smoke-tested. The direct all-month portable command is documented but was not itself run in full after that adapter change; the complete case-level forensic rerun used the historical correction path. No numerical method was edited.

## Rerun comparison

Comparison tolerances were fixed before results were inspected: finite numbers `rtol=1e-10`, `atol=1e-12`; identifiers, categories, and decisions must match exactly. Case rows were joined by stable identities because worker completion changes CSV order. Independent audit had already checked 17/17 package tests, 318 manuscript table fields, archived ablation reaggregation, and paired-null outcomes; relevant tests were repeated after repository edits (17/17 passed).

| Analysis | Rerun cases | Numeric comparisons | Missing/extra case keys | Mismatches | Result |
|---|---:|---:|---:|---:|---|
| E1 holdout | 555,660 | 7,524,720 | 0/0 | 0 | Case values reproduced |
| E2 development | 3,132 | 46,980 | 0/0 | 0 | Case values reproduced |
| E2 holdout | 5,616 | 84,240 | 0/0 | 0 | Case values reproduced |
| E3 primary + E3b exploratory | 1,068 | 18,156 | 0/0 | 0 | Case values reproduced |

E1 secondary metrics (69 settings), E1 summaries (66 rows), p-star (45), TND (108), E3 station summary (24), E2 risk–coverage, and all five analytical figure pixel arrays matched their historical values. E1 C1 remained true, with MCAR and BLOCK24 improvement. E2 C2 and C3 remained false, and frozen acceptance was 2,083/2,808 (74.18%), below its 80% target. E3 remains 570 primary plus 498 exploratory component cases; 830/1,068 were accepted in total.

E1 superiority CIs require a qualification. All 149 month-median pairs were exactly equal in each of nine settings, and all nine ratios and decisions were unchanged. The evaluator applies seed `20261114` to an array formed in case-CSV encounter order. Parallel worker completion permuted that array, so 12 `ci_lower`/`ci_upper` cells in six nontrivial settings changed by up to 0.0030973. The archived values remain the historical draw; no threshold or seed was changed. The archived and rerun random-rejection arm also uses row-order dependent draws (median error 0.0589900 versus 0.0590251; p90 0.477976 versus 0.476261). Deterministic ablation candidate correlations and errors matched all 2,561 eligible cases; matched-acceptance conclusions remain unchanged. Future outputs should record or canonicalize case order before bootstrap, but such a change would be a new analysis version, not a silent correction to the frozen record.

The GUA January 2014 source chain was independently verified from WDC ZIP SHA-256 `b483ce9313be1eec86a533ef11ace8efa0403f8999529103109dde7d0ce08703` through monthly matrix, fill/residual, and all 54 E2 case values. DIFI boundary sensitivity was recomputed: 19 pre-2014 UTC samples, maximum target change 0.09269 nT, relative target L2 0.002042, and accepted E3 correlation change 0.000370. This does not establish independent true Sq or station exclusion from DIFI model construction.

## Distribution and remaining limits

`repro/portable_pipeline.py` exposes explicit input and output roots, verifies every staged file, and runs the original stages in a separate tree. `repro/README.md` gives commands and required layout. The source download manifest has 79 authenticated third-party input URLs and historical hashes. Large WDC, GFZ, Mendeley, DIFI, and raw-equivalent crosscheck data are omitted from the repository and review ZIP. The public repository alone is therefore insufficient for a raw-input rerun; a researcher must obtain the matching provider files and the preserved non-public audit snapshot, including 46 preflight-required files absent from Git. Current provider bytes and access have not been revalidated as part of this rerun. BGS/WDC terms require checking before redistribution; Mendeley and GFZ attribution remains required.

G1's original-method benchmark remains on hold: only 56/381 eligible matrices met every 1% structural metric. Internal plans are versioned research records, not externally registered plans. DIFI model training-station overlap remains uncertain. The original 80% abstention target, numerical original-method discrepancy, mixed gap-filling outcomes, and lack of clear stability-ranking advantage over correlation ranking are reported as results, not hidden by this release.

This candidate has passed local code tests and authenticated-input case comparison. An immutable public source snapshot and DOI require owner review and release action; no publication action was taken here.
