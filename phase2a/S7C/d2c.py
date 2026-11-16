"""Registration-3 WDC fixed-width crosscheck; D2c only if its stop gate passes.

Uses metadata tabular base per date/element. No fitted constants, PCA or SVD.
"""
from __future__ import annotations

import calendar
import csv
import datetime as dt
import json
import math
import platform
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from s7c_prepare import ROOT, OUT, SOURCE, sha
from s7c_acquire_corrected import ARCHIVE

RAW = ROOT / "phase2a/raw"
COMPONENTS = "XYZF"
IAGA_ARCHIVES = {year: RAW / "wdc_hourly" / f"COI_{year}_hour_iaga_XYZF.zip"
                 for year in range(2007, 2018)}


def log(message: str) -> None:
    with (OUT / "S7C_execution.log").open("a", encoding="utf-8") as stream:
        stream.write(message + "\n")
    print(message)


def write_json(name: str, obj: object) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_wdc_line(line: bytes) -> dict:
    if len(line) != 120:
        raise ValueError(f"WDC hourly line length {len(line)} != 120: {line[:35]!r}")
    if line[0:3] != b"COI":
        raise ValueError(f"WDC code not COI: {line[:3]!r}")
    year = int(line[14:16]) * 100 + int(line[3:5])
    month = int(line[5:7])
    component = line[7:8].decode("ascii")
    day = int(line[8:10])
    if component not in COMPONENTS:
        raise ValueError(f"WDC element invalid: {component!r}")
    date = dt.date(year, month, day)
    base = int(line[16:20])
    tabular = [int(line[20+i*4:24+i*4]) for i in range(24)]
    daily_mean = int(line[116:120])
    if any(abs(v) > 9999 for v in tabular):
        raise ValueError(f"WDC hourly tabular outside I4: {date} {component}")
    return {"date": date, "component": component, "base": base,
            "tabular": tabular, "daily_mean_field": daily_mean,
            "raw_prefix": line[:20].decode("ascii")}


def parse_wdc_archive() -> tuple[dict[tuple[dt.date, str], dict], dict]:
    records = {}
    year_counts = {}
    with zipfile.ZipFile(ARCHIVE) as archive:
        failed = archive.testzip()
        if failed is not None:
            raise RuntimeError(f"WDC format ZIP CRC failed: {failed}")
        names = sorted(n for n in archive.namelist() if n.endswith("h.wdc"))
        expected = [f"coi{year}h.wdc" for year in range(2007, 2018)]
        if names != expected:
            raise RuntimeError(f"WDC format 11-year member set incomplete: {names}")
        for year in range(2007, 2018):
            lines = archive.read(f"coi{year}h.wdc").splitlines()
            year_counts[str(year)] = len(lines)
            for line in lines:
                item = parse_wdc_line(line)
                if item["date"].year != year:
                    raise RuntimeError(f"WDC format year mismatch in coi{year}h.wdc: {item['date']}")
                key = (item["date"], item["component"])
                if key in records:
                    raise RuntimeError(f"Duplicate WDC format date/element: {key}")
                records[key] = item
    expected_days = sum(366 if calendar.isleap(year) else 365 for year in range(2007, 2018))
    if len(records) != expected_days * 4:
        raise RuntimeError(f"WDC format records {len(records)} != {expected_days*4}")
    for year in range(2007, 2018):
        for month in range(1, 13):
            for day in range(1, calendar.monthrange(year, month)[1]+1):
                date = dt.date(year, month, day)
                for component in COMPONENTS:
                    if (date, component) not in records:
                        raise RuntimeError(f"Missing WDC format date/element: {date} {component}")
    return records, {"records": len(records), "calendar_days": expected_days,
                     "year_line_counts": year_counts, "archive_sha256": sha(ARCHIVE)}


def parse_iaga() -> tuple[dict[tuple[dt.date, int, str], float | None], dict]:
    values = {}
    details = {}
    for year, path in IAGA_ARCHIVES.items():
        year_rows = 0
        with zipfile.ZipFile(path) as archive:
            failed = archive.testzip()
            if failed is not None:
                raise RuntimeError(f"IAGA hourly ZIP CRC failed: {path}, {failed}")
            for month in range(1, 13):
                member = f"coi{year}{month:02d}dhor.hor"
                lines = archive.read(member).decode("ascii").splitlines()
                for line in lines:
                    if not line.startswith(f"{year}-{month:02d}-"):
                        continue
                    fields = line.split()
                    if len(fields) != 7:
                        raise RuntimeError(f"IAGA hourly row malformed: {member}: {line!r}")
                    date = dt.date.fromisoformat(fields[0])
                    hour = int(fields[1][:2])
                    if fields[1] != f"{hour:02d}:00:00.000" or not 0 <= hour < 24 or int(fields[2]) != date.timetuple().tm_yday:
                        raise RuntimeError(f"IAGA timestamp/DOY invalid: {member}: {line!r}")
                    for ci, comp in enumerate(COMPONENTS):
                        number = float(fields[3+ci])
                        key = (date, hour, comp)
                        if key in values:
                            raise RuntimeError(f"Duplicate IAGA hourly value: {key}")
                        values[key] = None if number >= 88888 else number
                    year_rows += 1
        expected = (366 if calendar.isleap(year) else 365) * 24
        if year_rows != expected:
            raise RuntimeError(f"IAGA {year} hours {year_rows} != {expected}")
        details[str(year)] = {"rows": year_rows, "archive_sha256": sha(path)}
    return values, {"hours": len(values)//4, "component_hour_values": len(values),
                    "year_archives": details}


