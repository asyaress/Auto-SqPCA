# Auto-SqPCA public repository packaging report

Status: **packaged and tested; review the unresolved items before a tagged/Zenodo release**. This report describes the Git content. The exact pushed commit SHA is reported separately because a commit cannot contain its own hash.

## Included files and identity

`docs/release_manifest.csv` lists every committed file except itself, with byte size and SHA-256. Core `auto_sqpca/*.py` files are byte-identical to the frozen `phase3/F3B_checksums.sha256`; `gaps.py` is `a97ddb8595176a9a518238761fd79d6089a933be6bc8cbe732597289338eeaa4`. The Phase 3 copy remains in its original path so frozen relative imports can find the Phase 2 cores. `F3_E1_frozen.json`, `F3_E2_frozen.json`, and `G2R_frozen_config.json` match their `.sha256` companions. Of the 101 entries in `F3B_checksums.sha256`, **93 included original-layout files match exactly, zero mismatch**. Eight are intentionally omitted: two internal plans, the F3A change log and environment file with local machine paths, and four execution/acquisition logs. Public redacted plan copies are in `docs/analysis_plans/`; public reading copies of the F3A changes and post-hoc audit are in `docs/` with original hashes explicitly stated.

The original uncompressed E1 holdout CSV was 101,644,499 bytes and had SHA-256 `1acbda1a8825b6b878704395973fea0c37b4fd1324ee470df106f2344d1aceb3`, matching `F3_C1_result.json`. `results/phase3/F3_E1_holdout_cases.csv.gz` is a deterministic gzip without an embedded filename or timestamp, SHA-256 `4f559d2f51f60b8641a6bafb1a34febb84e21399db4f48bf48eddb9a1f9a4499`; decompression reproduces the authenticated CSV hash. The historical missing requested gzip path remains documented.

The supplied final `Figures_600dpi.zip` had SHA-256 `3fa75356119142a2a6c6aaedf6e44b83b90d19ae9133e9b75f2e4441b822c2d5`. Its Fig1–Fig7 PNGs were copied byte-for-byte into `figures/manuscript/`, with individual hashes in `docs/manuscript_map.md`. The revised manuscript used for caption mapping had SHA-256 `8ad3fb1a3e20c3c6931c0e2feb558de4f605e532a3d67b170955b04255ecce1e`. The manuscript itself is not redistributed.

## Excluded on purpose

- Third-party raw WDC/INTERMAGNET/BMKG hourly and minute archives, GFZ QD files, Mendeley ZIP and extracted outputs, and external DIFI model files. `scripts/00_download/download_manifest.csv` gives 79 authenticated source URLs/paths/hashes; all 79 source files were present locally and matched those hashes during this packaging audit. No raw source file was edited.
- `phase2a/S7C/S7C_wdc_crosscheck.csv` (81.22 MB) and the 101.64 MB uncompressed E1 holdout CSV exceed the 50 MB limit. The latter is included only as authenticated gzip.
- `S7B/D2b_meanfield_comparison.csv` contains daily Mendeley benchmark values and was withheld to avoid redistributing publication data. Other small derived diagnostics are retained.
- G0 input manifest, environment JSONs, and 16 report/metadata copies containing local machine paths, plus nonessential review ZIPs, caches, logs, bytecode, and virtual environments. The public downloader manifest replaces the path-bearing G0 raw-input listing. Internal plan copies in `docs/analysis_plans/` and two explicitly labelled public reading copies in `docs/` redact only local path text; the analysis scripts and frozen numeric configurations were not edited.

## Validation in clean Python 3.12 environment

- Pinned `requirements.txt` installed successfully into a new virtual environment.
- `python -m pytest -q tests`: **10 passed, 0 xfail, 0 failed**. Tests cover frozen module/config/result hashes, observed-value preservation, daily means, synthetic rank-3 recovery below 1e-6 nT, V1 column centring, SVD sign invariance, deterministic selection, original script copy identity, gzip provenance, downloader manifest shape, consistency of the synthetic targeted audit, and release manifest integrity.
- `demo/synthetic_month.py`: **1.52 s**, selected PC1, stability 1.0, 90% band created, abstain false; no external data were read. This is a demonstration, not an E3 result.
- `provenance/audit_tests/audit_tests.py` ran in the clean environment. The rerun is `results/post_hoc/audit_tests_rerun.json`; unrounded values match the archived rounded summary, including 98 EM iterations, null self-reference pass rate 0.5625, independent-reference pass rate 0.4425, and 7 negative-r selections among 176 selections. This test is exploratory and does not modify the frozen method.
- The original E1 and F3B plotting functions were run from the frozen result CSV/JSON in temporary directories. All **five** regenerated PNGs match the archived analytical PNGs pixel-for-pixel at identical dimensions; PNG byte hashes differ in metadata. Checked input rows: E1 summary **66**, TND **108**, E2 risk–coverage **21**, E3 cases **1,068**. Fig. 2 source metrics contain **432** targets, including **381** eligible matrices. The English final manuscript PNGs were visually inspected against the analytical panels; no pixel identity to those edited layouts is claimed.
- No committed file exceeds 50 MB. The largest is the **17,250,288-byte** deterministic holdout gzip. A scan found no personal email address, credential assignment, or user-profile path in committed documentation/metadata. Original scripts still contain some absolute local protocol paths; no path-edited replacement was claimed output-equivalent.

## UNRESOLVED and limits

1. The editable source of manuscript Fig. 1 and the exact plotting script for manuscript Fig. 2 were not found. Final PNGs and Fig. 2 source metrics are archived; no source was fabricated.
2. A single-command full Phase 3 rebuild from third-party raw data is **not demonstrated** (frozen C5 PARTIAL). Several original scripts assume a specific local protocol path; no unverified path-only rewrite was published. Downloading current provider files may also fail a historical SHA-256 check if providers have changed them.
3. G1 remained **HOLD** under registration-2 and registration-3. Only 56/381 eligible matrices met all 1% structural metrics; the repository does not claim exact benchmark replication.
4. The originally requested `F3_E1_holdout_cases.csv.gz` was absent in the analysis tree. This release's deterministic gzip is an authenticated packaging artifact, not a retroactive claim that the original file existed.
5. Author ORCID identifiers and the software DOI require owner input. Third-party data redistribution terms require owner review before any later change to the exclusion policy.

No tag, GitHub Release, repository visibility change, or Zenodo record was created. The owner should review this package, fill ORCIDs, activate Zenodo integration, then create Release v1.0.0 and add its DOI to the citation metadata. `Fase4_protokol_rilis.md` was not present in the project or provided downloads during preparation.

