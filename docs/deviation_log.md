# Deviations and audit limits

This log describes recorded deviations. It does not alter the archived numerical results.

| Item | Record | Evidence |
|---|---|---|
| EM stopping precision | The initial F3-v1 text specified 1e-4 nT. Before observatory analysis, the implementation tightened the final guard to 1e-8 nT to satisfy the mandatory synthetic rank-3 test while retaining the 500-iteration cap. | `auto_sqpca/gaps.py`, `docs/F3A_changes_public.md`, `phase3/F3_synthetic_tests.json` |
| GFZ QD 2018 | The file was initially absent. It was later acquired and 20 affected months were recalculated; original and corrected results are documented. | `phase3/F3_GFZ2018_source.json`, `phase3/F3_E1_2018_correction.json`, `phase3/F3A_report.md` |
| F3-v1.1 | The versioned amendment governs Task B E2/E3. | `docs/analysis_plans/F3_amendment_v1.1.md`, frozen SHA-256 in `phase3/F3B_checksums.sha256` |
| E1 holdout file | Requested `F3_E1_holdout_cases.csv.gz` did not exist in the analysis tree. Authenticated `phase3/work/E1_holdout_cases.csv` was used; SHA-256 `1acbda1a8825b6b878704395973fea0c37b4fd1324ee470df106f2344d1aceb3` matches `F3_C1_result.json`. The 101,644,499-byte original exceeded the public file limit. This package adds a deterministic gzip (mtime=0, no embedded filename) at `results/phase3/F3_E1_holdout_cases.csv.gz`, SHA-256 `4f559d2f51f60b8641a6bafb1a34febb84e21399db4f48bf48eddb9a1f9a4499`. Decompress and compare its SHA-256 with the source hash. The missing originally requested path remains a historical **UNRESOLVED** record. | `phase3/F3_C1_result.json`, `docs/post_hoc_summary.md` |
| QD 2018 audit path | The first U1 audit run used the wrong QD path and failed with `FileNotFoundError`; the post-hoc audit script was corrected to the authenticated Phase 3 QD location. No frozen source was edited. | `docs/post_hoc_summary.md`, `phase3/audit_add/audit_u1.py` |
| Script path portability | No archived analysis script was edited for path portability because a three-case byte-identical output equivalence proof for changed copies has not been performed. Original absolute path assumptions remain in several scripts. `scripts/40_figures/render_frozen_figures.py` is a new wrapper that stages frozen CSV/JSON into a temporary directory; the original renderer bytes are unchanged. | `provenance/original_scripts/`, `tests/test_release.py` |
| Public data boundary | Third-party raw hourly/minute observatory archives, Mendeley outputs, GFZ days, and DIFI model inputs are excluded. The 81 MB `S7C_wdc_crosscheck.csv` is also excluded under the 50 MB file limit; its historical hash stays in the archived preflight inventory. | `scripts/00_download/download_manifest.csv`, `phase3/F3A_preflight.json` |

Additional limits: G1 held under both registration-2 and registration-3; 56/381 matrices met all structural 1% metrics. A one-command full Phase 3 rerun from raw data has not been demonstrated (C5 PARTIAL). Hashes establish identity but not timing or independent registration.

## Release candidate 1.0.1rc1 audit corrections (2026-11-16)

| Item | Versioned change and scope | Verification |
|---|---|---|
| Root package imports | Root `auto_sqpca` now imports exact copies of the frozen G2R and G4R numerical cores from `auto_sqpca/_frozen/`. The earlier direct import raised `ModuleNotFoundError: No module named 'pca_core'`. Historical `phase3/auto_sqpca/` stays unchanged. | Direct import, vendored byte equality, and valid-input exact-output tests in `tests/`. |
| Nonfinite input guard | Root M-EM now maps NaN and infinity to missing before computing daily initial means. Historical M-EM could pass infinity to SVD. This is a new behavior for formerly failing input only. | Infinity test, observed-value preservation, valid-input exact-output comparison. |
| Selection and bootstrap edge cases | Root selection rejects nonfinite or constant references and candidates explicitly; root bootstrap validates positive B and returns zero stability when the original selection is absent. Historical behavior remains in Phase 3. | Targeted unit tests in `tests/test_public_contract.py`. |
| Post hoc ablation | A matched-acceptance comparison on frozen E2 holdout cases was declared in `audit_20261116/posthoc_protocol.md` before execution. Correlation ranking was recomputed from SSB caches. It is descriptive and its holdout threshold is not a deployment threshold. | `audit_20261116/ablation.py`, cases, risk table, cluster resamples, summary. |
| Post hoc paired null | A new shared bank was declared before execution. It does not overwrite or pair the original 400/400/60 archives. | `audit_20261116/paired_null.py`, per-case transitions and summary. |
| U3 explanation and rounding | `audit_u3.py` fills original gaps before applying synthetic masks. Realized random mask fractions below 90%, not addition of original gaps, explain part of MCAR 10% abstention. The M-EM median `0.0224832947` rounds to `0.022` at three decimals. | Frozen code, `U3_summary.csv`, `audit_20261116/reconciliation.json`. |

