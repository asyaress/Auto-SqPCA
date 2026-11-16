# November 2026 audit reproduction

This folder adds post-hoc checks to historical commit `2dadbbd`; it does not modify archived Phase 3 outputs. Read `posthoc_protocol.md` before interpreting the ablation or null. Scripts use Python 3.12 with NumPy, Matplotlib (plot only), pyDIFI (DIFI sensitivity), and the frozen Phase 3 modules. Results were produced with the repository's existing `.venv` (NumPy 2.5.4, pyDIFI 8.1.5) unless the closure report states a clean-environment package check.

Run from the repository root:

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
.venv\Scripts\python audit_20261116\reconcile.py
.venv\Scripts\python audit_20261116\ablation.py
.venv\Scripts\python audit_20261116\paired_null.py
.venv\Scripts\python audit_20261116\difi_boundary.py
.venv\Scripts\python audit_20261116\rerun_raw_slice.py
.venv\Scripts\python audit_20261116\rerun_slice.py
.venv\Scripts\python audit_20261116\plot_ablation.py
```

`reconcile.py`, `ablation.py`, `difi_boundary.py`, `rerun_raw_slice.py`, and `rerun_slice.py` need the original project tree two levels above the repository, including `phase3/work`, the frozen monthly caches, `phase3/raw/hourly`, and `phase2a/raw/gfz`. These data are omitted from the small public package. They must match the SHA-256 values recorded in `reconciliation.json`, `ablation_summary.json`, and the slice result JSONs. `paired_null.py` is self-contained apart from frozen source code and NumPy. The source manuscript table checker is in the separate manuscript-revision workspace and its output is `manuscript_table_validation.json`.

The scripts write only into this audit folder. `ablation.py` resumes authenticated correlation scores from `ablation_scores.csv` if present. Remove that file only in a disposable working copy to force score recomputation; do not alter frozen case files. `case_manifest.csv` summarizes E1 truth slots plus all E2/E3 cases; the full 555,660-row E1 case ledger is the already archived `results/phase3/F3_E1_holdout_cases.csv.gz`.

`revise_manuscript.py` accepts the rev3 DOCX and a new output path as its first two arguments; the source rev3 file is not in Git. It uses the audited risk figure in this folder. `verify_manuscript_tables.py` accepts the revised DOCX as its first argument and writes `manuscript_table_validation.json`. Run these with the bundled document Python that includes `python-docx`; the package's scientific `.venv` need not contain that dependency. The delivered rev4 DOCX was exported with Word to 20 PDF pages and visually checked; `render_docx.py` was attempted but could not find LibreOffice on this Windows host.
