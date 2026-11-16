"""Single registered D2b diagnostic: direct WDC daily mean minus Mendeley meanField.

No offset fitting, PCA/SVD, D3/D4, Sq construction, or new benchmark tests.
"""
from __future__ import annotations

import calendar
import csv
import datetime as dt
import hashlib
import json
import math
import platform
import re
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "phase2a/S7B"
MEN = ROOT / "phase2a/raw/mendeley/jcmdrm5f5x-1"
RAW = ROOT / "phase2a/raw"
SOURCE = Path(r"D:\Downloads\Keputusan S7-B dan Instruksi Eksekusi Claude Code (G0-registration-2).docx")
MONTHS = (1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
COMPONENTS = "XYZ"
EXPECTED_SOURCE_SHA = "c722cbcc25b7328c02425d40bd98d54c13fcc1e8aa20fdd9af965858cb67e5f1"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def json_write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def log(message: str) -> None:
    with (OUT / "S7B_execution.log").open("a", encoding="utf-8") as stream:
        stream.write(message + "\n")
    print(message)


def verify_frozen(manifest: list[dict], frozen: dict[str, str], stage: str) -> dict:
    errors = []
    for row in manifest:
        path = ROOT / row["relative_path"]
        if not path.is_file():
            errors.append(f"MISSING {row['relative_path']}")
        elif sha(path).lower() != row["sha256"].lower():
            errors.append(f"SHA_MISMATCH {row['relative_path']}")
    for path, expected in frozen.items():
        if sha(ROOT / path) != expected:
            errors.append(f"FROZEN_SHA_MISMATCH {path}")
    if sha(SOURCE) != EXPECTED_SOURCE_SHA:
        errors.append(f"APPROVED_DOC_SHA_MISMATCH {SOURCE}")
    if errors:
        raise RuntimeError(f"{stage} frozen verification failed: {errors[:10]}")
    log(f"INFO {stage}: {len(manifest)} G0 manifest files + {len(frozen)} G0/D1/D2/S7-A frozen outputs SHA-256 match")
    return {"stage": stage, "G0_manifest_files": len(manifest),
            "frozen_output_files": len(frozen), "mismatches": 0, "pass": True}


def frozen_outputs() -> dict[str, str]:
    out = {}
    for gate in ("G0", "D1", "D2", "S7"):
        for path in (ROOT / "phase2a" / gate).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                out[rel(path)] = sha(path)
    return dict(sorted(out.items()))


def policy_validate() -> dict:
    rows = read_csv(OUT / "S7B_benchmark_policy.csv")
    if len(rows) != 684 or len({r["relative_path"] for r in rows}) != 684:
        raise RuntimeError("S7B policy must have 684 unique DAT")
    s7 = {r["relative_path"]: r for r in read_csv(ROOT / "phase2a/S7/S7_benchmark_manifest.csv")}
    if {r["relative_path"] for r in rows} != set(s7):
        raise RuntimeError("S7B policy path set differs from S7-A")
    counts = Counter(r["allowed_use"] for r in rows)
    if counts != {"ORIGINAL_ABSOLUTE": 624, "ABSOLUTE_REPORTED_ONLY": 36,
                  "SUSPECT_DIAGNOSTIC": 18, "EXCLUDED": 6}:
        raise RuntimeError(f"S7B policy counts invalid: {counts}")
    for row in rows:
        if row["sha256"] != s7[row["relative_path"]]["sha256"]:
            raise RuntimeError(f"S7B policy SHA differs: {row['relative_path']}")
        if row["month"] == "02" and row["d3_eligible"] != "false":
            raise RuntimeError(f"February D3 leak: {row['relative_path']}")
        if row["allowed_use"] == "EXCLUDED" and not row["excluded_reason"]:
            raise RuntimeError(f"Excluded DAT without reason: {row['relative_path']}")
    return {"rows": len(rows), "allowed_use": dict(counts),
            "development_seen_files": sum(r["development_seen"] == "true" for r in rows)}


def find_meanfield(component: str, month: int, combined: bool) -> Path:
    suffix = "_y_all" if combined else ""
    name = f"COI_{component}_meanField_m{month:02d}{suffix}.dat"
    matches = list(MEN.rglob(name))
    if len(matches) != 1:
        raise RuntimeError(f"Expected one Mendeley {name}, found {len(matches)}")
    return matches[0]


def tab(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream, delimiter="\t"))
    if not rows or len({len(row) for row in rows}) != 1:
        raise RuntimeError(f"Empty/ragged meanField DAT: {path}")
    return rows[0], rows[1:]


