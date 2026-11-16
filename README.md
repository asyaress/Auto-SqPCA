# Auto-SqPCA

This repository packages the Auto-SqPCA workflow accompanying *Transferring PCA-based extraction of the solar quiet geomagnetic variation to low and equatorial latitudes: an automated workflow with explicit abstention*. It customizes the PCA-based solar quiet (Sq) method of Morozova and Rebbah (2023), *MethodsX* **10**, 101999. Their Sq-mode selection rule is inherited; local-time matrices, missing-data handling, parsimonious candidate selection, day bootstrap, and explicit abstention were added here. The historical Phase 3 code and archived results are frozen. The portable root package is version 1.0.1rc1 and has documented input guards; it is not claimed to have generated the archived Phase 3 results.

## What the archived results show

- The structural comparison was broadly consistent with the published outputs, but all numerical structure metrics met the 1% criterion in only **56/381** eligible matrices (`results/phase2/G4R/G3R_structure_metrics.csv`; `phase2a/G4R/G4R_report.md`). G1 remained on hold; this is not a numerically exact reproduction.
- M-EM gap filling was **not better than linear interpolation for random missingness at 5–10%** in the post-hoc operating-range comparison. Block gaps showed mixed median and tail behavior; results can depend on the 500-iteration cap (`results/post_hoc/U1_summary.csv`, `U2_operating_range_ratios.csv`).
- PC combinations did not show an improvement for the pre-specified X-component comparison (`results/phase3/F3_E2_C2.csv`). They remain optional candidates, not a validated added contribution.
- The frozen abstention rule accepted **74.18%** of the unmasked E2 holdout cases, below its **80%** target (`results/phase3/F3_E2_result.json`; `phase3/F3B_report.md`).
- Agreement with DIFI-8 is descriptive and **not fully independent validation** of Auto-SqPCA. E3 is limited to the tested stations; E3b is exploratory.

## Install and try the synthetic demo

Python **3.12** was used. Frozen analysis versions were NumPy 2.5.4, pandas 2.3.3, Matplotlib 3.10.8, ppigrf 1.1.0, and pyDIFI 8.1.5 (`docs/release_environment.md`, `phase3/requirements_f3b.txt`). The pinned `requirements.txt` also lists supporting packages and pytest.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[demo,test]"
.venv\Scripts\python -c "from auto_sqpca.pca import decompose_v1; print('import OK')"
.venv\Scripts\python -m auto_sqpca.cli demo --output demo/output
.venv\Scripts\python -m auto_sqpca.cli verify
```

The demo uses generated 24-hour data only and writes `demo/output/demo_result.json`, a 24-row curve/band CSV, and a PNG. Its 200 day resamples use the frozen seed. It is illustrative; it does not reproduce an observatory result.

## Obtain the external inputs

`scripts/00_download/download_manifest.csv` records original URLs, target paths, versions, and archived SHA-256 for 79 source archives/files. Downloads are opt-in and hashes are mandatory:

```powershell
.venv\Scripts\python scripts/00_download/download.py --source GFZ_IQD_IDD
.venv\Scripts\python scripts/00_download/download.py --verify-only
```

Omit `--source` to fetch every listed input. Hash mismatches stop the operation; an upstream provider may have changed a file. The Mendeley archive is large and intentionally absent from Git. Archived derived results do not imply that an end-to-end rerun from third-party raw data has been demonstrated. The Phase 3 C5 status is **PARTIAL**.

## Trace the analysis and figures

Original scripts retain their original relative layout in `phase2a/` and `phase3/`; byte-identical copies are in `provenance/original_scripts/`. The top-level `auto_sqpca/` imports byte-identical vendored Phase 2 numerical cores from `auto_sqpca/_frozen/`; its NaN/infinity guard, reference validation, and bootstrap edge-case behavior are versioned release corrections. Valid finite inputs were compared against the historical code with exact equality in targeted tests. The `scripts/` folders are entry-point inventories of the historical scripts. Read the relevant internal plan and frozen configuration before running an analysis, then work in a separate copy so archived outputs stay unchanged:

- Phase 2: `phase2a/G2R/g2r.py` (V1 PCA) and `phase2a/G4R/g4r_run.py` (classification).
- Phase 3 E1: `phase3/f3_e1.py`, E2: `phase3/f3b_e2_eval.py`, E3: `phase3/f3b_e3.py`.
- Post-hoc checks U1–U6: `phase3/audit_add/` and `results/post_hoc/`, all labelled **EXPLORATORY_POST_HOC**. They do not change the frozen method.
- Archived figure script: `.venv\Scripts\python scripts/40_figures/render_frozen_figures.py`. It runs the unmodified F3B renderer from frozen CSV/JSON in a temporary directory and writes to `scripts/40_figures/output/`. The original PNGs are in `phase3/`.

The detailed [manuscript map](docs/manuscript_map.md) lists each table and figure, its source script and result hash. Some manuscript graphics are editorial compositions for which no exact one-command source is archived; the map identifies those limits. Do not substitute newly drawn figures as if they were archived originals.

## November 2026 audit and reproduction level

The [audit protocol](audit_20261116/posthoc_protocol.md) identifies the post hoc analyses before their execution. [Case reconciliation](audit_20261116/reconciliation.json) re-aggregates archived E1–E3 and U3/U5 case files; [matched ablation](audit_20261116/ablation_summary.json) recomputes the frozen selected-candidate correlation from authenticated SSB month caches and validates each candidate error against the archived value; [paired pure-null](audit_20261116/paired_null_summary.json) reruns the frozen selection and day bootstrap on a new, paired synthetic bank. A [54-case E2 slice](audit_20261116/rerun_slice.json) reproduces archived values from its authenticated SSB cache, and a [DIFI boundary sensitivity](audit_20261116/difi_boundary_summary.json) recomputes the two affected model months. These are different verification levels. `audit_20261116/case_manifest.csv`, `ablation_cases.csv`, and `paired_null_cases.csv` carry per-case decisions. The full E1/E2/E3 pipeline from third-party raw inputs has not been rerun end to end in a clean environment. Phase 3 C5 therefore remains **PARTIAL**. See [audit closure](audit_20261116/audit_closure.md) for findings, unresolved provenance, and release limitations.

## Provenance and data credit

The plans in `docs/analysis_plans/` are **versioned internal documents, not third-party registered plans**. Hashes establish file identity, not chronology. See [deviations](docs/deviation_log.md) and [release report](docs/RELEASE_REPORT.md) for known limits.

Observatory source data came through [WDC Edinburgh/BGS](https://www.wdc.bgs.ac.uk/), with INTERMAGNET and BMKG station contributions where applicable. International quiet days and Kp come from [GFZ Potsdam](https://kp.gfz-potsdam.de/) (Matzka et al., 2021; DOI 10.5880/Kp.0001). The published comparison data are [Morozova and Rebbah's Mendeley Data v1](https://doi.org/10.17632/jcmdrm5f5x.1). The external field comparison uses DIFI-8 (Chulliat et al., 2025, [DOI 10.1051/swsc/2025041](https://doi.org/10.1051/swsc/2025041)). Raw observatory, Mendeley, GFZ and DIFI-model data are not redistributed here.

## Citation and license

Software code: MIT. `pyproject.toml`, `CITATION.cff`, and `.zenodo.json` carry release candidate version 1.0.1rc1. No DOI, tag, GitHub Release, or Zenodo record is claimed. Third-party datasets retain their providers' terms.

