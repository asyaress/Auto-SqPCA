"""Read-only S7 source audit. Writes only phase2a/S7; no WDC PCA/SVD."""
from __future__ import annotations

import csv
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
OUT = ROOT / "phase2a/S7"
RAW = ROOT / "phase2a/raw"
MEN = RAW / "mendeley/jcmdrm5f5x-1"
NIGHT = [0, 1, 2, 3, 23]
CONTROLS = [(2008, 1), (2008, 3), (2012, 6), (2016, 10), (2017, 6), (2017, 10)]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_csv(name: str, rows: list[dict], fields: list[str]) -> None:
    with (OUT / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def read_dat(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    if not rows or not rows[0] or len({len(row) for row in rows}) != 1:
        raise RuntimeError(f"Empty or ragged DAT: {path}")
    return rows[0], rows[1:]


def col(path: Path, key: str | None = None) -> np.ndarray:
    header, rows = read_dat(path)
    index = header.index(key) if key is not None else 1
    values = np.array([np.nan if row[index] == "NA" else float(row[index]) for row in rows])
    return values


def logger_setup() -> logging.Logger:
    OUT.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("S7")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)s %(message)s")
    for handler in (logging.FileHandler(OUT / "S7_execution.log", mode="w", encoding="utf-8"),
                    logging.StreamHandler(sys.stdout)):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def frozen_manifest() -> dict[str, str]:
    with (ROOT / "phase2a/G0/input_manifest.csv").open(encoding="utf-8", newline="") as f:
        return {row["relative_path"]: row["sha256"] for row in csv.DictReader(f)}


def check_frozen(expected: dict[str, str], other: dict[str, str], logger: logging.Logger, stage: str) -> dict:
    raw_entries = {k: v for k, v in expected.items() if k.startswith("phase2a/raw/")}
    minute_entries = {k: v for k, v in expected.items() if re.fullmatch(
        r"audit_sq_wdc/cache/COI_20(?:0[7-9]|1[0-7])_minute_iaga_XYZF\.zip", k)}
    actual_paths = {relative(p) for p in RAW.rglob("*") if p.is_file()}
    if actual_paths != set(raw_entries):
        raise RuntimeError(f"Raw path set differs from G0: missing={sorted(set(raw_entries)-actual_paths)[:5]}, added={sorted(actual_paths-set(raw_entries))[:5]}")
    for name, digest in {**raw_entries, **minute_entries, **other}.items():
        actual = sha(ROOT / name)
        if actual.lower() != digest.lower():
            raise RuntimeError(f"Frozen SHA-256 mismatch: {name}; expected={digest}; actual={actual}")
    logger.info("%s: %d raw, %d frozen minute ZIPs, %d G0/D1/D2 documents match SHA-256",
                stage, len(raw_entries), len(minute_entries), len(other))
    return {"raw_files": len(raw_entries), "minute_zip_files": len(minute_entries),
            "frozen_documents": len(other), "all_sha256_match": True}


def dat_index() -> dict[str, Path]:
    files = list(MEN.rglob("*.dat"))
    if len(files) != 684:
        raise RuntimeError(f"Expected 684 Mendeley DAT, found {len(files)}")
    by_name = {p.name: p for p in files}
    if len(by_name) != len(files):
        raise RuntimeError("Duplicate Mendeley DAT basenames; cannot index uniquely")
    return by_name


def mode_fit(observed: np.ndarray, prediction: np.ndarray) -> dict:
    if observed.shape != prediction.shape or not np.isfinite(observed).all() or not np.isfinite(prediction).all():
        raise RuntimeError(f"Invalid mode comparison shapes or finite values: {observed.shape}, {prediction.shape}")
    denom = float(np.dot(prediction, prediction))
    if denom == 0:
        raise RuntimeError("Zero-norm PC x EOF prediction")
    scale = float(np.dot(observed, prediction) / denom)
    direct = observed - prediction
    fitted = observed - scale * prediction
    return {"n": len(observed), "fitted_scale_signed": scale,
            "rmse_direct_nT": float(np.sqrt(np.mean(direct**2))),
            "max_abs_direct_nT": float(np.max(np.abs(direct))),
            "rmse_signed_scale_nT": float(np.sqrt(np.mean(fitted**2))),
            "relative_frobenius_residual": float(np.linalg.norm(fitted) / np.linalg.norm(observed)),
            "abs_correlation": float(abs(np.corrcoef(observed, prediction)[0, 1])),
            "amplitude_observed_nT": float(np.ptp(observed)),
            "amplitude_predicted_nT": float(np.ptp(prediction)),
            "amplitude_ratio_observed_over_predicted": float(np.ptp(observed) / np.ptp(prediction))}


def modes(index: dict[str, Path], logger: logging.Logger) -> tuple[list[dict], list[dict]]:
    rows = []
    pair_rows = []
    for role in ("meanField", "mode1", "mode2"):
        for suffix in ("", "_y_all"):
            y = index[f"COI_Y_{role}_m02{suffix}.dat"]
            z = index[f"COI_Z_{role}_m02{suffix}.dat"]
            hy, ry = read_dat(y)
            hz, rz = read_dat(z)
            identical = sha(y) == sha(z)
            pair_rows.append({"role": role, "scope": "per_year" if not suffix else "all_years",
                              "y_path": relative(y), "z_path": relative(z), "sha256_y": sha(y),
                              "sha256_z": sha(z), "rows": len(ry), "columns": len(hy),
                              "headers_identical": hy == hz, "values_identical": ry == rz,
                              "byte_identical": identical})
            if not identical or hy != hz or ry != rz:
                raise RuntimeError(f"Expected February Y/Z duplicate absent: {role}{suffix}")
    for month in (1, 2, 3):
        mm = f"m{month:02d}"
        for mode in (1, 2):
            for scope in ("per_year", "all_years"):
                years = list(range(2007, 2018)) if scope == "per_year" else ["all"]
                for year in years:
                    key = f"y.{year}"
                    predictions = {}
                    observations = {}
                    hashes = {}
                    for comp in "YZ":
                        e_name = f"COI_{comp}_EOF{mode}{'_y_all' if scope == 'all_years' else ''}_{mm}.dat"
                        p_name = f"COI_{comp}_PC{mode}_{mm}.dat"
                        m_name = f"COI_{comp}_mode{mode}_{mm}{'_y_all' if scope == 'all_years' else ''}.dat"
                        e, p, m = (index[n] for n in (e_name, p_name, m_name))
                        eof = col(e, None if scope == "all_years" else key)
                        pc = col(p, key)
                        obs = col(m, None if scope == "all_years" else key)
                        eof = eof[np.isfinite(eof)]
                        pred = np.outer(eof, pc).reshape(-1)
                        if len(obs) != len(pred):
                            raise RuntimeError(f"Mode dimensions inconsistent: {m_name}, {len(obs)} vs {len(pred)}")
                        predictions[comp] = pred
                        observations[comp] = obs
                        hashes[comp] = "|".join(f"{relative(q)}:{sha(q)}" for q in (e, p, m))
                    for observed_comp in "YZ":
                        for predicted_comp in "YZ":
                            result = mode_fit(observations[observed_comp], predictions[predicted_comp])
                            rows.append({"month": month, "mode": mode, "scope": scope, "year": year,
                                         "observed_component": observed_comp, "prediction_component": predicted_comp,
                                         **result, "exact_direct_1e_9": result["max_abs_direct_nT"] < 1e-9,
                                         "observed_and_prediction_input_sha256": hashes[observed_comp] + " || " + hashes[predicted_comp]})
        logger.info("Mode PC x EOF evaluated for month %02d, Y/Z, modes 1/2, annual and combined", month)
    write_csv("S7_mode_consistency.csv", rows, list(rows[0]))
    return rows, pair_rows


def read_gfz(year: int, month: int) -> tuple[list[int], Path]:
    path = RAW / "gfz" / f"QD_days{year}.txt"
    label = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month-1]
    lines = [line for line in path.read_text(encoding="utf-8").splitlines()
             if re.match(rf"^\s*{label}\s+{year}\s", line)]
    if len(lines) != 1:
        raise RuntimeError(f"Expected one GFZ {label} {year} row, found {len(lines)}")
    days = [int(re.match(r"\d+", token).group()) for token in lines[0].split()[2:7]]
    if len(days) != 5 or len(set(days)) != 5:
        raise RuntimeError(f"Invalid GFZ Q1-Q5 {year}-{month:02d}: {days}")
    return days, path