def printed_resolution(rows: list[list[str]]) -> dict:
    decimals = Counter()
    for row in rows:
        for token in row[1:]:
            if token == "NA":
                continue
            if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", token):
                raise RuntimeError(f"Unsupported meanField numeric token: {token!r}")
            decimals[len(token.partition(".")[2])] += 1
    if not decimals:
        raise RuntimeError("No numeric meanField values")
    max_decimals = max(decimals)
    return {"min_printed_decimals": min(decimals), "max_printed_decimals": max_decimals,
            "decimal_count_distribution": dict(sorted(decimals.items())),
            "file_printed_resolution_nT": 10 ** (-max_decimals)}


def meanfield_preflight() -> tuple[dict, dict]:
    per = {}
    combined = {}
    summary = {}
    for month in MONTHS:
        days = calendar.monthrange(2007, month)[1]
        for comp in COMPONENTS:
            path = find_meanfield(comp, month, False)
            header, rows = tab(path)
            expected_header = ["day"] + [f"y.{year}" for year in range(2007, 2018)]
            aligned = header == expected_header and len(rows) == days and [r[0] for r in rows] == [str(d) for d in range(1, days+1)]
            resolution = printed_resolution(rows)
            combined_path = find_meanfield(comp, month, True)
            cheader, crows = tab(combined_path)
            expected_combined = [r[i] for i in range(1, 12) for r in rows]
            combined_index = [str(i) for i in range(1, len(expected_combined)+1)]
            combined_consistent = (len(crows) == len(expected_combined) and
                                   [r[0] for r in crows] == combined_index and
                                   len(cheader) == 2 and [r[1] for r in crows] == expected_combined)
            per[(month, comp)] = (path, header, rows, aligned, resolution)
            combined[(month, comp)] = (combined_path, combined_consistent)
            summary[f"{month:02d}:{comp}"] = {
                "annual_path": rel(path), "annual_sha256": sha(path),
                "annual_shape": [len(rows), len(header)], "calendar_days": days,
                "annual_alignment_pass": aligned, "printed_resolution": resolution,
                "combined_path": rel(combined_path), "combined_sha256": sha(combined_path),
                "combined_shape": [len(crows), len(cheader)],
                "combined_exact_year_major_consistency": combined_consistent}
    return per, {"files": summary, "combined_consistency_all_pass": all(
        combined[key][1] for key in combined),
        "annual_alignment_all_pass": all(per[key][3] for key in per)}


def wdc_year(year: int) -> tuple[dict[int, np.ndarray], dict]:
    path = RAW / "wdc_hourly" / f"COI_{year}_hour_iaga_XYZF.zip"
    arrays = {}
    details = {}
    with zipfile.ZipFile(path) as archive:
        failed = archive.testzip()
        if failed is not None:
            raise RuntimeError(f"WDC ZIP CRC failed: {path}, member={failed}")
        for month in range(1, 13):
            member = f"coi{year}{month:02d}dhor.hor"
            lines = archive.read(member).decode("ascii").splitlines()
            header_text = "\n".join(lines[:20])
            if "IAGA-2002" not in header_text or "XYZF" not in header_text or "COI" not in header_text:
                raise RuntimeError(f"WDC IAGA/XYZF header missing: {member}")
            rows = []
            stamps = []
            for line in lines:
                if re.match(rf"^{year}-{month:02d}-\d\d\s", line):
                    fields = line.split()
                    if len(fields) != 7:
                        raise RuntimeError(f"WDC row not seven fields: {member}: {line!r}")
                    date = dt.date.fromisoformat(fields[0])
                    if int(fields[2]) != date.timetuple().tm_yday:
                        raise RuntimeError(f"WDC DOY mismatch: {member}: {line!r}")
                    stamps.append(fields[0] + " " + fields[1])
                    rows.append([float(x) for x in fields[3:6]])
            n_days = calendar.monthrange(year, month)[1]
            expected = [f"{year}-{month:02d}-{day:02d} {hour:02d}:00:00.000"
                        for day in range(1, n_days+1) for hour in range(24)]
            if stamps != expected:
                raise RuntimeError(f"WDC timestamp alignment failed: {member}: rows={len(stamps)}")
            arr = np.asarray(rows, dtype=np.float64).reshape(n_days, 24, 3)
            sentinel = arr >= 88888
            arr[sentinel] = np.nan
            arrays[month] = arr
            details[f"{year}-{month:02d}"] = {"member": member, "hours": len(rows),
                 "sentinel_XYZ": [int(sentinel[:, :, i].sum()) for i in range(3)]}
    return arrays, {"path": rel(path), "sha256": sha(path), "months": details}


