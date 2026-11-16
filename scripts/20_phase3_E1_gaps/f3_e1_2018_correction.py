"""Add the missing GFZ 2018 holdout months without changing frozen E1 code.

The original 2007-2017/2014-2017 holdout rows and pre-correction evaluation are
retained byte-for-byte. This is a documented post-evaluation input correction.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed

import f3_e1
from f3_e1 import CASE_FIELDS, WORK, csv_read, csv_write, log, process_month, stage_rows
from f3_e1_resume import inspect, key
from f3_preflight import OUT, sha, verify_snapshot


def gfz_days_2018(year: int, month: int) -> list[int]:
    if year != 2018:
        return _ORIGINAL_GFZ_DAYS(year, month)
    names = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    path = OUT / "raw/gfz/QD_days2018.txt"
    line = next((x for x in path.read_text(encoding="utf-8").splitlines()
                 if re.match(rf"^\s*{names[month-1]}\s+2018\s", x)), None)
    if line is None:
        raise RuntimeError(f"GFZ QD missing {year}-{month:02d}")
    days = [int(re.match(r"^\d+", v).group()) for v in line.split()[2:7]]
    if len(days) != 5 or len(set(days)) != 5:
        raise RuntimeError(f"GFZ Q1-Q5 invalid {year}-{month:02d}: {days}")
    return days


_ORIGINAL_GFZ_DAYS = f3_e1.gfz_days


def worker_init(expected_gfz_hash: str) -> None:
    path = OUT / "raw/gfz/QD_days2018.txt"
    if sha(path) != expected_gfz_hash:
        raise RuntimeError("GFZ 2018 file changed before worker")
    f3_e1.gfz_days = gfz_days_2018


def main() -> None:
    verify_snapshot()
    config_path = OUT / "F3_E1_frozen.json"
    if sha(config_path) != (OUT / "F3_E1_frozen.json.sha256").read_text().split()[0]:
        raise RuntimeError("E1 frozen config hash mismatch")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    for name, digest in config["code_sha256"].items():
        if sha(OUT / name) != digest:
            raise RuntimeError(f"E1 frozen code changed: {name}")
    plan = json.loads((OUT / "F3_E1_analysis_plan.json").read_text(encoding="utf-8"))
    if sha(OUT / "f3_e1_eval.py") != plan["evaluation_code_sha256"]:
        raise RuntimeError("E1 evaluator changed since preregistration")
    source = json.loads((OUT / "F3_GFZ2018_source.json").read_text(encoding="utf-8"))
    gfz_hash = source["sha256"]
    if sha(OUT / source["path"]) != gfz_hash or source["months_validated"] != 12:
        raise RuntimeError("GFZ 2018 source hash/validation mismatch")
    original = WORK / "E1_holdout_cases.csv"
    status_path = WORK / "E1_holdout_truth_status.csv"
    preliminary = json.loads((OUT / "F3_C1_result.json").read_text(encoding="utf-8"))
    if sha(original) != preliminary["holdout_cases_sha256"]:
        raise RuntimeError("Preliminary holdout hash does not match preliminary C1 result")
    todo = stage_rows("holdout")
    targets = [r for r in todo if int(r["year"]) == 2018]
    if len(targets) != 20 or any(r["station"] not in ("KDU", "GUA") for r in targets):
        raise RuntimeError(f"Unexpected 2018 holdout target set: {len(targets)}")
    notes_old = csv_read(status_path)
    old_2018 = [r for r in notes_old if r["year"] == "2018"]
    if len(notes_old) != 447 or len(old_2018) != 60 or any("FileNotFoundError" not in r["error"] for r in old_2018):
        raise RuntimeError("Expected exactly 60 GFZ-missing 2018 truth notes")
    counts, _, old_rows = inspect(original, {key(r) for r in todo})
    if any(k[1] == 2018 for k in counts):
        raise RuntimeError("2018 case rows already present")
    saved = WORK / "E1_pre_GFZ2018"
    if saved.exists():
        raise RuntimeError("Pre-GFZ2018 forensic snapshot already exists")
    saved.mkdir()
    preliminary_files = ("F3_C1_result.json", "F3_E1_holdout_summary.csv", "F3_E1_pstar.csv",
                         "F3_E1_TND_summary.csv", "F3_E1_superiority.csv",
                         "F3A_figure1_error_curves.png", "F3A_figure2_TND.png")
    for name in preliminary_files:
        shutil.copy2(OUT / name, saved / name)
    shutil.copy2(original, saved / original.name)
    shutil.copy2(status_path, saved / status_path.name)
    initial_hash = sha(original)
    correction = {"started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "reason": "GFZ 2018 quiet-day input omitted before initial holdout; all 60 2018 component targets failed FileNotFoundError",
                  "protocol_holdout_2018_months": len(targets),
                  "preliminary_C1_success": preliminary["C1_success"],
                  "preliminary_holdout_sha256": initial_hash, "preliminary_holdout_rows": old_rows,
                  "preliminary_C1_sha256": sha(saved / "F3_C1_result.json"),
                  "preliminary_snapshot_sha256": {p.name: sha(p) for p in saved.iterdir()},
                  "GFZ2018_sha256": gfz_hash, "GFZ2018_source_url": source["url"],
                  "frozen_config_sha256": sha(config_path), "evaluator_sha256": sha(OUT / "f3_e1_eval.py"),
                  "correction_script_sha256": sha(OUT / "f3_e1_2018_correction.py"),
                  "recomputed_prior_case_months": False,
                  "note": "Correction was identified after inspecting preliminary C1; method, masks, seeds, and evaluation rule remain frozen."}
    record = OUT / "F3_E1_2018_correction.json"
    record.write_text(json.dumps(correction, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log(f"E1 2018 correction: preserved preliminary {old_rows} case rows SHA-256={initial_hash}; computing 20 GFZ-missing months")
    supplement = WORK / "E1_holdout_2018_supplement.csv"
    supplement_notes = []
    with supplement.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CASE_FIELDS)
        writer.writeheader()
        with ProcessPoolExecutor(max_workers=int(os.environ.get("F3_WORKERS", "8")),
                                 initializer=worker_init, initargs=(gfz_hash,)) as pool:
            futures = {pool.submit(process_month, row, "holdout"): row for row in targets}
            for i, future in enumerate(as_completed(futures), 1):
                row = futures[future]
                try:
                    cases, info = future.result()
                except Exception as e:
                    raise RuntimeError(f"E1 2018 correction worker failure {key(row)}: {type(e).__name__}: {e}") from e
                writer.writerows(cases)
                f.flush()
                supplement_notes.extend(info)
                if i % 5 == 0 or i == len(targets):
                    log(f"E1 2018 correction: completed {i}/{len(targets)} station-months; {supplement.stat().st_size} bytes")
    csv_write(WORK / "E1_holdout_2018_supplement_truth_status.csv", supplement_notes,
              ["split", "station", "year", "month", "component", "status", "truth_candidate", "error"])
    if len(supplement_notes) != 60 or any("FileNotFoundError" in r["error"] for r in supplement_notes):
        raise RuntimeError("GFZ 2018 correction did not resolve missing input for all components")
    combined = WORK / "E1_holdout_with_GFZ2018.csv"
    with combined.open("wb") as dst, original.open("rb") as src, supplement.open("rb") as add:
        shutil.copyfileobj(src, dst)
        add.readline()  # Skip the supplement CSV header only.
        shutil.copyfileobj(add, dst)
    all_counts, _, all_rows = inspect(combined, {key(r) for r in todo})
    if all_rows != old_rows + sum(r["status"] == "OK" for r in supplement_notes) * 1323:
        raise RuntimeError("Combined 2018 correction case count mismatch")
    merged_notes = [r for r in notes_old if r["year"] != "2018"] + supplement_notes
    if len(merged_notes) != 447 or all_rows != sum(r["status"] == "OK" for r in merged_notes) * 1323:
        raise RuntimeError("Combined 2018 correction truth/case mismatch")
    updated_status = WORK / "E1_holdout_truth_with_GFZ2018.csv"
    csv_write(updated_status, merged_notes,
              ["split", "station", "year", "month", "component", "status", "truth_candidate", "error"])
    os.replace(combined, original)
    os.replace(updated_status, status_path)
    correction.update({"completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                       "supplement_cases": all_rows - old_rows,
                       "supplement_truth_OK": sum(r["status"] == "OK" for r in supplement_notes),
                       "supplement_truth_unresolved": sum(r["status"] != "OK" for r in supplement_notes),
                       "final_case_months": len(all_counts), "final_holdout_rows": all_rows,
                       "final_holdout_sha256": sha(original), "final_truth_status_sha256": sha(status_path),
                       "supplement_sha256": sha(supplement),
                       "preliminary_rows_preserved_as_prefix": original.open("rb").read((saved / original.name).stat().st_size) == (saved / original.name).read_bytes()})
    if not correction["preliminary_rows_preserved_as_prefix"]:
        raise RuntimeError("Original holdout case rows changed during GFZ 2018 correction")
    record.write_text(json.dumps(correction, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log(f"E1 2018 correction complete: {all_rows} total cases, {len(all_counts)} case-bearing months, SHA-256={correction['final_holdout_sha256']}")
    verify_snapshot()


if __name__ == "__main__":
    main()