def read_hourly(year: int, month: int) -> tuple[np.ndarray, Path]:
    import calendar
    path = RAW / "wdc_hourly" / f"COI_{year}_hour_iaga_XYZF.zip"
    member = f"coi{year}{month:02d}dhor.hor"
    with zipfile.ZipFile(path) as archive:
        lines = archive.read(member).decode("ascii").splitlines()
    n_days = calendar.monthrange(year, month)[1]
    values = []
    stamps = []
    for line in lines:
        if re.match(rf"^{year}-{month:02d}-\d{{2}}\s", line):
            tokens = line.split()
            if len(tokens) != 7:
                raise RuntimeError(f"Invalid WDC row: {line!r}")
            stamps.append(tokens[0] + " " + tokens[1])
            values.append([float(x) for x in tokens[3:6]])
    expected = [f"{year}-{month:02d}-{day:02d} {h:02d}:00:00.000"
                for day in range(1, n_days+1) for h in range(24)]
    if stamps != expected:
        raise RuntimeError(f"WDC timestamp sequence invalid: {member}; {len(stamps)} rows")
    a = np.asarray(values).reshape(n_days, 24, 3)
    a[a >= 88888] = np.nan
    return a, path


def sq_metrics(curve: np.ndarray, reference: np.ndarray) -> dict:
    residual = curve - reference
    centered = residual - residual.mean()
    return {"rmse_absolute_nT": float(np.sqrt(np.mean(residual**2))),
            "rmse_shape_nT": float(np.sqrt(np.mean(centered**2))),
            "max_abs_absolute_nT": float(np.max(np.abs(residual))),
            "max_abs_shape_nT": float(np.max(np.abs(centered))),
            "correlation": float(np.corrcoef(curve, reference)[0, 1]),
            "offset_mean_residual_nT": float(residual.mean()),
            "mean_24h_nT": float(curve.mean()),
            "mean_night_nT": float(curve[NIGHT].mean()),
            "amplitude_nT": float(np.ptp(curve)),
            "amplitude_delta_nT": float(np.ptp(curve) - np.ptp(reference))}