def base_table(records: dict) -> tuple[list[dict], dict]:
    groups: dict[tuple[int, int, str, int], list[str]] = defaultdict(list)
    monthly: dict[tuple[int, int, str], set[int]] = defaultdict(set)
    overall: dict[str, set[int]] = defaultdict(set)
    for (date, comp), item in records.items():
        base = item["base"]
        groups[(date.year, date.month, comp, base)].append(date.isoformat())
        monthly[(date.year, date.month, comp)].add(base)
        overall[comp].add(base)
    rows = []
    for (year, month, comp, base), dates in sorted(groups.items()):
        rows.append({"year": year, "month": f"{month:02d}", "component": comp,
                     "tabular_base_I4": base, "base_times_100_nT": base*100,
                     "days": len(dates), "first_date": min(dates), "last_date": max(dates),
                     "source_archive_sha256": sha(ARCHIVE)})
    with (OUT / "S7C_wdc_base_table.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    info = {"overall_unique_bases": {c: sorted(overall[c]) for c in COMPONENTS},
            "base_constant_all_2007_2017": {c: len(overall[c]) == 1 for c in COMPONENTS},
            "months_with_multiple_bases": [f"{year}-{month:02d}:{comp}" for (year, month, comp), bases in sorted(monthly.items()) if len(bases)>1],
            "month_base_sets": {f"{year}-{month:02d}:{comp}": sorted(bases) for (year, month, comp), bases in sorted(monthly.items())},
            "rows": len(rows)}
    return rows, info


def crosscheck(records: dict, iaga: dict) -> dict:
    path = OUT / "S7C_wdc_crosscheck.csv"
    fields = ["date", "year", "month", "day", "hour_UTC", "component", "tabular_base_I4",
              "tabular_value_I4", "wdc_reconstructed_nT", "iaga_hourly_nT", "abs_difference_nT",
              "status", "wdc_format_archive_sha256", "iaga_archive_sha256"]
    counts = Counter()
    by_component = defaultdict(Counter)
    paired_differences = []
    examples = []
    archive_digest = sha(ARCHIVE)
    iaga_digests = {year: sha(path) for year, path in IAGA_ARCHIVES.items()}
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for (date, comp), item in sorted(records.items()):
            for hour, tabular in enumerate(item["tabular"]):
                observed = iaga.get((date, hour, comp))
                reconstructed = None if tabular == 9999 else item["base"]*100 + tabular
                if reconstructed is None and observed is None:
                    status, difference = "BOTH_MISSING", None
                elif reconstructed is None:
                    status, difference = "WDC_FORMAT_MISSING_ONLY", None
                elif observed is None:
                    status, difference = "IAGA_MISSING_ONLY", None
                else:
                    difference = abs(reconstructed - observed)
                    status = "MISMATCH_GT_0P1" if difference > 0.10000001 else "WITHIN_0P1"
                    paired_differences.append(difference)
                counts[status] += 1
                by_component[comp][status] += 1
                row = {"date": date.isoformat(), "year": date.year,
                       "month": f"{date.month:02d}", "day": date.day, "hour_UTC": hour,
                       "component": comp, "tabular_base_I4": item["base"],
                       "tabular_value_I4": tabular,
                       "wdc_reconstructed_nT": reconstructed if reconstructed is not None else "",
                       "iaga_hourly_nT": observed if observed is not None else "",
                       "abs_difference_nT": difference if difference is not None else "",
                       "status": status, "wdc_format_archive_sha256": archive_digest,
                       "iaga_archive_sha256": iaga_digests[date.year]}
                writer.writerow(row)
                if status == "MISMATCH_GT_0P1" and len(examples) < 20:
                    examples.append({k: row[k] for k in ("date", "hour_UTC", "component", "tabular_base_I4",
                                                       "tabular_value_I4", "wdc_reconstructed_nT", "iaga_hourly_nT", "abs_difference_nT")})
    total = sum(counts.values())
    expected = 4018*24*4
    if total != expected:
        raise RuntimeError(f"Crosscheck row total {total} != {expected}")
    paired = counts["WITHIN_0P1"] + counts["MISMATCH_GT_0P1"]
    mismatch = counts["MISMATCH_GT_0P1"]
    pct = 100*mismatch/paired if paired else None
    return {"total_component_hours": total, "paired_valid_component_hours": paired,
            "status_counts": dict(counts), "by_component": {k: dict(v) for k, v in by_component.items()},
            "mismatch_gt_0p1_nT_count": mismatch,
            "mismatch_gt_0p1_nT_percent_of_paired": pct,
            "mismatch_gt_0p1_nT_percent_of_all": 100*mismatch/total,
            "threshold_percent": .1, "format_inconsistent": bool(paired and pct > .1),
            "max_abs_difference_nT": max(paired_differences) if paired_differences else None,
            "median_abs_difference_nT": statistics.median(paired_differences) if paired_differences else None,
            "examples": examples, "csv_sha256": sha(path)}


