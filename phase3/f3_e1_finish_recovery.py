"""Finish E1 holdout recovery after all missing station-month workers exit.

Some completed months have no complete-data S8 target and rightly produce zero
case rows. Their completion is established by the worker log and truth audit.
"""
from __future__ import annotations

import datetime as dt
import json
import os

from f3_e1 import WORK, csv_write, log, prepare_truth, stage_rows
from f3_e1_resume import inspect, key
from f3_preflight import OUT, sha, verify_snapshot


def main() -> None:
    verify_snapshot()
    audit_path = OUT / "F3_E1_recovery.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    original = WORK / "E1_holdout_cases.csv"
    backup = WORK / "E1_holdout_interrupted.csv"
    temp = WORK / "E1_holdout_resuming.csv"
    status_path = WORK / "E1_holdout_truth_status.csv"
    if status_path.exists():
        raise RuntimeError("Holdout truth status already exists; refusing to finalize twice")
    if sha(original) != audit["original_partial_sha256"] or sha(backup) != audit["original_partial_sha256"]:
        raise RuntimeError("Interrupted holdout original/backup hash mismatch")
    log_text = (OUT / "F3A_execution.log").read_text(encoding="utf-8")
    completion_marker = f"E1 holdout recovery: completed {audit['remaining_months']}/{audit['remaining_months']} remaining station-months"
    if completion_marker not in log_text:
        raise RuntimeError("Holdout recovery worker completion marker missing")
    todo = stage_rows("holdout")
    lookup = {key(r): r for r in todo}
    if len(lookup) != len(todo) or len(todo) != 149:
        raise RuntimeError(f"Holdout inventory changed: {len(todo)}")
    counts, candidates, final_rows = inspect(temp, set(lookup))
    if final_rows < audit["original_partial_rows"] or len(counts) < audit["original_complete_months"]:
        raise RuntimeError("Recovery CSV lost original complete cases")
    notes = []
    zero_case_months = []
    for row in todo:
        k = key(row)
        resolved = 0
        for ci, c in enumerate("XYZ"):
            base = {"split": "holdout", "station": k[0], "year": k[1], "month": k[2], "component": c}
            if (k, c) in candidates:
                if not candidates[(k, c)]:
                    raise RuntimeError(f"Blank truth candidate for completed case block: {k} {c}")
                notes.append({**base, "status": "OK", "truth_candidate": candidates[(k, c)], "error": ""})
                resolved += 1
            else:
                try:
                    prepare_truth(row, ci)
                except Exception as e:
                    notes.append({**base, "status": "UNRESOLVED_TRUTH", "truth_candidate": "", "error": f"{type(e).__name__}: {e}"})
                else:
                    raise RuntimeError(f"Missing case rows for resolvable truth: {k} {c}")
        if resolved == 0:
            zero_case_months.append(f"{k[0]}:{k[1]}-{k[2]:02d}")
    if len(notes) != 447 or sum(n["status"] == "OK" for n in notes) * 1323 != final_rows:
        raise RuntimeError(f"Truth/case count mismatch: notes={len(notes)}, case rows={final_rows}")
    os.replace(temp, original)
    csv_write(status_path, notes,
              ["split", "station", "year", "month", "component", "status", "truth_candidate", "error"])
    audit.update({"completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "recovery_precheck_error_original": "RuntimeError: Holdout recovery incomplete: months=129, truth notes=447",
                  "final_months": len(todo), "final_months_with_cases": len(counts),
                  "zero_case_months": zero_case_months, "final_rows": final_rows,
                  "final_holdout_sha256": sha(original), "truth_status_sha256": sha(status_path),
                  "preserved_partial_sha256": sha(backup),
                  "finalization_script_sha256": sha(OUT / "f3_e1_finish_recovery.py")})
    audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log(f"E1 holdout recovery complete: {final_rows} rows, {len(todo)} processed months ({len(zero_case_months)} without case rows), SHA-256={audit['final_holdout_sha256']}")
    verify_snapshot()


if __name__ == "__main__":
    main()