def sq_audit(index: dict[str, Path], logger: logging.Logger) -> tuple[list[dict], dict, float]:
    rows = []
    sd_identity_max = 0.0
    profile = {role: {"columns": 0, "max_abs_mean24_nT": 0., "night_abs_gt_0p1_count": 0,
                      "night_abs_values": []} for role in ("Sq", "SD", "S")}
    for month in range(1, 13):
        for comp in "XYZ":
            path = index[f"COI_{comp}_Sq.SD.S_m{month:02d}.dat"]
            header, data = read_dat(path)
            if len(data) != 24 or len(header) != 37 or [int(row[0]) for row in data] != list(range(1, 25)):
                raise RuntimeError(f"Invalid Sq/SD/S DAT dimensions/index: {path}")
            for year in [*range(2007, 2018), "all"]:
                sq_values = col(path, f"Sq.y.{year}")
                sd_values = col(path, f"SD.y.{year}")
                s_values = col(path, f"S.y.{year}")
                sd_identity_max = max(sd_identity_max,
                                      float(np.max(np.abs(s_values - sq_values - sd_values))))
            for role in ("Sq", "SD", "S"):
                for year in [*range(2007, 2018), "all"]:
                    key = f"{role}.y.{year}"
                    a = col(path, key)
                    if not np.isfinite(a).all():
                        raise RuntimeError(f"Nonfinite Mendeley {key}: {path}")
                    q = profile[role]
                    q["columns"] += 1
                    q["max_abs_mean24_nT"] = max(q["max_abs_mean24_nT"], abs(float(a.mean())))
                    night_abs = abs(float(a[NIGHT].mean()))
                    q["night_abs_gt_0p1_count"] += night_abs > .1
                    q["night_abs_values"].append(night_abs)
                    rows.append({"record_type": "mendeley_column", "year": year, "month": month,
                                 "component": comp, "role": role, "candidate": "original",
                                 "iqd_days": "", "matched_hours": 24, "source_path": relative(path),
                                 "source_sha256": sha(path), "mean_24h_nT": float(a.mean()),
                                 "mean_night_nT": float(a[NIGHT].mean()), "amplitude_nT": float(np.ptp(a))})
    for year, month in CONTROLS:
        days, gfz_path = read_gfz(year, month)
        hour, wdc_path = read_hourly(year, month)
        for ci, comp in enumerate("XYZ"):
            selected = hour[np.asarray(days)-1, :, ci]
            if not np.isfinite(selected).all():
                raise RuntimeError(f"Representative IQD contains missing {comp}: {year}-{month:02d}, days {days}")
            ref_path = index[f"COI_{comp}_Sq.SD.S_m{month:02d}.dat"]
            ref = col(ref_path, f"Sq.y.{year}")
            night = (selected - selected[:, NIGHT].mean(axis=1)[:, None]).mean(axis=0)
            daily = (selected - selected.mean(axis=1)[:, None]).mean(axis=0)
            night_centered = night - night.mean()
            if np.max(np.abs(daily-night_centered)) > 1e-9:
                raise RuntimeError("Night then 24h centering differs from daily mean")
            for candidate, curve in (("night", night), ("daily_mean", daily),
                                     ("night_then_center", night_centered)):
                rows.append({"record_type": "wdc_reconstruction", "year": year, "month": month,
                             "component": comp, "role": "Sq", "candidate": candidate,
                             "iqd_days": "|".join(map(str, days)), "matched_hours": 24,
                             "source_path": "|".join(map(relative, (ref_path, gfz_path, wdc_path))),
                             "source_sha256": "|".join(map(sha, (ref_path, gfz_path, wdc_path))),
                             **sq_metrics(curve, ref),
                             "reference_mean24_nT": float(ref.mean()),
                             "reference_night_mean_nT": float(ref[NIGHT].mean()),
                             "reference_amplitude_nT": float(np.ptp(ref))})
        logger.info("Representative non-February Sq compared: %d-%02d, GFZ Q1-Q5=%s", year, month, days)
    for q in profile.values():
        q["median_abs_night_mean_nT"] = float(np.median(q.pop("night_abs_values")))
    write_csv("S7_sq_baseline_diagnostics.csv", rows, list(dict.fromkeys(k for row in rows for k in row)))
    return rows, profile, sd_identity_max


