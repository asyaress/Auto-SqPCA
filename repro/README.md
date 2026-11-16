# Reproducing the Phase 3 case analyses

The frozen Phase 3 scripts still use paths relative to a project root. `portable_pipeline.py` creates that root at an explicit `--output-root`, stages the repository source, and verifies copied data by SHA-256. It does not alter the scientific scripts, frozen configuration, thresholds, seeds, or archived case results. The output root must be outside both the repository and the input root.

## Inputs and rights

Populate `--input-root` with the preserved research input tree:

```
INPUT_ROOT/
  phase2a/            # G0, D1, D2, S7*, G2R, G4R and raw WDC/GFZ/Mendeley
  phase3/raw/          # 2014–2018 hourly WDC, GFZ 2018
  audit_sq_wdc/cache/  # authenticated 2014–2018 monthly source caches
  audit_final/         # Phase 1 minute-archive freeze and QC metadata
```

`scripts/00_download/download_manifest.csv` records original URLs and hashes for downloadable inputs. Obtain raw files from the named providers under their terms. WDC, GFZ, Mendeley, and DIFI data are not redistributed in this package. `prepare` verifies each copied file and then checks the original 161-file Phase 1/2 frozen preflight and minute archive hashes. Its manifest records the input and output roots and Python version. A missing or changed input stops the run.

## Environment and commands

Use Python 3.12 in a new virtual environment. Install `phase3/requirements_f3b.txt`, then `pytest` separately if needed. The reproduction recorded on 17 November 2026 used Python 3.12.6, NumPy 2.5.4, pandas 2.3.3, pyDIFI 8.1.5, geomaglib 1.2.4, ppigrf 1.1.0, Matplotlib 3.10.8, requests 2.34.2, and pytest 9.2.0. `F3_WORKERS` controls concurrent workers; row order can therefore differ while case identities and values agree.

```
python repro/portable_pipeline.py prepare --input-root INPUT_ROOT --output-root OUTPUT_ROOT
python repro/portable_pipeline.py run --output-root OUTPUT_ROOT --workers 8 --stages inventory,ssb,e1_holdout,e1_evaluate,e1_secondary,e2_development,e2_holdout,e2_evaluate,e3b_prepare,e3,e3_summary,figures
```

Stages should run in the order shown. `inventory` verifies raw hourly ZIPs and constructs monthly local-time matrices; `ssb` builds DIFI-8 targets and the 8,748-case injection manifest; `e1_holdout` runs synthetic masks on eligible monthly matrices. The historical E1 reader looks for all GFZ years under `phase2a/raw/gfz`, while the authenticated 2018 file was acquired later under `phase3/raw/gfz`. `prepare` verifies the source against `F3_GFZ2018_source.json` and copies identical bytes to the legacy lookup path inside the output root. No source file or scientific code is modified. This lets a new run include all 149 holdout months directly. The November 2026 forensic rerun instead reproduced the documented preliminary result and then ran the historical 2018 correction; its case results matched the archive. E2 development and holdout use the frozen decisions; `e3b_prepare` reconstructs the exploratory minute-derived months; `e3` evaluates real monthly curves. Evaluator and figure stages regenerate summaries and figures. Stage logs record the command, exit code, elapsed time, and log hash. `prepare` excludes the archived `F3_E3_cases.csv` so `e3` can write a fresh one. Archived results remain in `results/phase3/` for comparison.

Use `compare_cases.py` for E2/E3 and `compare_large_cases.py` for the E1 gzipped archive. The comparison tolerances were fixed before checking: `rtol=1e-10`, `atol=1e-12`, with exact categorical and case-key matching. This accommodates float summation order at a scale well below manuscript rounding. The large comparator uses a disk-backed SQLite database; exclude its temporary database from the review archive.

The old E1 secondary descriptive script pins the archived CSV *byte hash*, which changes with worker completion order. The `e1_secondary` stage first checks all regenerated cases by identity against the archived gzipped table, then supplies the verified rerun hash to the unchanged metric code. It records this narrow hash-guard adaptation. The unmodified E1 evaluator runs on the regenerated cases. Historical summary and figure outputs are references; do not infer full reproduction from their mere presence in the staged tree.

The original `f3_preflight.py` main entry point contains a private protocol download path. The portable wrapper calls its path-independent `verify_snapshot()` function; the underlying frozen code and protocol hash are retained. This is a path adapter, not a change to the scientific method.

The original E1 evaluator forms bootstrap month arrays in CSV encounter order. Worker completion can permute those arrays, changing finite fixed-seed confidence limits by up to 0.00310 in the audited rerun. Every one of the 555,660 case rows matched by identity, all 149 month-median pairs matched in each setting, and the nine superiority decisions were unchanged. `diagnose_bootstrap_order.py` records this effect. The archived confidence limits remain historical values; they are not silently overwritten with the new draw.
