"""D2 input and diagnostic computation; no D3/D4 or full PCA.

All WDC, Mendeley and GFZ files are read only. Output is written solely under
phase2a/D2. Aggregation A/B/C uses the frozen Phase-1 minute ZIPs and G0 hourly
ZIPs. An exact 60 valid minutes is required for A and B comparisons.
"""
from __future__ import annotations

import calendar
import csv
import datetime as dt
import hashlib
import json
import logging
import platform
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
D2 = ROOT / "phase2a/D2"
G0 = ROOT / "phase2a/G0"
D1 = ROOT / "phase2a/D1"
RAW = ROOT / "phase2a/raw"
MEN = RAW / "mendeley/jcmdrm5f5x-1"
START = dt.date(2007, 1, 1)
STOP = dt.date(2018, 1, 1)
NDAYS = (STOP - START).days
NHOURS = NDAYS * 24
NMINUTES = NHOURS * 60
COMP = "XYZF"
NIGHT = (0, 1, 2, 3, 23)
FOCUS = [(2008, 2), (2012, 2), (2016, 2), (2012, 1), (2013, 1),
         (2008, 5), (2017, 6), (2017, 10)]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def log_setup() -> logging.Logger:
    D2.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("d2")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(levelname)s %(message)s")
    for handler in (logging.FileHandler(D2 / "D2_execution.log", mode="w", encoding="utf-8"),
                    logging.StreamHandler(sys.stdout)):
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    return logger