def quarantine(index: dict[str, Path]) -> tuple[list[dict], dict]:
    rows = []
    for name, path in sorted(index.items()):
        parts = path.relative_to(MEN).parts
        family = parts[1]
        comp = parts[2]
        mm = re.search(r"_m(\d{2})(?:_|\.)", name)
        month = int(mm.group(1)) if mm else None
        status = "VERIFIED"
        note = "G0 DAT format/structure and SHA-256 verified; no scientific truth claim"
        if family == "IQD Sq and SD":
            status = "SUSPECT"
            note = "Sq/SD/S columns centered at 24h mean zero; source night baseline and absolute 0.1 nT criterion unresolved"
        elif comp == "Y" and month == 2:
            if re.match(r"COI_Y_(meanField|mode[12])_m02(?:_y_all)?\.dat$", name):
                status = "UNUSABLE_FOR_NUMERIC_BENCHMARK"
                note = "Byte-identical to Z February counterpart; mode1/2 reconstruct from Z PC x EOF, not Y"
            else:
                status = "SUSPECT"
                note = "February Y PC/EOF/VF or mode3 under affected family; individual scientific validity unverified"
        elif comp == "Z" and month == 2 and re.match(
                r"COI_Z_(?:PC[12]|EOF[12]|mode[12])_m02\.dat$", name):
            status = "SUSPECT"
            note = "2014 Z annual mode differs from Z PC x EOF (signed-scale residual 0.744/0.341 nT for modes 1/2); responsible member not isolated"
        elif family == "PCA modes" and comp in "YZ" and month in (1, 2, 3) and re.search(r"mode[12]_", name):
            note = "G0 format/hash and S7 PC x EOF internal consistency verified for this mode; WDC PCA not tested"
        rows.append({"relative_path": relative(path), "sha256": sha(path), "family": family,
                     "component": comp, "month": month, "bytes": path.stat().st_size,
                     "status": status, "checks_and_limitations": note})
    write_csv("S7_benchmark_manifest.csv", rows, list(rows[0]))
    return rows, dict(Counter(row["status"] for row in rows))


