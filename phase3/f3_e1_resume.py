"""Resume an interrupted, frozen E1 holdout from complete station-month blocks.

This script never recomputes a month already present in the source CSV. It keeps
the interrupted file as a forensic artifact and documents the recovery boundary.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import shutil
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

from f3_e1 import CASE_FIELDS, WORK, csv_write, log, prepare_truth, process_month, stage_rows
from f3_preflight import OUT, sha, verify_snapshot


def key(row: dict) -> tuple[str, int, int]:
    return row["station"], int(row["year"]), int(row["month"])


def inspect(path, expected: set) -> tuple[dict, dict, int]:
    counts = Counter()
    per_component = defaultdict(Counter)
    candidates = {}
    unique = set()
    rows = 0
    with path.open("rb") as f:
        f.seek(-1, os.SEEK_END)
        if f.read(1) != b"\n":
            raise RuntimeError("Interrupted CSV ends in an incomplete line")
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != CASE_FIELDS:
            raise RuntimeError("Interrupted CSV header differs from frozen CASE_FIELDS")
        for r in reader:
            rows += 1
            k = key(r)
            if k not in expected:
                raise RuntimeError(f"Unexpected holdout month in interrupted CSV: {k}")
            if None in r or any(r[x] is None for x in CASE_FIELDS):
                raise RuntimeError(f"Malformed interrupted CSV row {rows}")
            identity = (k, r["component"], r["mask_kind"], r["p_nominal"], r["replicate"], r["method"])
            if identity in unique:
                raise RuntimeError(f"Duplicate interrupted CSV identity: {identity}")
            unique.add(identity)
            counts[k] += 1
            per_component[(k, r["component"])][r["method"]] += 1
            candidates[(k, r["component"])] = r["truth_candidate"]
    for (k, component), by_method in per_component.items():
        if component not in "XYZ" or by_method != Counter({"M-INT": 441, "M-EXC": 441, "M-EM": 441}):
            raise RuntimeError(f"Incomplete component block: {k} {component} {dict(by_method)}")
    for k, count in counts.items():
        if count != 1323 * sum((k, c) in per_component for c in "XYZ"):
            raise RuntimeError(f"Incomplete month block: {k} {count}")
    return counts, candidates, rows


def completed_notes(todo, candidates):
    notes = []
    for row in todo:
        k = key(row)
        for c in "XYZ":
            base = {"split": "holdout", "station": k[0], "year": k[1], "month": k[2], "component": c}
            if (k, c) in candidates:
                notes.append({**base, "status": "OK", "truth_candidate": candidates[(k, c)], "error": ""})
            else:
                try:
                    prepare_truth(row, "XYZ".index(c))
                except Exception as e:
                    notes.append({**base, "status": "UNRESOLVED_TRUTH", "truth_candidate": "", "error": f"{type(e).__name__}: {e}"})
                else:
                    raise RuntimeError(f"Original month {k} lacks component {c}, but truth now resolves")
    return notes


def main() -> None:
    verify_snapshot()
    freeze = OUT / "F3_E1_frozen.json"
    if sha(freeze) != (OUT / "F3_E1_frozen.json.sha256").read_text().split()[0]:
        raise RuntimeError("E1 frozen config hash mismatch")
    config = json.loads(freeze.read_text(encoding="utf-8"))
    for name, digest in config["code_sha256"].items():
        if sha(OUT / name) != digest:
            raise RuntimeError(f"E1 code changed after freeze: {name}")
    todo = stage_rows("holdout")
    lookup = {key(r): r for r in todo}
    if len(lookup) != len(todo) or len(todo) != 149:
        raise RuntimeError(f"Holdout station-month inventory mismatch: {len(todo)}")
    original = WORK / "E1_holdout_cases.csv"
    backup = WORK / "E1_holdout_interrupted.csv"
    temp = WORK / "E1_holdout_resuming.csv"
    if backup.exists() or temp.exists() or (WORK / "E1_holdout_truth_status.csv").exists():
        raise RuntimeError("Recovery artifacts already exist; inspect before resuming again")
    counts, candidates, old_rows = inspect(original, set(lookup))
    if not 0 < len(counts) < len(todo):
        raise RuntimeError(f"Expected partial holdout, found {len(counts)}/{len(todo)} months")
    partial_hash = sha(original)
    shutil.copy2(original, backup)
    if sha(backup) != partial_hash:
        raise RuntimeError("Interrupted CSV backup hash mismatch")
    remaining = [r for r in todo if key(r) not in counts]
    audit = {"started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
             "reason": "Original process interrupted after user turn interruption; no Python process remained",
             "original_partial_sha256": partial_hash, "original_partial_rows": old_rows,
             "original_complete_months": len(counts), "remaining_months": len(remaining),
             "recovery_script_sha256": sha(OUT / "f3_e1_resume.py"),
             "frozen_config_sha256": sha(freeze), "rerun_completed_months": False}
    (OUT / "F3_E1_recovery.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    log(f"E1 holdout recovery: preserved {len(counts)} complete months/{old_rows} rows SHA-256={partial_hash}; computing {len(remaining)} unseen months")
    notes = completed_notes([lookup[k] for k in counts], candidates)
    with original.open(encoding="utf-8", newline="") as src, temp.open("w", encoding="utf-8", newline="") as dst:
        reader = csv.DictReader(src)
        writer = csv.DictWriter(dst, fieldnames=CASE_FIELDS)
        writer.writeheader()
        writer.writerows(reader)
        dst.flush()
        with ProcessPoolExecutor(max_workers=int(os.environ.get("F3_WORKERS", "8"))) as pool:
            futures = {pool.submit(process_month, row, "holdout"): row for row in remaining}
            for i, future in enumerate(as_completed(futures), 1):
                row = futures[future]
                try:
                    cases, info = future.result()
                except Exception as e:
                    raise RuntimeError(f"E1 recovery worker failure {key(row)}: {type(e).__name__}: {e}") from e
                writer.writerows(cases)
                dst.flush()
                notes.extend(info)
                if i % 5 == 0 or i == len(remaining):
                    log(f"E1 holdout recovery: completed {i}/{len(remaining)} remaining station-months; rows written {temp.stat().st_size} bytes")
    final_counts, _, final_rows = inspect(temp, set(lookup))
    if len(final_counts) != len(todo) or len(notes) != 3 * len(todo):
        raise RuntimeError(f"Holdout recovery incomplete: months={len(final_counts)}, truth notes={len(notes)}")
    os.replace(temp, original)
    csv_write(WORK / "E1_holdout_truth_status.csv", notes,
              ["split", "station", "year", "month", "component", "status", "truth_candidate", "error"])
    audit.update({"completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "final_months": len(final_counts), "final_rows": final_rows,
                  "final_holdout_sha256": sha(original), "truth_status_sha256": sha(WORK / "E1_holdout_truth_status.csv"),
                  "preserved_partial_sha256": sha(backup)})
    (OUT / "F3_E1_recovery.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    log(f"E1 holdout recovery complete: {final_rows} rows, {len(final_counts)} months, SHA-256={audit['final_holdout_sha256']}")
    verify_snapshot()


if __name__ == "__main__":
    main()