def csv_write(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def json_safe(value):
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def input_hash_map() -> dict[str, str]:
    with (G0 / "input_manifest.csv").open("r", encoding="utf-8", newline="") as stream:
        return {row["relative_path"]: row["sha256"] for row in csv.DictReader(stream)}


def check_frozen_inputs(expected: dict[str, str], logger: logging.Logger, stage: str) -> dict:
    # Every raw file from G0, plus frozen COI minute ZIPs, is checked twice.
    keys = sorted(k for k in expected if k.startswith("phase2a/raw/") or
                  bool(re.fullmatch(r"audit_sq_wdc/cache/COI_20(?:0[7-9]|1[0-7])_minute_iaga_XYZF\.zip", k)))
    actual_raw = {rel(p) for p in RAW.rglob("*") if p.is_file()}
    expected_raw = {k for k in keys if k.startswith("phase2a/raw/")}
    if actual_raw != expected_raw:
        raise RuntimeError(f"Raw path set changed: missing={sorted(expected_raw-actual_raw)[:5]}, added={sorted(actual_raw-expected_raw)[:5]}")
    for key in keys:
        found = sha(ROOT / key)
        if found.lower() != expected[key].lower():
            raise RuntimeError(f"Frozen SHA-256 mismatch: {key}, expected={expected[key]}, actual={found}")
    logger.info("%s: %d raw + %d COI minute ZIP SHA-256 match G0", stage, len(expected_raw), len(keys)-len(expected_raw))
    return {"raw_files": len(expected_raw), "minute_zip_files": len(keys)-len(expected_raw),
            "all_match_G0": True}


def is_missing(token: bytes) -> bool:
    return token.startswith((b"99999", b"88888")) or token.lower() in (b"nan", b"na", b"null")


def read_minute(logger: logging.Logger) -> tuple[np.ndarray, dict]:
    minute = np.full((NMINUTES, 4), np.nan, dtype=np.float64)
    observed = np.zeros(NMINUTES, dtype=bool)
    member_dates = set()
    row_count = 0
    sentinels = Counter()
    header_intervals = Counter()
    verified_headers = 0
    sample_digits = Counter()
    for year in range(2007, 2018):
        path = ROOT / f"audit_sq_wdc/cache/COI_{year}_minute_iaga_XYZF.zip"
        with zipfile.ZipFile(path) as archive:
            names = sorted(n for n in archive.namelist() if n.lower().endswith(".min"))
            if len(names) != (366 if calendar.isleap(year) else 365):
                raise RuntimeError(f"Minute ZIP {year}: expected calendar daily members, got {len(names)}")
            for name in names:
                match = re.fullmatch(r"coi(\d{4})(\d{2})(\d{2})dmin\.min", name, re.I)
                if not match:
                    raise RuntimeError(f"Minute member name invalid: {name}")
                date = dt.date(*map(int, match.groups()))
                if date.year != year or date in member_dates:
                    raise RuntimeError(f"Minute member year/duplicate invalid: {name}")
                member_dates.add(date)
                day_index = (date - START).days
                values = np.full((1440, 4), np.nan, dtype=np.float64)
                local_seen = np.zeros(1440, dtype=bool)
                header_flags = set()
                with archive.open(name) as stream:
                    for line in stream:
                        if line.startswith(b" Format") and b"IAGA-2002" in line:
                            header_flags.add("format")
                        if line.startswith(b" IAGA Code") and b"COI" in line:
                            header_flags.add("station")
                        if line.startswith(b" Reported") and b"XYZF" in line:
                            header_flags.add("orientation")
                        if line.startswith(b" Data Interval Type"):
                            header_intervals[line.decode("ascii", "replace").split("|")[0].strip()] += 1
                            if b"1-minute" in line:
                                header_flags.add("cadence")
                        if line.startswith(b"DATE") and all(x in line for x in (b"COIX", b"COIY", b"COIZ", b"COIF")):
                            header_flags.add("columns")
                        if not line[:4].isdigit() or line[4:5] != b"-":
                            continue
                        fields = line.split()
                        if len(fields) != 7 or fields[0] != date.isoformat().encode("ascii"):
                            raise RuntimeError(f"Minute row invalid in {name}: {line[:110]!r}")
                        clock = fields[1]
                        hour, minu = int(clock[:2]), int(clock[3:5])
                        if clock[5:] != b":00.000" or not (0 <= hour <= 23 and 0 <= minu <= 59):
                            raise RuntimeError(f"Minute timestamp invalid in {name}: {clock!r}")
                        pos = hour * 60 + minu
                        if local_seen[pos]:
                            raise RuntimeError(f"Duplicate minute in {name}: {clock!r}")
                        local_seen[pos] = True
                        row_count += 1
                        for i, token in enumerate(fields[3:7]):
                            if is_missing(token):
                                sentinels[COMP[i]] += 1
                            else:
                                values[pos, i] = float(token)
                                if row_count <= 1000:
                                    sample_digits[len(token.partition(b".")[2])] += 1
                start = day_index * 1440
                if header_flags != {"format", "station", "orientation", "cadence", "columns"}:
                    raise RuntimeError(f"Minute IAGA/XYZF header invalid in {name}: found={sorted(header_flags)}")
                verified_headers += 1
                minute[start:start+1440] = values
                observed[start:start+1440] = local_seen
        logger.info("Minute %d parsed: %d daily members", year, len(names))
    if len(member_dates) != NDAYS:
        raise RuntimeError(f"Minute calendar missing daily members: {len(member_dates)} vs {NDAYS}")
    valid = np.isfinite(minute)
    quantization = {}
    for i, c in enumerate(COMP):
        v = minute[:, i][valid[:, i]]
        quantization[c] = float(np.max(np.abs(v * 10 - np.rint(v * 10)))) if len(v) else None
    meta = {"daily_members": len(member_dates), "data_rows": row_count,
            "expected_minutes": NMINUTES, "missing_timestamp_rows": int(NMINUTES-observed.sum()),
            "sentinel_by_component": dict(sentinels),
            "missing_or_absent_by_component": {c: int((~valid[:, i]).sum()) for i, c in enumerate(COMP)},
            "interval_headers": dict(header_intervals), "sample_printed_decimal_digits": dict(sample_digits),
            "verified_IAGA_2002_XYZF_headers": verified_headers,
            "max_deviation_from_0p1nT_grid": quantization}
    return minute, meta


def read_hourly(logger: logging.Logger) -> tuple[np.ndarray, dict]:
    hour = np.full((NHOURS, 4), np.nan, dtype=np.float64)
    observed = np.zeros(NHOURS, dtype=bool)
    sentinels = Counter()
    interval_headers = Counter()
    verified_headers = 0
    sample_digits = Counter()
    row_count = 0
    for year in range(2007, 2018):
        path = RAW / "wdc_hourly" / f"COI_{year}_hour_iaga_XYZF.zip"
        with zipfile.ZipFile(path) as archive:
            names = sorted(n for n in archive.namelist() if n.lower().endswith(".hor"))
            if len(names) != 12:
                raise RuntimeError(f"Hourly ZIP {year}: expected 12 members, got {len(names)}")
            for name in names:
                header_flags = set()
                with archive.open(name) as stream:
                    for line in stream:
                        if line.startswith(b" Format") and b"IAGA-2002" in line:
                            header_flags.add("format")
                        if line.startswith(b" IAGA Code") and b"COI" in line:
                            header_flags.add("station")
                        if line.startswith(b" Reported") and b"XYZF" in line:
                            header_flags.add("orientation")
                        if line.startswith(b" Data Interval Type"):
                            interval_headers[line.decode("ascii", "replace").split("|")[0].strip()] += 1
                            if b"1-hour" in line:
                                header_flags.add("cadence")
                        if line.startswith(b"DATE") and all(x in line for x in (b"COIX", b"COIY", b"COIZ", b"COIF")):
                            header_flags.add("columns")
                        if not line[:4].isdigit() or line[4:5] != b"-":
                            continue
                        fields = line.split()
                        if len(fields) != 7:
                            raise RuntimeError(f"Hourly row invalid in {name}: {line[:110]!r}")
                        date = dt.date.fromisoformat(fields[0].decode("ascii"))
                        clock = fields[1]
                        if clock[2:] != b":00:00.000":
                            raise RuntimeError(f"Hourly timestamp invalid in {name}: {clock!r}")
                        hour_of_day = int(clock[:2])
                        if not (0 <= hour_of_day < 24):
                            raise RuntimeError(f"Hourly hour invalid in {name}: {clock!r}")
                        pos = (date - START).days * 24 + hour_of_day
                        if not (0 <= pos < NHOURS) or observed[pos]:
                            raise RuntimeError(f"Hourly out of range/duplicate in {name}: {fields[0]!r} {clock!r}")
                        observed[pos] = True
                        row_count += 1
                        for i, token in enumerate(fields[3:7]):
                            if is_missing(token):
                                sentinels[COMP[i]] += 1
                            else:
                                hour[pos, i] = float(token)
                                if row_count <= 1000:
                                    sample_digits[len(token.partition(b".")[2])] += 1
                if header_flags != {"format", "station", "orientation", "cadence", "columns"}:
                    raise RuntimeError(f"Hourly IAGA/XYZF header invalid in {name}: found={sorted(header_flags)}")
                verified_headers += 1
        logger.info("Hourly %d parsed: 12 monthly members", year)
    if not observed.all():
        raise RuntimeError(f"Hourly timestamps incomplete: {int(observed.sum())}/{NHOURS}")
    quantization = {}
    for i, c in enumerate(COMP):
        v = hour[:, i][np.isfinite(hour[:, i])]
        quantization[c] = float(np.max(np.abs(v * 10 - np.rint(v * 10)))) if len(v) else None
    meta = {"monthly_members": 132, "data_rows": row_count, "expected_hours": NHOURS,
            "sentinel_by_component": dict(sentinels), "interval_headers": dict(interval_headers),
            "sample_printed_decimal_digits": dict(sample_digits),
            "verified_IAGA_2002_XYZF_headers": verified_headers,
            "max_deviation_from_0p1nT_grid": quantization}
    return hour, meta


def aggregates(minute: np.ndarray) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    blocks = minute.reshape(NHOURS * 2, 30, 4)
    half_sum = np.nansum(blocks, axis=1)
    half_count = np.isfinite(blocks).sum(axis=1)
    a_sum = half_sum[0::2] + half_sum[1::2]
    a_count = half_count[0::2] + half_count[1::2]
    b_sum = np.zeros_like(a_sum)
    b_count = np.zeros_like(a_count)
    # HH-30 through HH+29: preceding 30-min block plus current first block.
    # The continuous minute axis naturally crosses day, month and year edges.
    b_sum[1:] = half_sum[1:-1:2] + half_sum[2::2]
    b_count[1:] = half_count[1:-1:2] + half_count[2::2]
    # The first window has no 2006 minutes in scope; retain its observed
    # current 30 minutes so the incomplete count is truthful.
    b_sum[0] = half_sum[0]
    b_count[0] = half_count[0]
    curves = {"A_00_59": np.divide(a_sum, a_count, out=np.full_like(a_sum, np.nan), where=a_count > 0),
              "B_HHm30_to_HHp29": np.divide(b_sum, b_count, out=np.full_like(b_sum, np.nan), where=b_count > 0),
              "C_HH00": minute[0::60].copy()}
    counts = {"A_00_59": a_count, "B_HHm30_to_HHp29": b_count,
              "C_HH00": np.isfinite(curves["C_HH00"]).astype(np.int16)}
    return curves, counts


def quantization_diagnostics(hour: np.ndarray, a: np.ndarray, a_count: np.ndarray) -> dict:
    result = {}
    for i, component in enumerate(COMP):
        valid = np.isfinite(hour[:, i]) & (a_count[:, i] == 60)
        mean = a[valid, i]
        published = hour[valid, i]
        # The minute inputs are all integer tenths of nT. Recover their 60-value
        # integer sum to avoid binary-float boundary errors in truncation.
        summed_tenths = np.rint(mean * 600)
        trunc_toward_zero = np.trunc(summed_tenths / 60) / 10
        nearest_tenth = np.rint(summed_tenths / 60) / 10
        trunc_error = published - trunc_toward_zero
        result[component] = {
            "matched_hours": int(valid.sum()),
            "pct_equal_trunc_toward_zero_0p1nT": float(100 * np.mean(np.abs(trunc_error) < 1e-7)),
            "pct_equal_round_nearest_0p1nT": float(100 * np.mean(np.abs(published - nearest_tenth) < 1e-7)),
            "trunc_nonmatches": int(np.sum(np.abs(trunc_error) >= 1e-7)),
            "trunc_max_abs_residual_nT": float(np.max(np.abs(trunc_error))) if len(trunc_error) else None,
            "A_error_min_nT": float(np.min(published-mean)) if len(mean) else None,
            "A_error_max_nT": float(np.max(published-mean)) if len(mean) else None,
        }
    return result


def missing_threshold_diagnostics(hour: np.ndarray, a_count: np.ndarray) -> dict:
    result = {}
    for i, component in enumerate(COMP):
        n = a_count[:, i]
        valid = np.isfinite(hour[:, i])
        incomplete_valid = n[(n < 60) & valid]
        incomplete_missing = n[(n < 60) & ~valid]
        result[component] = {
            "incomplete_hourly_valid": int(len(incomplete_valid)),
            "incomplete_hourly_missing": int(len(incomplete_missing)),
            "min_minutes_when_hourly_valid": int(incomplete_valid.min()) if len(incomplete_valid) else None,
            "max_minutes_when_hourly_missing": int(incomplete_missing.max()) if len(incomplete_missing) else None,
            "valid_with_fewer_than_54_minutes": int(np.sum(valid & (n < 54))),
            "missing_with_54_or_more_minutes": int(np.sum(~valid & (n >= 54))),
        }
    return result


def stats(hourly: np.ndarray, candidate: np.ndarray, count: np.ndarray,
          selector: np.ndarray, required: int) -> dict:
    h = hourly[selector]
    c = candidate[selector]
    n = count[selector]
    h_valid = np.isfinite(h)
    full = n == required
    paired = h_valid & full & np.isfinite(c)
    residual = h[paired] - c[paired]
    result = {"hours_total": int(len(h)), "hourly_valid": int(h_valid.sum()),
              "minute_window_complete": int(full.sum()),
              "minute_window_incomplete": int((~full).sum()),
              "hourly_valid_but_minute_incomplete": int((h_valid & ~full).sum()),
              "matched_hours": int(paired.sum())}
    if not len(residual):
        result.update({k: "" for k in ("mean_error_nT", "median_error_nT", "mae_nT", "rmse_nT",
                                               "p95_abs_error_nT", "max_abs_error_nT", "pearson_r", "pct_abs_le_0p1")})
        return result
    abs_err = np.abs(residual)
    corr = float(np.corrcoef(h[paired], c[paired])[0, 1]) if len(residual) > 1 and np.std(h[paired]) and np.std(c[paired]) else float("nan")
    result.update({"mean_error_nT": float(np.mean(residual)), "median_error_nT": float(np.median(residual)),
                   "mae_nT": float(np.mean(abs_err)), "rmse_nT": float(np.sqrt(np.mean(residual**2))),
                   "p95_abs_error_nT": float(np.quantile(abs_err, 0.95)),
                   "max_abs_error_nT": float(np.max(abs_err)), "pearson_r": corr,
                   "pct_abs_le_0p1": float(100 * np.mean(abs_err <= 0.100000001))})
    return result


def periods() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    dates = [START + dt.timedelta(days=d) for d in range(NDAYS)]
    years = np.repeat(np.array([d.year for d in dates], dtype=np.int16), 24)
    months = np.repeat(np.array([d.month for d in dates], dtype=np.int8), 24)
    return years, months, np.arange(NHOURS)


def compare_all(hour: np.ndarray, curves: dict, counts: dict, logger: logging.Logger) -> tuple[list[dict], dict]:
    years, months, hours = periods()
    rows = []
    for group in ("overall", "year", "month"):
        keys = [(None, None)] if group == "overall" else ([(y, None) for y in range(2007, 2018)] if group == "year" else
            [(y, m) for y in range(2007, 2018) for m in range(1, 13)])
        for year, month in keys:
            mask = np.ones(NHOURS, dtype=bool) if year is None else (years == year if month is None else ((years == year) & (months == month)))
            for i, component in enumerate(COMP):
                for candidate, series in curves.items():
                    required = 1 if candidate.startswith("C_") else 60
                    m = stats(hour[:, i], series[:, i], counts[candidate][:, i], mask, required)
                    rows.append({"period_type": group, "year": year or "", "month": month or "",
                                 "component": component, "candidate": candidate, **m})
    logger.info("Computed %d overall/year/month/component/candidate metric rows", len(rows))
    overall = {f"{row['component']}:{row['candidate']}": row for row in rows if row["period_type"] == "overall"}
    return rows, overall


def timestamp_diagnostics(hour: np.ndarray, curves: dict, counts: dict, logger: logging.Logger) -> list[dict]:
    years, months, indices = periods()
    rows = []
    for year, month in FOCUS:
        mask = (years == year) & (months == month)
        for i, component in enumerate(COMP):
            a_metric = stats(hour[:, i], curves["A_00_59"][:, i], counts["A_00_59"][:, i], mask, 60)
            for candidate, series in curves.items():
                required = 1 if candidate.startswith("C_") else 60
                m = stats(hour[:, i], series[:, i], counts[candidate][:, i], mask, required)
                valid = mask & np.isfinite(hour[:, i]) & (counts[candidate][:, i] == required)
                selected = indices[valid]
                error = hour[selected, i] - series[selected, i]
                local = np.full(len(selected), np.nan)
                if len(selected):
                    prev = np.maximum(selected - 1, 0)
                    next_ = np.minimum(selected + 1, NHOURS - 1)
                    local = (hour[next_, i] - hour[prev, i]) / 2
                good = np.isfinite(local)
                slope_corr = float(np.corrcoef(error[good], local[good])[0, 1]) if good.sum() > 2 and np.std(error[good]) and np.std(local[good]) else float("nan")
                # Median residual per UTC day is removed to distinguish a level shift
                # from a within-day shape difference. It does not prove revision.
                day_indices = selected // 24
                shape_err = error.copy()
                for day in np.unique(day_indices):
                    loc = day_indices == day
                    shape_err[loc] -= np.median(error[loc])
                shape_pct = float(100 * np.mean(np.abs(shape_err) > 0.100000001)) if len(shape_err) else float("nan")
                shape_rmse = float(np.sqrt(np.mean(shape_err**2))) if len(shape_err) else float("nan")
                ratio = float(m["mae_nT"] / a_metric["mae_nT"]) if m["mae_nT"] != "" and a_metric["mae_nT"] not in ("", 0) else float("nan")
                rows.append({"record_type": "focus_period", "year": year, "month": month,
                             "component": component, "candidate": candidate,
                             "timestamp_utc": "", "window_start_utc": "", "window_end_utc": "",
                             "minute_count": "", "matched_hours": m["matched_hours"],
                             "incomplete_windows": m["minute_window_incomplete"],
                             "mae_nT": m["mae_nT"], "rmse_nT": m["rmse_nT"],
                             "A_mae_nT": a_metric["mae_nT"], "mae_ratio_to_A": ratio,
                             "error_vs_hourly_slope_r": slope_corr,
                             "day_detrended_shape_rmse_nT": shape_rmse,
                             "pct_day_detrended_abs_gt_0p1": shape_pct,
                             "note": "Day-level median detrending is diagnostic only; differences do not prove historical revision"})
    for stamp in [dt.datetime(2008, 3, 1), dt.datetime(2012, 1, 1), dt.datetime(2013, 1, 1),
                  dt.datetime(2016, 3, 1), dt.datetime(2017, 6, 1), dt.datetime(2017, 7, 1)]:
        h = int((stamp.date() - START).days * 24 + stamp.hour)
        for candidate in ("A_00_59", "B_HHm30_to_HHp29", "C_HH00"):
            a = stamp if candidate.startswith(("A_", "C_")) else stamp - dt.timedelta(minutes=30)
            b = stamp if candidate.startswith("C_") else (stamp + dt.timedelta(minutes=59 if candidate.startswith("A_") else 29))
            rows.append({"record_type": "boundary_window", "year": stamp.year, "month": stamp.month,
                         "component": "XYZF", "candidate": candidate,
                         "timestamp_utc": stamp.isoformat(sep=" "),
                         "window_start_utc": a.isoformat(sep=" "), "window_end_utc": b.isoformat(sep=" "),
                         "minute_count": "|".join(map(str, counts[candidate][h].tolist())),
                         "matched_hours": "", "incomplete_windows": "", "mae_nT": "", "rmse_nT": "",
                         "A_mae_nT": "", "mae_ratio_to_A": "", "error_vs_hourly_slope_r": "",
                         "day_detrended_shape_rmse_nT": "", "pct_day_detrended_abs_gt_0p1": "",
                         "note": "B correctly crosses previous day/month/year where applicable"})
    for candidate in ("A_00_59", "B_HHm30_to_HHp29"):
        for i, component in enumerate(COMP):
            for h in np.flatnonzero(counts[candidate][:, i] < 60):
                stamp = dt.datetime.combine(START, dt.time()) + dt.timedelta(hours=int(h))
                window_start = stamp if candidate.startswith("A_") else stamp - dt.timedelta(minutes=30)
                window_end = stamp + dt.timedelta(minutes=59 if candidate.startswith("A_") else 29)
                n = int(counts[candidate][h, i])
                rows.append({"record_type": "incomplete_window", "year": stamp.year, "month": stamp.month,
                             "component": component, "candidate": candidate,
                             "timestamp_utc": stamp.isoformat(sep=" "),
                             "window_start_utc": window_start.isoformat(sep=" "),
                             "window_end_utc": window_end.isoformat(sep=" "),
                             "minute_count": n, "missing_minutes": 60-n,
                             "hourly_valid": bool(np.isfinite(hour[h, i])),
                             "matched_hours": "", "incomplete_windows": "", "mae_nT": "", "rmse_nT": "",
                             "A_mae_nT": "", "mae_ratio_to_A": "", "error_vs_hourly_slope_r": "",
                             "day_detrended_shape_rmse_nT": "", "pct_day_detrended_abs_gt_0p1": "",
                             "note": "Excluded from primary A/B comparison because fewer than 60 valid minutes"})
    logger.info("Computed %d focus/boundary timestamp diagnostic rows", len(rows))
    return rows


_DAT_INDEX: dict[str, list[Path]] | None = None


def find_unique_dat(pattern: str) -> Path:
    global _DAT_INDEX
    if _DAT_INDEX is None:
        _DAT_INDEX = {}
        for path in MEN.rglob("*.dat"):
            _DAT_INDEX.setdefault(path.name, []).append(path)
    matches = _DAT_INDEX.get(pattern, [])
    if len(matches) != 1:
        raise RuntimeError(f"Mendeley file count for {pattern}: {len(matches)}")
    return matches[0]


def read_gfz_feb(year: int) -> list[int]:
    path = RAW / "gfz" / f"QD_days{year}.txt"
    line = next(s for s in path.read_text(encoding="utf-8").splitlines() if re.match(rf"^\s*Feb\s+{year}\s", s))
    return [int(re.match(r"\d+", x).group()) for x in line.split()[2:7]]


def sq_curve(day_hour: np.ndarray, baseline: str) -> np.ndarray:
    if not np.all(np.isfinite(day_hour)):
        raise RuntimeError("Selected IQD day has missing hourly values; no interpolation permitted in D2")
    night_base = day_hour[:, list(NIGHT)].mean(axis=1)
    if baseline == "night":
        return (day_hour - night_base[:, None]).mean(axis=0)
    if baseline == "daily_mean":
        return (day_hour - day_hour.mean(axis=1, keepdims=True)).mean(axis=0)
    if baseline == "night_then_center":
        curve = (day_hour - night_base[:, None]).mean(axis=0)
        return curve - curve.mean()
    raise ValueError(baseline)


def benchmark_offsets(hour: np.ndarray, logger: logging.Logger) -> tuple[list[dict], dict]:
    rows = []
    equivalence = {}
    for year in (2008, 2012, 2016):
        quiet = read_gfz_feb(year)
        for i, component in enumerate("XYZ"):
            path = find_unique_dat(f"COI_{component}_Sq.SD.S_m02.dat")
            data = list(csv.reader(path.open(encoding="utf-8", newline=""), delimiter="\t"))
            col = data[0].index(f"Sq.y.{year}")
            reference = np.array([float(row[col]) for row in data[1:]])
            day_hour = np.stack([hour[((dt.date(year, 2, day)-START).days)*24:((dt.date(year, 2, day)-START).days+1)*24, i]
                                 for day in quiet])
            curves = {key: sq_curve(day_hour, key) for key in ("night", "daily_mean", "night_then_center")}
            eq = float(np.max(np.abs(curves["daily_mean"] - curves["night_then_center"])))
            equivalence[f"{year}:{component}"] = eq
            for name, curve in curves.items():
                residual = curve - reference
                shape = (curve - curve.mean()) - (reference - reference.mean())
                rows.append({"year": year, "component": component, "candidate": name,
                             "iqd_days": "|".join(map(str, quiet)), "matched_hours": 24,
                             "correlation": float(np.corrcoef(curve, reference)[0, 1]),
                             "rmse_absolute_nT": float(np.sqrt(np.mean(residual**2))),
                             "rmse_offset_removed_nT": float(np.sqrt(np.mean(shape**2))),
                             "mean_residual_nT": float(residual.mean()),
                             "mean_five_night_hours_nT": float(curve[list(NIGHT)].mean()),
                             "mean_24h_nT": float(curve.mean()),
                             "benchmark_night_mean_nT": float(reference[list(NIGHT)].mean()),
                             "benchmark_mean_24h_nT": float(reference.mean()),
                             "amplitude_nT": float(np.ptp(curve)),
                             "benchmark_amplitude_nT": float(np.ptp(reference)),
                             "amplitude_delta_nT": float(np.ptp(curve)-np.ptp(reference)),
                             "source_file": rel(path), "source_sha256": sha(path),
                             "note": "2016 includes GFZ Q5=29; D1-IQD remains provisional" if year == 2016 else "Official GFZ Q1-Q5"})
    logger.info("Benchmark offset: %d February year/component/baseline rows; max daily_mean vs night_then_center = %.3g nT",
                len(rows), max(equivalence.values()))
    return rows, equivalence


def meanfield_anomaly(hour: np.ndarray, logger: logging.Logger) -> tuple[list[dict], dict]:
    rows = []
    pair_counts = Counter()
    for month in range(1, 13):
        for category, suffix in [
            ("meanField", f"meanField_m{month:02d}.dat"),
            ("meanField_y_all", f"meanField_m{month:02d}_y_all.dat"),
            ("EOF1", f"EOF1_m{month:02d}.dat"), ("EOF1_y_all", f"EOF1_y_all_m{month:02d}.dat"),
            ("EOF2", f"EOF2_m{month:02d}.dat"), ("EOF2_y_all", f"EOF2_y_all_m{month:02d}.dat"),
            ("EOF3", f"EOF3_m{month:02d}.dat"), ("EOF3_y_all", f"EOF3_y_all_m{month:02d}.dat"),
            ("PC1", f"PC1_m{month:02d}.dat"), ("PC2", f"PC2_m{month:02d}.dat"),
            ("PC3", f"PC3_m{month:02d}.dat"),
            ("mode1", f"mode1_m{month:02d}.dat"), ("mode1_y_all", f"mode1_m{month:02d}_y_all.dat"),
            ("mode2", f"mode2_m{month:02d}.dat"), ("mode2_y_all", f"mode2_m{month:02d}_y_all.dat")]:
            y = find_unique_dat(f"COI_Y_{suffix}")
            z = find_unique_dat(f"COI_Z_{suffix}")
            y_hash, z_hash = sha(y), sha(z)
            y_line = y.read_text(encoding="utf-8").splitlines()
            z_line = z.read_text(encoding="utf-8").splitlines()
            y_shape = (len(y_line), len(y_line[0].split("\t")))
            z_shape = (len(z_line), len(z_line[0].split("\t")))
            same = y_hash == z_hash
            pair_counts[(category, same)] += 1
            rows.append({"record_type": "hash_structure", "month": month, "year": "",
                         "category": category, "Y_file": rel(y), "Z_file": rel(z),
                         "Y_sha256": y_hash, "Z_sha256": z_hash,
                         "identical_hash": same, "Y_rows": y_shape[0], "Y_columns": y_shape[1],
                         "Z_rows": z_shape[0], "Z_columns": z_shape[1],
                         "WDC_component": "", "fit_offset_nT": "", "rmse_nT": "",
                         "max_abs_nT": "", "valid_days": "",
                         "note": "Structure/hash only for EOF, PC and modes; no PCA computed"})
    y = find_unique_dat("COI_Y_meanField_m02.dat")
    z = find_unique_dat("COI_Z_meanField_m02.dat")
    y_data = list(csv.reader(y.open(encoding="utf-8", newline=""), delimiter="\t"))
    z_data = list(csv.reader(z.open(encoding="utf-8", newline=""), delimiter="\t"))
    if sha(y) != sha(z):
        raise RuntimeError("D1 Y/Z February meanField identity no longer holds")
    for year in (2008, 2012, 2016):
        col = y_data[0].index(f"y.{year}")
        ref_y = np.array([float(row[col]) for row in y_data[1:]])
        ref_z = np.array([float(row[col]) for row in z_data[1:]])
        for reference_name, reference, file in (("Y_meanField", ref_y, y), ("Z_meanField", ref_z, z)):
            for i, component in enumerate("YZ", start=1):
                feb_start = (dt.date(year, 2, 1) - START).days * 24
                daily = hour[feb_start:feb_start+28*24, i].reshape(28, 24)
                valid = np.all(np.isfinite(daily), axis=1)
                mean = np.nanmean(daily, axis=1)
                offset = float(np.median((mean-reference)[valid]))
                err = (mean-reference-offset)[valid]
                rows.append({"record_type": "WDC_daily_mean_fit", "month": 2, "year": year,
                             "category": reference_name, "Y_file": rel(y), "Z_file": rel(z),
                             "Y_sha256": sha(y), "Z_sha256": sha(z), "identical_hash": True,
                             "Y_rows": 29, "Y_columns": 12, "Z_rows": 29, "Z_columns": 12,
                             "WDC_component": component, "fit_offset_nT": offset,
                             "rmse_nT": float(np.sqrt(np.mean(err**2))),
                             "max_abs_nT": float(np.max(np.abs(err))), "valid_days": int(valid.sum()),
                             "note": "Offset fitted solely to identify which WDC component is represented; no correction applied"})
    logger.info("MeanField anomaly: %d Y/Z structural hash pairs; identical=%d", sum(pair_counts.values()),
                sum(n for (k, same), n in pair_counts.items() if same))
    return rows, {f"{k}:{same}": n for (k, same), n in pair_counts.items()}


def main() -> None:
    logger = log_setup()
    logger.info("D2 started; no downloads, D3/D4, full PCA, DTW, DIFI or classifier")
    expected = input_hash_map()
    frozen_paths = [G0 / "G0_report.md", G0 / "G0_validation.json", G0 / "input_manifest.csv",
                    D1 / "D1_feb29_report.md", D1 / "D1_validation.json", D1 / "d1_feb29.py",
                    ROOT / "audit_final/dataset_freeze.json"]
    before = {rel(p): sha(p) for p in frozen_paths}
    integrity_before = check_frozen_inputs(expected, logger, "Before D2")
    minute, minute_meta = read_minute(logger)
    hourly, hour_meta = read_hourly(logger)
    curves, counts = aggregates(minute)
    del minute
    quantization = quantization_diagnostics(hourly, curves["A_00_59"], counts["A_00_59"])
    missing_rule = missing_threshold_diagnostics(hourly, counts["A_00_59"])
    logger.info("A truncation match by component: %s", {k: round(x["pct_equal_trunc_toward_zero_0p1nT"], 4) for k, x in quantization.items()})
    logger.info("Observed 54/60-minute hourly availability rule violations: %s", {k: (x["valid_with_fewer_than_54_minutes"], x["missing_with_54_or_more_minutes"]) for k, x in missing_rule.items()})
    metrics, overall = compare_all(hourly, curves, counts, logger)
    timestamp = timestamp_diagnostics(hourly, curves, counts, logger)
    benchmark, equivalence = benchmark_offsets(hourly, logger)
    anomalies, anomaly_counts = meanfield_anomaly(hourly, logger)
    metric_fields = ["period_type", "year", "month", "component", "candidate", "hours_total", "hourly_valid",
                     "minute_window_complete", "minute_window_incomplete", "hourly_valid_but_minute_incomplete",
                     "matched_hours", "mean_error_nT", "median_error_nT", "mae_nT", "rmse_nT",
                     "p95_abs_error_nT", "max_abs_error_nT", "pearson_r", "pct_abs_le_0p1"]
    csv_write(D2 / "D2_hourly_vs_minute.csv", metrics, metric_fields)
    csv_write(D2 / "D2_timestamp_diagnostics.csv", timestamp,
              ["record_type", "year", "month", "component", "candidate", "timestamp_utc", "window_start_utc",
               "window_end_utc", "minute_count", "missing_minutes", "hourly_valid", "matched_hours", "incomplete_windows", "mae_nT", "rmse_nT",
               "A_mae_nT", "mae_ratio_to_A", "error_vs_hourly_slope_r", "day_detrended_shape_rmse_nT",
               "pct_day_detrended_abs_gt_0p1", "note"])
    csv_write(D2 / "D2_benchmark_offset.csv", benchmark,
              ["year", "component", "candidate", "iqd_days", "matched_hours", "correlation", "rmse_absolute_nT",
               "rmse_offset_removed_nT", "mean_residual_nT", "mean_five_night_hours_nT", "mean_24h_nT",
               "benchmark_night_mean_nT", "benchmark_mean_24h_nT", "amplitude_nT", "benchmark_amplitude_nT",
               "amplitude_delta_nT", "source_file", "source_sha256", "note"])
    csv_write(D2 / "D2_meanfield_anomaly.csv", anomalies,
              ["record_type", "month", "year", "category", "Y_file", "Z_file", "Y_sha256", "Z_sha256",
               "identical_hash", "Y_rows", "Y_columns", "Z_rows", "Z_columns", "WDC_component",
               "fit_offset_nT", "rmse_nT", "max_abs_nT", "valid_days", "note"])
    integrity_after = check_frozen_inputs(expected, logger, "After D2")
    after = {rel(p): sha(p) for p in frozen_paths}
    if before != after:
        raise RuntimeError("Frozen Phase1/G0/D1 configuration or output changed during D2")
    logger.info("Frozen Phase1/G0/D1 key file SHA-256 unchanged")
    used_inputs = {key: expected[key] for key in expected if key.startswith("phase2a/raw/wdc_hourly/") or
                   bool(re.fullmatch(r"audit_sq_wdc/cache/COI_20(?:0[7-9]|1[0-7])_minute_iaga_XYZF\.zip", key)) or
                   bool(re.fullmatch(r"phase2a/raw/gfz/QD_days20(?:08|12|16)\.txt", key))}
    for path in MEN.rglob("*.dat"):
        if "PCA modes" in str(path) and path.name.startswith(("COI_Y_", "COI_Z_")):
            used_inputs[rel(path)] = expected[rel(path)]
        elif path.name.endswith("Sq.SD.S_m02.dat") and path.name.startswith(("COI_X_", "COI_Y_", "COI_Z_")):
            used_inputs[rel(path)] = expected[rel(path)]
    validation = {"schema": "Auto-SqPCA-D2-validation-v1",
                  "scope": "D2 hourly/minute, timestamp, benchmark offset and source-file anomaly only",
                  "protocol_version": "G0-registration-1", "input_sha256": used_inputs,
                  "frozen_key_files_sha256_before": before, "frozen_key_files_sha256_after": after,
                  "integrity_before": integrity_before, "integrity_after": integrity_after,
                  "parameters": {"time_basis": "UTC", "orientation": "XYZF", "format": "IAGA-2002",
                    "sentinels": ["99999.xx", "88888.xx"], "components": list(COMP),
                    "A": "minute HH:00 through HH:59", "B": "minute HH-30 through HH+29, crossing boundaries on continuous UTC axis",
                    "C": "minute exactly HH:00", "A_B_primary_require_valid_minutes": 60,
                    "rounding_compatibility_threshold_nT": 0.1,
                    "night_baseline_hour_indices": list(NIGHT), "February_Sq_IQD": "GFZ Q1-Q5; 2016 includes Q5=29 provisionally",
                    "offset_removed_metric": "subtract each 24h curve mean only for diagnostic shape comparison",
                    "meanField_fit": "median constant offset across complete 24h days; not a correction"},
                  "minute_metadata": minute_meta, "hourly_metadata": hour_meta,
                  "quantization_diagnostics": quantization,
                  "missing_threshold_diagnostics": missing_rule,
                  "archive_hourly_interval_definition": "UNKNOWN: archive header says 1-hour but does not state averaging window; external INTERMAGNET standard says minutes 00–59",
                  "external_standard": "https://tech-man.intermagnet.org/latest/chapters/submitdata/standardsformeans.html",
                  "overall_metrics": overall, "monthly_metric_rows": sum(r["period_type"] == "month" for r in metrics),
                  "focused_periods": FOCUS, "boundary_diagnostics_rows": len(timestamp),
                  "benchmark_rows": len(benchmark), "daily_mean_vs_night_then_center_max_abs_by_year_component": equivalence,
                  "meanfield_pair_counts": anomaly_counts,
                  "output_rows": {"D2_hourly_vs_minute.csv": len(metrics), "D2_timestamp_diagnostics.csv": len(timestamp),
                                  "D2_benchmark_offset.csv": len(benchmark), "D2_meanfield_anomaly.csv": len(anomalies)},
                  "decisions": {"D2-TIME": "PENDING_REVIEW", "D2-DATA": "PENDING_REVIEW", "D2-BENCHMARK": "PENDING_REVIEW",
                                "D2_GATE": "PENDING_REVIEW", "G1": "NOT_EVALUATED"},
                  "environment": {"python": sys.version, "numpy": np.__version__, "platform": platform.platform(),
                                  "script_sha256": sha(Path(__file__))},
                  "errors": []}
    (D2 / "D2_validation.json").write_text(json.dumps(json_safe(validation), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    logger.info("D2 numerical tables complete; decisions assigned after audit of distributions")


if __name__ == "__main__":
    main()