def classify(value: float, printed_resolution: float) -> dict:
    magnitude = abs(value)
    bound = .02 + .5*printed_resolution
    flags = {"MATCH": magnitude <= bound, "QUANT": .02 < magnitude <= .08,
             "SMALL_UNEXPLAINED": .08 < magnitude <= .5,
             "REVISION_LIKE": magnitude > .5}
    labels = [key for key, hit in flags.items() if hit]
    return {"flags": flags, "labels": labels,
            "status": labels[0] if len(labels)==1 else ("AMBIGUOUS" if labels else "UNCLASSIFIED"),
            "match_bound_nT": bound}


def d2c_if_allowed(records: dict, cross: dict) -> dict:
    path = OUT / "D2c_comparison.csv"
    fields = ["date", "year", "month", "day", "component", "d_D2b_nT", "tabular_base_I4",
              "base_times_100_nT", "d_prime_nT", "abs_d_prime_nT", "printed_resolution_nT",
              "match_bound_nT", "predicate_MATCH", "predicate_QUANT", "predicate_SMALL_UNEXPLAINED",
              "predicate_REVISION_LIKE", "classification_set", "status", "is_gfz_Q1_Q5",
              "interpolated_hours_D2b", "wdc_format_archive_sha256", "mendeley_sha256"]
    if cross["format_inconsistent"]:
        with path.open("w", encoding="utf-8", newline="") as stream:
            csv.DictWriter(stream, fieldnames=fields).writeheader()
        return {"status": "NOT_RUN_WDC_FORMAT_INCONSISTENT", "valid_D2b_rows_available": 10953,
                "D2c_comparison_rows": 0, "reason": "Pre-D2c stop 0a: WDC format/IAGA >0.1 nT mismatch on >0.1% paired hours",
                "comparison_csv_sha256": sha(path)}
    source = ROOT / "phase2a/S7B/D2b_meanfield_comparison.csv"
    rows = []
    with source.open(encoding="utf-8", newline="") as stream:
        for original in csv.DictReader(stream):
            if not original["d_wdc_minus_mendeley_nT"]:
                continue
            date = dt.date.fromisoformat(original["date"])
            comp = original["component"]
            base = records[(date, comp)]["base"]
            d = float(original["d_wdc_minus_mendeley_nT"])
            prime = d - base*100
            resolution = float(original["file_printed_resolution_nT"])
            c = classify(prime, resolution)
            rows.append({"date": original["date"], "year": original["year"],
                         "month": original["month"], "day": original["day"], "component": comp,
                         "d_D2b_nT": d, "tabular_base_I4": base,
                         "base_times_100_nT": base*100, "d_prime_nT": prime,
                         "abs_d_prime_nT": abs(prime), "printed_resolution_nT": resolution,
                         "match_bound_nT": c["match_bound_nT"],
                         **{f"predicate_{k}": str(v).lower() for k, v in c["flags"].items()},
                         "classification_set": "|".join(c["labels"]), "status": c["status"],
                         "is_gfz_Q1_Q5": original["is_gfz_Q1_Q5"],
                         "interpolated_hours_D2b": original["interpolated_hours"],
                         "wdc_format_archive_sha256": sha(ARCHIVE),
                         "mendeley_sha256": original["mendeley_sha256"]})
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    if len(rows) != 10953:
        raise RuntimeError(f"D2c valid D2b row count {len(rows)} != 10953")
    counts = Counter(r["status"] for r in rows)
    predicates = {key: sum(r[f"predicate_{key}"] == "true" for r in rows)
                  for key in ("MATCH", "QUANT", "SMALL_UNEXPLAINED", "REVISION_LIKE")}
    affected = sorted({r["date"][:7] for r in rows if r["predicate_REVISION_LIKE"] == "true"})
    medians = {comp: statistics.median(r["d_prime_nT"] for r in rows if r["component"]==comp)
               for comp in "XYZ"}
    forward = (-.08 <= medians["X"] <= -.02 and -.08 <= medians["Z"] <= -.02 and .02 <= medians["Y"] <= .08)
    reverse = (.02 <= medians["X"] <= .08 and .02 <= medians["Z"] <= .08 and -.08 <= medians["Y"] <= -.02)
    return {"status": "COMPLETED", "D2c_comparison_rows": len(rows),
            "classification_counts_exclusive": dict(counts), "predicate_counts_nonexclusive": predicates,
            "ambiguous_count": counts["AMBIGUOUS"],
            "match_union_quant_count": sum(r["predicate_MATCH"]=="true" or r["predicate_QUANT"]=="true" for r in rows),
            "median_d_prime_nT": medians,
            "H_a": "SUPPORTED" if forward or reverse else "NOT_SUPPORTED",
            "affected_year_months": len(affected), "affected_months": affected,
            "revision_like_component_days": predicates["REVISION_LIKE"],
            "revision_like_iqd_component_days": sum(r["is_gfz_Q1_Q5"]=="True" for r in rows if r["predicate_REVISION_LIKE"]=="true"),
            "comparison_csv_sha256": sha(path)}