def main() -> None:
    logger = logger_setup()
    logger.info("S7-A began; no D3/D4, WDC PCA/SVD, source edits or downloads")
    expected = frozen_manifest()
    frozen_names = [f"phase2a/{gate}/{name}" for gate, names in {
        "G0": ["G0_report.md", "G0_validation.json", "input_manifest.csv", "mendeley_dat_inventory.csv",
               "wdc_hourly_inventory.csv", "gfz_day_inventory.csv", "Protokol Final Fase 2A Replikasi Morozova & Rebbah (2023) untuk Auto-SqPCA.docx"],
        "D1": ["D1_feb29_report.md", "D1_validation.json", "D1_evidence.csv", "d1_feb29.py"],
        "D2": ["D2_report.md", "D2_validation.json", "D2_benchmark_offset.csv", "d2_compute.py", "d2_report.py"]}.items() for name in names]
    frozen = {name: sha(ROOT / name) for name in frozen_names}
    before = check_frozen(expected, frozen, logger, "BEFORE")
    index = dat_index()
    mode_rows, duplicate_pairs = modes(index, logger)
    sq_rows, sq_profile, sd_identity_max = sq_audit(index, logger)
    manifest_rows, status_counts = quarantine(index)
    after = check_frozen(expected, frozen, logger, "AFTER")
    result = {"schema": "Auto-SqPCA-S7-A-v1", "protocol_version": "G0-registration-1; unchanged",
              "scope": "S7-A source audit only", "parameters": {
                  "mode_reconstruction": "day-major outer(EOF_day, PC_hour); fitted signed scale for shape and direct scale=1 residual",
                  "mode_exact_max_abs_threshold": 1e-9, "night_hour_indices_zero_based": NIGHT,
                  "reference_columns": "Sq.y.YYYY, SD.y.YYYY, S.y.YYYY",
                  "sq_candidates": ["night", "daily_mean", "night_then_center"],
                  "sq_absolute_tolerance_nT_frozen": 0.1, "representative_months": CONTROLS,
                  "missing_handling": "No interpolation; all 5x24 XYZ selected WDC values must be finite"},
              "frozen_sha256": frozen, "integrity_before": before, "integrity_after": after,
              "duplicate_pairs": duplicate_pairs, "mode_rows": len(mode_rows),
              "mode_exact_counts_by_month_observed_predicted": {
                  f"{month}:{o}:{p}": sum(r["exact_direct_1e_9"] for r in mode_rows if
                                         r["month"] == month and r["observed_component"] == o and
                                         r["prediction_component"] == p)
                  for month in (1, 2, 3) for o in "YZ" for p in "YZ"},
              "sq_profile": sq_profile, "S_minus_Sq_minus_SD_max_abs_nT": sd_identity_max,
              "sq_diagnostic_rows": len(sq_rows),
              "benchmark_manifest_rows": len(manifest_rows), "status_counts": status_counts,
              "input_sha256": {"mendeley_archive": expected["phase2a/raw/mendeley/jcmdrm5f5x-1.zip"],
                               **{f"wdc_{year}": expected[f"phase2a/raw/wdc_hourly/COI_{year}_hour_iaga_XYZF.zip"]
                                  for year, _ in CONTROLS},
                               **{f"gfz_{year}": expected[f"phase2a/raw/gfz/QD_days{year}.txt"]
                                  for year, _ in CONTROLS}},
              "environment": {"python": sys.version, "numpy": np.__version__, "platform": platform.platform()},
              "decisions": "See s7_finalize.py after numeric review", "errors": []}
    (OUT / "S7_decision.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    logger.info("Completed: %d mode rows, %d Sq rows, %d DAT manifest rows; status=%s",
                len(mode_rows), len(sq_rows), len(manifest_rows), status_counts)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.getLogger("S7").exception("S7-A failed")
        raise