def gfz_quiet(year: int, month: int) -> tuple[list[int], Path]:
    path = RAW / "gfz" / f"QD_days{year}.txt"
    label = calendar.month_abbr[month]
    lines = [line for line in path.read_text(encoding="utf-8").splitlines()
             if re.match(rf"^\s*{label}\s+{year}\s", line)]
    if len(lines) != 1:
        raise RuntimeError(f"GFZ month row missing/duplicated: {year}-{month:02d}")
    days = [int(re.match(r"\d+", item).group()) for item in lines[0].split()[2:7]]
    n_days = calendar.monthrange(year, month)[1]
    if len(days) != 5 or len(set(days)) != 5 or any(not 1 <= day <= n_days for day in days):
        raise RuntimeError(f"GFZ Q1-Q5 invalid: {year}-{month:02d}: {days}")
    return days, path


def interpolate_month(values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Interpolate only bracketed within-month gaps, excluding runs crossing a full missing day."""
    if values.ndim != 2 or values.shape[1] != 24:
        raise ValueError(f"Expected day×24 array, got {values.shape}")
    n_days = values.shape[0]
    full_missing = ~np.isfinite(values).any(axis=1)
    flat = values.reshape(-1).copy()
    original_missing = ~np.isfinite(flat)
    filled = np.zeros(len(flat), dtype=bool)
    i = 0
    while i < len(flat):
        if not original_missing[i]:
            i += 1
            continue
        start = i
        while i < len(flat) and original_missing[i]:
            i += 1
        end = i
        if start == 0 or end == len(flat) or any(full_missing[d] for d in range(start//24, (end-1)//24+1)):
            continue
        left, right = start-1, end
        flat[start:end] = np.interp(np.arange(start, end), [left, right], [flat[left], flat[right]])
        filled[start:end] = True
    return (flat.reshape(n_days, 24), original_missing.reshape(n_days, 24),
            filled.reshape(n_days, 24), full_missing)


def classify(d: float, resolution: float) -> dict:
    a = abs(d)
    bound = .02 + .5 * resolution
    predicates = {"MATCH": a <= bound, "QUANT": .02 < a <= .08,
                  "SMALL_UNEXPLAINED": .08 < a <= .5, "REVISION": a > .5}
    labels = [name for name, hit in predicates.items() if hit]
    return {"match_bound_nT": bound, "predicates": predicates, "labels": labels,
            "status": labels[0] if len(labels) == 1 else ("AMBIGUOUS" if labels else "UNCLASSIFIED")}


def main() -> None:
    started_utc = dt.datetime.now(dt.timezone.utc)
    log(f"INFO D2b started_utc={started_utc.isoformat()} source=G0-registration-2; one registered run")
    frozen = frozen_outputs()
    manifest = read_csv(ROOT / "phase2a/G0/input_manifest.csv")
    if len(manifest) != 3702:
        raise RuntimeError(f"Unexpected G0 manifest rows: {len(manifest)}")
    before = verify_frozen(manifest, frozen, "BEFORE_D2B")
    policy_summary = policy_validate()
    per, mf_preflight = meanfield_preflight()
    log(f"INFO meanField print resolution and calendar preflight: {len(mf_preflight['files'])} annual + combined file pairs; alignment_all={mf_preflight['annual_alignment_all_pass']}; combined_all={mf_preflight['combined_consistency_all_pass']}")
    wdc_arrays = {}
    wdc_details = {}
    for year in range(2007, 2018):
        wdc_arrays[year], wdc_details[str(year)] = wdc_year(year)
    gfz = {}
    gfz_hashes = {}
    for year in range(2007, 2018):
        path = RAW / "gfz" / f"QD_days{year}.txt"
        gfz_hashes[str(year)] = sha(path)
        for month in MONTHS:
            gfz[(year, month)], _ = gfz_quiet(year, month)
    log("INFO WDC/GFZ preflight: 132 ordered IAGA-2002 XYZF monthly HOR members, 121 GFZ non-February Q1-Q5 rows")
    preflight = {"started_utc": started_utc.isoformat(),
                 "approved_source_sha256": sha(SOURCE), "G0_manifest_sha256": sha(ROOT / "phase2a/G0/input_manifest.csv"),
                 "frozen_outputs_sha256": frozen, "integrity_before": before,
                 "policy": policy_summary, "meanfield": mf_preflight,
                 "wdc_hourly": wdc_details, "gfz_sha256": gfz_hashes,
                 "missing_sentinels": ["88888.xx", "99999.xx"],
                 "interpolation": "linear for bracketed missing runs inside month; no month-edge extrapolation or run crossing all-missing day",
                 "printed_resolution_rule": "file-level 10^(-maximum decimal places across annual DAT numeric values); preserve per-value printed decimals in source, no post-hoc choice"}
    json_write(OUT / "D2b_preflight.json", preflight)
    rows = []
    for year in range(2007, 2018):
        for month in MONTHS:
            arr = wdc_arrays[year][month]
            quiet = set(gfz[(year, month)])
            for ci, comp in enumerate(COMPONENTS):
                path, header, dat_rows, aligned, resolution_info = per[(month, comp)]
                processed, original_missing, interpolated, full_missing = interpolate_month(arr[:, :, ci])
                resolution = resolution_info["file_printed_resolution_nT"]
                for day in range(1, arr.shape[0]+1):
                    index = day - 1
                    missing_count = int(original_missing[index].sum())
                    filled_count = int(interpolated[index].sum())
                    remaining = int((~np.isfinite(processed[index])).sum())
                    base = {"date": f"{year}-{month:02d}-{day:02d}", "year": year,
                            "month": f"{month:02d}", "day": day, "component": comp,
                            "calendar_month_key": f"{year}-{month:02d}", "is_gfz_Q1_Q5": day in quiet,
                            "gfz_Q1_Q5": "|".join(map(str, sorted(quiet))),
                            "original_missing_hours": missing_count,
                            "interpolated_hours": filled_count,
                            "remaining_missing_hours": remaining,
                            "full_day_missing_original": bool(full_missing[index]),
                            "file_printed_resolution_nT": resolution,
                            "file_max_printed_decimals": resolution_info["max_printed_decimals"],
                            "mendeley_path": rel(path), "mendeley_sha256": sha(path),
                            "wdc_path": wdc_details[str(year)]["path"],
                            "wdc_sha256": wdc_details[str(year)]["sha256"],
                            "gfz_path": rel(RAW / "gfz" / f"QD_days{year}.txt"),
                            "gfz_sha256": gfz_hashes[str(year)]}
                    if not aligned:
                        rows.append({**base, "status": "ALIGNMENT_FAIL", "classification_set": "",
                                     "reason": "meanField day rows/header not exact calendar sequence"})
                        continue
                    token = dat_rows[index][header.index(f"y.{year}")]
                    if token == "NA":
                        rows.append({**base, "status": "MENDELEY_MISSING", "classification_set": "",
                                     "reason": "meanField token NA"})
                        continue
                    if full_missing[index]:
                        rows.append({**base, "status": "ALL_DAY_MISSING", "classification_set": "",
                                     "meanfield_mendeley_nT": float(token),
                                     "reason": "all 24 WDC hourly XYZ values missing; no synthetic day"})
                        continue
                    if remaining:
                        rows.append({**base, "status": "UNRESOLVED_MISSING", "classification_set": "",
                                     "meanfield_mendeley_nT": float(token),
                                     "reason": "month-edge or full-day-crossing gap cannot be interpolated under registered rule"})
                        continue
                    mean_wdc = float(np.mean(processed[index]))
                    mean_men = float(token)
                    difference = mean_wdc - mean_men
                    c = classify(difference, resolution)
                    rows.append({**base, "mean_daily_wdc_nT": mean_wdc,
                                 "meanfield_mendeley_nT": mean_men, "d_wdc_minus_mendeley_nT": difference,
                                 "abs_d_nT": abs(difference), "match_bound_nT": c["match_bound_nT"],
                                 **{f"predicate_{k}": str(v).lower() for k, v in c["predicates"].items()},
                                 "classification_set": "|".join(c["labels"]), "status": c["status"],
                                 "ambiguous": len(c["labels"]) > 1, "reason": ""})
        log(f"INFO D2b computed year {year}: {sum(r['year']==year for r in rows)} component-days")
    expected_days = sum((365 + calendar.isleap(y)) - calendar.monthrange(y, 2)[1] for y in range(2007, 2018))
    if len(rows) != expected_days * 3:
        raise RuntimeError(f"D2b row count {len(rows)} != {expected_days*3}")
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with (OUT / "D2b_meanfield_comparison.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    valid = [r for r in rows if "d_wdc_minus_mendeley_nT" in r]
    status_count = Counter(r["status"] for r in rows)
    predicate_count = {key: sum(r.get(f"predicate_{key}") == "true" for r in valid)
                       for key in ("MATCH", "QUANT", "SMALL_UNEXPLAINED", "REVISION")}
    overlaps = [r for r in valid if r.get("ambiguous")]
    revision = [r for r in valid if r.get("predicate_REVISION") == "true"]
    affected_months = sorted({r["calendar_month_key"] for r in revision})
    medians = {comp: statistics.median(r["d_wdc_minus_mendeley_nT"] for r in valid
                                     if r["component"] == comp) for comp in COMPONENTS}
    ha_forward = (-.08 <= medians["X"] <= -.02 and -.08 <= medians["Z"] <= -.02 and
                  .02 <= medians["Y"] <= .08)
    ha_reverse = (.02 <= medians["X"] <= .08 and .02 <= medians["Z"] <= .08 and
                  -.08 <= medians["Y"] <= -.02)
    summary = {
        "schema": "Auto-SqPCA-D2b-v1", "started_utc": started_utc.isoformat(),
        "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "started_local_Asia_Makassar": started_utc.astimezone(ZoneInfo("Asia/Makassar")).isoformat(),
        "scope": "Non-February 2007-2017 X/Y/Z direct daily mean comparison; no fitting/PCA/SVD",
        "protocol": "G0-registration-2 APPROVED", "preflight_sha256": sha(OUT / "D2b_preflight.json"),
        "input_sha256": {"decision_docx": sha(SOURCE), "G0_manifest": sha(ROOT / "phase2a/G0/input_manifest.csv"),
                         "S7_manifest": sha(ROOT / "phase2a/S7/S7_benchmark_manifest.csv"),
                         "policy": sha(OUT / "S7B_benchmark_policy.csv")},
        "integrity_before": before,
        "calendar_days": expected_days, "component_day_target_total": len(rows),
        "valid_comparison_rows": len(valid), "missing_or_alignment_rows": len(rows)-len(valid),
        "status_counts": dict(status_count), "predicate_counts_nonexclusive": predicate_count,
        "match_union_quant_count": sum(r.get("predicate_MATCH") == "true" or
                                       r.get("predicate_QUANT") == "true" for r in valid),
        "ambiguous_count": len(overlaps),
        "ambiguous_examples": [{"date": r["date"], "component": r["component"],
                                 "d_nT": r["d_wdc_minus_mendeley_nT"],
                                 "resolution_nT": r["file_printed_resolution_nT"],
                                 "classification_set": r["classification_set"]} for r in overlaps[:20]],
        "median_d_wdc_minus_mendeley_nT": medians,
        "H_a": {"status": "SUPPORTED" if ha_forward or ha_reverse else "NOT_SUPPORTED",
                "forward_sign_pattern": ha_forward, "reverse_sign_pattern": ha_reverse,
                "rule": "X/Z [-0.08,-0.02] and Y [+0.02,+0.08] nT, or reverse"},
        "revision": {"component_days": len(revision), "calendar_days": len({r["date"] for r in revision}),
                     "affected_year_months": len(affected_months), "total_year_months": 121,
                     "affected_percent": 100*len(affected_months)/121,
                     "months": affected_months,
                     "iqd_revision_component_days": sum(r["is_gfz_Q1_Q5"] for r in revision),
                     "interpolated_hours_on_revision_days": sum(r["interpolated_hours"] for r in revision)},
        "interpolation": {"total_interpolated_hours_component_day": sum(r["interpolated_hours"] for r in rows),
                          "days_with_interpolation_component_day": sum(r["interpolated_hours"]>0 for r in rows),
                          "full_day_missing_component_day": status_count["ALL_DAY_MISSING"],
                          "unresolved_missing_component_day": status_count["UNRESOLVED_MISSING"]},
        "combined_meanfield_consistency_all_pass": mf_preflight["combined_consistency_all_pass"],
        "annual_alignment_all_pass": mf_preflight["annual_alignment_all_pass"],
        "environment": {"python": sys.version, "numpy": np.__version__, "platform": platform.platform()},
        "errors": [],
        "limitations": ["Direct difference only; no additive offset fitted or inferred from author-era data.",
                        "MATCH and QUANT predicates are preserved without a new priority rule.",
                        "All-missing days and month-edge/full-day-crossing gaps are not synthesized."]}
    after = verify_frozen(manifest, frozen, "AFTER_D2B")
    summary["integrity_after"] = after
    json_write(OUT / "D2b_summary.json", summary)
    log(f"INFO D2b completed: {len(rows)} component-days, {len(valid)} valid, {len(revision)} REVISION, {len(affected_months)}/121 affected year-months, {len(overlaps)} ambiguous")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        log(f"ERROR {type(error).__name__}: {error}")
        raise