def main() -> None:
    pre = json.loads((OUT / "S7C_preflight.json").read_text(encoding="utf-8"))
    acquire = json.loads((OUT / "S7C_acquisition_correction.json").read_text(encoding="utf-8"))
    if acquire["status"] != "DOWNLOADED_COMPLETE_VALID_ZIP" or sha(ARCHIVE) != acquire["archive_sha256"]:
        raise RuntimeError("Complete WDC format archive unavailable or changed")
    for path, digest in pre["frozen_outputs_sha256_before"].items():
        if sha(ROOT / path) != digest:
            raise RuntimeError(f"Frozen output changed before D2c: {path}")
    records, format_meta = parse_wdc_archive()
    iaga, iaga_meta = parse_iaga()
    bases, base_meta = base_table(records)
    cross = crosscheck(records, iaga)
    log(f"INFO WDC format crosscheck: {cross['paired_valid_component_hours']} paired valid XYZF hours; {cross['mismatch_gt_0p1_nT_count']} differ >0.1 nT ({cross['mismatch_gt_0p1_nT_percent_of_paired']:.3f}%); threshold 0.1%")
    cross_summary = {"schema": "Auto-SqPCA-S7C-WDC-crosscheck-v1",
                     "executed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                     "format_meta": format_meta, "iaga_meta": iaga_meta,
                     "base_meta": base_meta, "crosscheck": cross,
                     "source_URL": acquire["corrected_url"],
                     "source_archive_sha256": acquire["archive_sha256"],
                     "first_partial_query_archive_sha256": json.loads((OUT / "S7C_acquisition.json").read_text(encoding="utf-8"))["archive_sha256"],
                     "rule": "stop if >0.1 nT discrepancy on >0.1% valid paired component-hours; 9999 means missing"}
    write_json("S7C_wdc_crosscheck_summary.json", cross_summary)
    result = d2c_if_allowed(records, cross)
    result.update({"schema": "Auto-SqPCA-D2c-v1", "crosscheck_status": "WDC_FORMAT_INCONSISTENT" if cross["format_inconsistent"] else "PASS",
                   "source_archive_sha256": acquire["archive_sha256"],
                   "D2b_summary_sha256": sha(ROOT / "phase2a/S7B/D2b_summary.json"),
                   "D2b_comparison_sha256": sha(ROOT / "phase2a/S7B/D2b_meanfield_comparison.csv"),
                   "environment": {"python": sys.version, "numpy": np.__version__, "platform": platform.platform()},
                   "executed_utc": dt.datetime.now(dt.timezone.utc).isoformat()})
    write_json("D2c_summary.json", result)
    for path, digest in pre["frozen_outputs_sha256_before"].items():
        if sha(ROOT / path) != digest:
            raise RuntimeError(f"Frozen output changed after D2c: {path}")
    if sha(ARCHIVE) != acquire["archive_sha256"]:
        raise RuntimeError("WDC format raw archive changed after D2c")
    log(f"INFO D2c status={result['status']}; frozen G0/D1/D2/S7/S7B hashes unchanged; WDC format raw hash unchanged")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        log(f"ERROR {type(error).__name__}: {error}")
        raise
