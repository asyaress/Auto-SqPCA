"""D1 only: audit February leap-day indexing and Sq IQD candidates.

Reads frozen G0/raw inputs. Does not perform D2, full PCA, DTW, DIFI, or
classification. Limited SVD is used only on February 2008 X to diagnose
calendar length, with all four previously named centering variants displayed.
"""
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
D1 = ROOT / "phase2a" / "D1"
G0 = ROOT / "phase2a" / "G0"
RAW = ROOT / "phase2a" / "raw"
MEN = RAW / "mendeley" / "jcmdrm5f5x-1"
NIGHT_HOURS = (0, 1, 2, 3, 23)
YEARS = (2008, 2012, 2016)
EVIDENCE_FIELDS = [
    "evidence_type", "year", "component", "candidate", "days_1based", "source_file",
    "source_sha256", "rows", "columns", "valid_count", "offset_fit_nT", "correlation",
    "rmse_nT", "max_abs_nT", "mean_residual_nT", "shape_rmse_nT", "shape_max_abs_nT",
    "amplitude_nT", "benchmark_amplitude_nT", "amplitude_delta_nT", "vf1", "benchmark_vf1",
    "vf1_abs_delta", "eof1_abs_corr", "note",
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def configure_log() -> logging.Logger:
    D1.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("d1")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(levelname)s %(message)s")
    file_handler = logging.FileHandler(D1 / "D1_execution.log", mode="w", encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)
    return logger


def manifest_hashes() -> dict[str, str]:
    with (G0 / "input_manifest.csv").open(encoding="utf-8", newline="") as f:
        return {r["relative_path"]: r["sha256"] for r in csv.DictReader(f)}


def assert_raw_unchanged(expected: dict[str, str], stage: str, logger: logging.Logger) -> int:
    raw_entries = {key: val for key, val in expected.items() if key.startswith("phase2a/raw/")}
    actual_paths = {relative(p) for p in RAW.rglob("*") if p.is_file()}
    if actual_paths != set(raw_entries):
        missing = sorted(set(raw_entries) - actual_paths)
        added = sorted(actual_paths - set(raw_entries))
        raise RuntimeError(f"Raw path inventory differs from G0: missing={missing[:5]}, added={added[:5]}")
    for path, expected_digest in raw_entries.items():
        actual = sha(ROOT / path)
        if actual.lower() != expected_digest.lower():
            raise RuntimeError(f"Raw SHA-256 differs from G0: {path}, expected={expected_digest}, actual={actual}")
    logger.info("%s: %d/%d raw files match G0 SHA-256", stage, len(raw_entries), len(raw_entries))
    return len(raw_entries)


def find_dat(name: str) -> Path:
    found = list(MEN.rglob(name))
    if len(found) != 1:
        raise RuntimeError(f"Expected exactly one Mendeley file {name}, found {len(found)}")
    return found[0]


def tab(path: Path) -> tuple[list[str], list[list[str]]]:
    rows = list(csv.reader(path.open(encoding="utf-8", newline=""), delimiter="\t"))
    if not rows or len({len(r) for r in rows}) != 1:
        raise RuntimeError(f"Empty/ragged DAT: {path}")
    return rows[0], rows[1:]


def feb_data(year: int) -> tuple[np.ndarray, list[str], Path]:
    path = RAW / "wdc_hourly" / f"COI_{year}_hour_iaga_XYZF.zip"
    name = f"coi{year}02dhor.hor"
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise RuntimeError(f"WDC ZIP CRC failed: {path}")
        lines = archive.read(name).decode("ascii").splitlines()
    stamps = []
    values = []
    for line in lines:
        if not line.startswith(f"{year}-02-"):
            continue
        fields = line.split()
        if len(fields) != 7:
            raise RuntimeError(f"WDC data row does not have seven columns: {line!r}")
        stamps.append(fields[0] + " " + fields[1])
        values.append([float(t) for t in fields[3:6]])
    if len(stamps) != 29 * 24 or len(set(stamps)) != len(stamps):
        raise RuntimeError(f"WDC February {year} has {len(stamps)} rows, {len(set(stamps))} unique timestamps")
    expected_stamps = [f"{year}-02-{d:02d} {h:02d}:00:00.000" for d in range(1, 30) for h in range(24)]
    if stamps != expected_stamps:
        raise RuntimeError(f"WDC February {year} timestamps are not complete ordered HH:00")
    array = np.asarray(values, dtype=float).reshape(29, 24, 3)
    array[array >= 88888] = np.nan
    return array, stamps, path


def gfz_feb(year: int) -> tuple[list[int], Path]:
    path = RAW / "gfz" / f"QD_days{year}.txt"
    line = next((x for x in path.read_text(encoding="utf-8").splitlines()
                 if re.match(rf"^\s*Feb\s+{year}\s", x)), None)
    if line is None:
        raise RuntimeError(f"GFZ February {year} not found: {path}")
    tokens = line.split()[2:12]
    days = [int(re.match(r"^\d+", t).group()) for t in tokens]
    if len(days) != 10 or len(set(days)) != 10:
        raise RuntimeError(f"GFZ February {year} Q1-Q10 invalid: {line}")
    return days, path


def add(records: list[dict], **data: object) -> None:
    records.append({field: data.get(field, "") for field in EVIDENCE_FIELDS})


def curve_metrics(curve: np.ndarray, reference: np.ndarray) -> dict[str, float]:
    if len(curve) != 24 or not np.all(np.isfinite(curve)) or not np.all(np.isfinite(reference)):
        raise RuntimeError("Sq candidate/reference requires 24 finite hourly values")
    residual = curve - reference
    shape_residual = (curve - curve.mean()) - (reference - reference.mean())
    return {"correlation": float(np.corrcoef(curve, reference)[0, 1]),
            "rmse_nT": float(np.sqrt(np.mean(residual**2))),
            "max_abs_nT": float(np.max(np.abs(residual))),
            "mean_residual_nT": float(residual.mean()),
            "shape_rmse_nT": float(np.sqrt(np.mean(shape_residual**2))),
            "shape_max_abs_nT": float(np.max(np.abs(shape_residual))),
            "amplitude_nT": float(np.ptp(curve)),
            "benchmark_amplitude_nT": float(np.ptp(reference)),
            "amplitude_delta_nT": float(np.ptp(curve) - np.ptp(reference))}


def main() -> None:
    logger = configure_log()
    logger.info("D1 began; protocol G0-registration-1; no D2/full PCA")
    expected = manifest_hashes()
    g0_paths = [G0 / n for n in ("G0_report.md", "G0_validation.json", "input_manifest.csv")]
    g0_before = {relative(p): sha(p) for p in g0_paths}
    raw_count = assert_raw_unchanged(expected, "Before D1", logger)
    input_hashes: dict[str, str] = {}

    def register(path: Path) -> None:
        name = relative(path)
        digest = sha(path)
        if name in expected and digest.lower() != expected[name].lower():
            raise RuntimeError(f"Input SHA-256 differs from G0: {name}")
        input_hashes[name] = digest

    protocol = next(G0.glob("Protokol Final Fase 2A*.docx"))
    register(protocol)
    arrays: dict[int, np.ndarray] = {}
    quiet: dict[int, list[int]] = {}
    evidence: list[dict] = []
    for year in YEARS:
        arrays[year], stamps, archive = feb_data(year)
        register(archive)
        quiet[year], gfz_path = gfz_feb(year)
        register(gfz_path)
        missing_by_component = {c: int(np.isnan(arrays[year][:, :, i]).sum()) for i, c in enumerate("XYZ")}
        logger.info("WDC %d: 696 unique HH:00, 29 Feb = 24 hours, missing XYZ=%s; GFZ Q1-Q10=%s",
                    year, missing_by_component, quiet[year])
        for i, component in enumerate("XYZ"):
            add(evidence, evidence_type="wdc_leap_day", year=year, component=component,
                candidate="29 February", source_file=relative(archive), source_sha256=input_hashes[relative(archive)],
                rows=24, columns=7, valid_count=int(np.isfinite(arrays[year][28, :, i]).sum()),
                note=f"29 February, 24 timestamps; missing component hours={int(np.isnan(arrays[year][28, :, i]).sum())}")
        add(evidence, evidence_type="gfz_feb_quiet", year=year, candidate="Q1-Q10",
            days_1based="|".join(map(str, quiet[year])), source_file=relative(gfz_path),
            source_sha256=input_hashes[relative(gfz_path)], rows=1, columns=10,
            note="Q1-Q5 are official IQD; Q6 is replacement candidate only in 2016")
    if quiet[2016][:6] != [22, 28, 27, 21, 29, 10]:
        raise RuntimeError(f"2016 GFZ quiet-day order differs from expected review: {quiet[2016][:6]}")

    file_structure: dict[str, dict] = {}
    year_tables: dict[str, dict] = {}
    benchmark_sq: dict[tuple[int, str], np.ndarray] = {}
    benchmark_eof: dict[str, np.ndarray] = {}
    vf_benchmark: dict[str, float] = {}
    for component in "XYZ":
        files = {kind: find_dat(f"COI_{component}_{suffix}") for kind, suffix in {
            "meanField": "meanField_m02.dat", "meanField_y_all": "meanField_m02_y_all.dat",
            "EOF1": "EOF1_m02.dat", "EOF1_y_all": "EOF1_y_all_m02.dat",
            "VF1": "VF1_m02.dat", "Sq": "Sq.SD.S_m02.dat"}.items()}
        for path in files.values():
            register(path)
        structure = {}
        for kind in ("meanField", "meanField_y_all", "EOF1", "EOF1_y_all", "Sq"):
            header, data = tab(files[kind])
            structure[kind] = {"file": relative(files[kind]), "rows": len(data), "columns": len(header),
                               "header": header, "first_index": data[0][0], "last_index": data[-1][0]}
            add(evidence, evidence_type="mendeley_structure", component=component, candidate=kind,
                source_file=relative(files[kind]), source_sha256=input_hashes[relative(files[kind])],
                rows=len(data), columns=len(header), note=f"first index={data[0][0]}; last index={data[-1][0]}")
        h_mean, m_mean = tab(files["meanField"])
        h_all, m_all = tab(files["meanField_y_all"])
        h_eof, m_eof = tab(files["EOF1"])
        h_eof_all, m_eof_all = tab(files["EOF1_y_all"])
        h_sq, m_sq = tab(files["Sq"])
        vf_rows = list(csv.reader(files["VF1"].open(encoding="utf-8", newline=""), delimiter="\t"))
        structure["VF1"] = {"file": relative(files["VF1"]), "rows": len(vf_rows), "columns": 2,
                             "labels": [row[0] for row in vf_rows]}
        add(evidence, evidence_type="mendeley_structure", component=component, candidate="VF1",
            source_file=relative(files["VF1"]), source_sha256=input_hashes[relative(files["VF1"])],
            rows=len(vf_rows), columns=2, note="No header; y.2007–y.2017 and y.all")
        expected_year_header = ["day"] + [f"y.{y}" for y in range(2007, 2018)]
        if h_mean != expected_year_header or h_eof != expected_year_header:
            raise RuntimeError(f"Unexpected year header in {component} February meanField/EOF1")
        if [r[0] for r in m_mean] != list(map(str, range(1, 29))) or [r[0] for r in m_eof] != list(map(str, range(1, 29))):
            raise RuntimeError(f"Unexpected per-year February day index in {component}")
        if len(m_all) != 308 or [r[0] for r in m_all] != list(map(str, range(1, 309))):
            raise RuntimeError(f"Unexpected combined February meanField index in {component}")
        flatten = [m_mean[day][col] for col in range(1, 12) for day in range(28)]
        flatten_exact = [row[1] for row in m_all] == flatten
        if not flatten_exact:
            raise RuntimeError(f"Combined meanField not exact year-major flatten in {component}")
        if len(m_eof_all) != 341 or [r[0] for r in m_eof_all] != list(map(str, range(1, 342))):
            raise RuntimeError(f"Unexpected combined EOF1 index in {component}")
        eof_valid = sum(row[1] != "NA" for row in m_eof_all)
        eof_padding = sum(row[1] == "NA" for row in m_eof_all)
        if eof_valid != 308 or eof_padding != 33 or any(row[1] == "NA" for row in m_eof_all[:308]):
            raise RuntimeError(f"Combined EOF1 padding unexpected in {component}: valid={eof_valid}, NA={eof_padding}")
        structure["meanField_y_all"]["exact_year_major_flatten"] = flatten_exact
        structure["EOF1_y_all"].update({"valid_prefix": eof_valid, "trailing_NA": eof_padding})
        add(evidence, evidence_type="combined_index", component=component, candidate="meanField year-major",
            source_file=relative(files["meanField_y_all"]), source_sha256=input_hashes[relative(files["meanField_y_all"])],
            rows=308, columns=2, valid_count=308, note="Exact text match to 11 consecutive 28-day year blocks")
        add(evidence, evidence_type="combined_index", component=component, candidate="EOF1 combined padding",
            source_file=relative(files["EOF1_y_all"]), source_sha256=input_hashes[relative(files["EOF1_y_all"])],
            rows=341, columns=2, valid_count=308, note="Indices 1–308 numeric; 309–341 NA; not per-year EOF flatten")
        for year in YEARS:
            idx = h_sq.index(f"Sq.y.{year}")
            benchmark_sq[year, component] = np.array([float(row[idx]) for row in m_sq], dtype=float)
        benchmark_eof[component] = np.array([float(row[h_eof.index("y.2008")]) for row in m_eof], dtype=float)
        vf_benchmark[component] = float(next(row[1] for row in vf_rows if row[0] == "y.2008"))
        year_tables[component] = {year: np.array([float(row[h_mean.index(f"y.{year}")]) for row in m_mean]) for year in YEARS}
        file_structure[component] = structure
        logger.info("Mendeley %s: 28 per-year rows; meanField combined 308 exact year-major; EOF1 combined 308 + 33 NA", component)

    y_mean_hash = input_hashes[file_structure["Y"]["meanField"]["file"]]
    z_mean_hash = input_hashes[file_structure["Z"]["meanField"]["file"]]
    yz_duplicate = y_mean_hash == z_mean_hash
    logger.warning("Y and Z February meanField byte-identical: %s; Y not used to confirm calendar mapping", yz_duplicate)

    map_scores: dict[int, dict[str, list[dict]]] = {}
    for year in YEARS:
        map_scores[year] = {}
        for j, component in enumerate("XYZ"):
            daily = arrays[year][:, :, j]
            complete = np.all(np.isfinite(daily), axis=1)
            means = np.nanmean(daily, axis=1)
            reference = year_tables[component][year]
            scores = []
            for dropped in range(1, 30):
                observed = np.delete(means, dropped - 1)
                valid = np.delete(complete, dropped - 1)
                offset = float(np.median((observed - reference)[valid]))
                residual = (observed - offset - reference)[valid]
                rmse = float(np.sqrt(np.mean(residual**2)))
                maximum = float(np.max(np.abs(residual)))
                item = {"dropped_day": dropped, "rmse_nT": rmse, "max_abs_nT": maximum,
                        "offset_fit_nT": offset, "valid_days": int(valid.sum())}
                scores.append(item)
                add(evidence, evidence_type="calendar_mapping", year=year, component=component,
                    candidate=f"drop day {dropped}", days_1based="|".join(map(str, [d for d in range(1, 30) if d != dropped])),
                    source_file=file_structure[component]["meanField"]["file"],
                    source_sha256=input_hashes[file_structure[component]["meanField"]["file"]],
                    rows=28, columns=1, valid_count=int(valid.sum()), offset_fit_nT=offset,
                    rmse_nT=rmse, max_abs_nT=maximum,
                    note="Y benchmark is byte-identical to Z; excluded from mapping decision" if component == "Y" else
                         "Median constant offset fitted; incomplete WDC days omitted from score")
            map_scores[year][component] = sorted(scores, key=lambda s: s["rmse_nT"])
            best = map_scores[year][component][0]
            logger.info("Calendar %d %s: best drop=%d, RMSE=%.6f nT; second drop=%d, RMSE=%.6f nT",
                        year, component, best["dropped_day"], best["rmse_nT"],
                        map_scores[year][component][1]["dropped_day"], map_scores[year][component][1]["rmse_nT"])

    svd_results = []
    x2008 = arrays[2008][:, :, 0].T
    if not np.all(np.isfinite(x2008)):
        raise RuntimeError("2008 February X contains missing data; limited un-interpolated SVD not allowed")
    for day_count in (28, 29):
        matrix = x2008[:, :day_count]
        variants = {
            "V0": matrix,
            "V1": matrix - matrix.mean(axis=0, keepdims=True),
            "V2": matrix - matrix.mean(axis=1, keepdims=True),
            "V3": matrix - matrix[list(NIGHT_HOURS), :].mean(axis=0, keepdims=True),
        }
        for variant, data in variants.items():
            _, singular, vh = np.linalg.svd(data, full_matrices=False)
            vf1 = float(singular[0] ** 2 / np.sum(singular**2))
            # EOF1 in the published file has unit Euclidean norm; compare shape
            # after truncating the 29-day candidate to its first 28 entries.
            eof_abs_corr = float(abs(np.corrcoef(vh[0, :28], benchmark_eof["X"])[0, 1]))
            item = {"days": day_count, "variant": variant, "vf1": vf1,
                    "benchmark_vf1": vf_benchmark["X"], "vf1_abs_delta": abs(vf1 - vf_benchmark["X"]),
                    "eof1_abs_corr": eof_abs_corr}
            svd_results.append(item)
            add(evidence, evidence_type="limited_svd_2008_X", year=2008, component="X",
                candidate=f"{variant} {day_count} days", days_1based="|".join(map(str, range(1, day_count + 1))),
                source_file=file_structure["X"]["VF1"]["file"],
                source_sha256=input_hashes[file_structure["X"]["VF1"]["file"]],
                rows=24, columns=day_count, valid_count=24 * day_count, vf1=vf1,
                benchmark_vf1=vf_benchmark["X"], vf1_abs_delta=abs(vf1 - vf_benchmark["X"]),
                eof1_abs_corr=eof_abs_corr, note="Calendar sensitivity only; no centering variant selected")
    logger.info("Limited SVD: 8 February-2008 X combinations (V0–V3 × 28/29), no other PCA")

    sq_results: dict[int, dict[str, dict]] = {}
    for year in YEARS:
        sq_results[year] = {}
        candidates = {"official_Q1_Q5": quiet[year][:5]}
        if year == 2016:
            candidates["replace_29_with_Q6"] = quiet[year][:4] + [quiet[year][5]]
            candidates["omit_29_no_replacement"] = quiet[year][:4]
        for component_index, component in enumerate("XYZ"):
            sq_results[year][component] = {}
            reference = benchmark_sq[year, component]
            for name, days in candidates.items():
                selected = arrays[year][np.array(days) - 1, :, component_index]
                if not np.all(np.isfinite(selected)):
                    raise RuntimeError(f"Missing WDC IQD input: {year} {component} {name} {days}")
                nightly = selected[:, list(NIGHT_HOURS)].mean(axis=1)
                curve = (selected - nightly[:, None]).mean(axis=0)
                metrics = curve_metrics(curve, reference)
                metrics.update({"days": days, "benchmark_mean_24h_nT": float(reference.mean()),
                                "benchmark_night_mean_nT": float(reference[list(NIGHT_HOURS)].mean()),
                                "candidate_night_mean_nT": float(curve[list(NIGHT_HOURS)].mean()),
                                "candidate_mean_24h_nT": float(curve.mean())})
                sq_results[year][component][name] = metrics
                add(evidence, evidence_type="sq_iqd_candidate", year=year, component=component,
                    candidate=name, days_1based="|".join(map(str, days)),
                    source_file=file_structure[component]["Sq"]["file"],
                    source_sha256=input_hashes[file_structure[component]["Sq"]["file"]],
                    rows=24, columns=len(days), valid_count=24 * len(days), **{k: metrics[k] for k in (
                        "correlation", "rmse_nT", "max_abs_nT", "mean_residual_nT",
                        "shape_rmse_nT", "shape_max_abs_nT", "amplitude_nT",
                        "benchmark_amplitude_nT", "amplitude_delta_nT")},
                    note="Primary curve subtracts per-day mean of HH=0,1,2,3,23; shape metric removes only additive offset diagnostically")
    for component in "XYZ":
        opts = sq_results[2016][component]
        logger.info("2016 Sq %s: shape RMSE official=%.6f, replace=%.6f, omit=%.6f nT",
                    component, opts["official_Q1_Q5"]["shape_rmse_nT"],
                    opts["replace_29_with_Q6"]["shape_rmse_nT"],
                    opts["omit_29_no_replacement"]["shape_rmse_nT"])

    pca_confirmed = all(map_scores[y][c][0]["dropped_day"] == 29
                        and map_scores[y][c][0]["rmse_nT"] < 0.1
                        and map_scores[y][c][1]["rmse_nT"] > 1.5 * map_scores[y][c][0]["rmse_nT"]
                        for y in YEARS for c in "XZ")
    iqd_shape_favors_official = all(
        sq_results[2016][c]["official_Q1_Q5"]["shape_rmse_nT"] <
        min(sq_results[2016][c]["replace_29_with_Q6"]["shape_rmse_nT"],
            sq_results[2016][c]["omit_29_no_replacement"]["shape_rmse_nT"])
        for c in "XYZ")
    pca_status = "CONFIRMED" if pca_confirmed else "UNRESOLVED"
    iqd_status = "PROVISIONAL" if iqd_shape_favors_official else "UNRESOLVED"

    with (D1 / "D1_evidence.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=EVIDENCE_FIELDS)
        writer.writeheader()
        writer.writerows(evidence)

    # Hash every raw file again after computation; no raw or G0 output is modified.
    assert_raw_unchanged(expected, "After D1", logger)
    g0_after = {relative(p): sha(p) for p in g0_paths}
    if g0_after != g0_before:
        raise RuntimeError("G0 report/validation/manifest hash changed during D1")
    logger.info("G0 report/validation/manifest SHA-256 unchanged")
    logger.info("D1-PCA=%s, D1-IQD=%s; G1 not evaluated", pca_status, iqd_status)
    for handler in logger.handlers:
        handler.flush()

    validation = {
        "schema": "Auto-SqPCA-D1-validation-v1",
        "scope": "February leap-day diagnostic only; no D2, full PCA, DTW, DIFI, classifier",
        "protocol_version": "G0-registration-1", "source_paper": "https://arxiv.org/pdf/2103.13899",
        "parameters": {"components": list("XYZ"), "leap_years": list(YEARS),
                       "night_hour_indices_0based": list(NIGHT_HOURS),
                       "night_time_interpretation": "00:30,01:30,02:30,03:30,23:30 in source; WDC HH:00 rows used provisionally",
                       "quiet_day_order": "GFZ Q1-Q10; candidate 2 substitutes Q6 for Q5=29; candidate 3 uses Q1-Q4",
                       "daily_baseline": "mean of the five selected night hours per day, subtracted before averaging days",
                       "missing_policy": "No interpolation in Sq; selected IQD hours must all be finite; incomplete day excluded from calendar mapping score",
                       "calendar_score": "Median constant offset between WDC complete-day 24h mean and Mendeley meanField; RMSE over remaining complete days",
                       "shape_metric": "Remove each 24-hour series mean solely to diagnose additive offset; not a replacement baseline",
                       "svd": "2008 February X only; V0,V1,V2,V3 × 28/29 days; no final centering choice"},
        "input_sha256": input_hashes, "raw_integrity": {"files_checked_before": raw_count,
            "files_checked_after": raw_count, "all_match_G0_manifest": True,
            "G0_key_files_before": g0_before, "G0_key_files_after": g0_after},
        "mendeley_structure": file_structure,
        "mendeley_Y_Z_meanField_identical_sha256": yz_duplicate,
        "gfz_february_Q1_Q10": {str(k): val for k, val in quiet.items()},
        "wdc_february": {str(y): {"hourly_rows": 696, "feb29_hours": 24,
            "feb29_finite_XYZ": {c: int(np.isfinite(arrays[y][28, :, i]).sum()) for i, c in enumerate("XYZ")},
            "missing_XYZ_month": {c: int(np.isnan(arrays[y][:, :, i]).sum()) for i, c in enumerate("XYZ")}}
            for y in YEARS},
        "calendar_mapping_sorted": {str(y): map_scores[y] for y in YEARS},
        "limited_svd_2008_X": svd_results, "sq_iqd_metrics": {str(y): sq_results[y] for y in YEARS},
        "decisions": {"D1-PCA": {"status": pca_status,
            "handling": "Use February days 1–28 for PCA matrices; exclude 29 February in leap years" if pca_confirmed else None,
            "basis": "28 indexed per-year rows, exact 308 year-major combined meanField, and X/Z independent WDC calendar mapping"},
            "D1-IQD": {"status": iqd_status,
            "handling_hypothesis": "Keep official GFZ Q1–Q5, including 29 February 2016" if iqd_shape_favors_official else None,
            "basis": "2016 X/Y/Z Sq curve shapes favor official Q5=29; absolute residual retains unexplained baseline offset and time convention awaits D2"}},
        "G1_status": "NOT_EVALUATED: D2 not run",
        "limitations": ["WDC HH:00 versus source HH:30 not resolved (D2).",
                        "Published Sq columns have 24h mean near zero, whereas night-baseline candidates have night-hour mean zero; source calculation or export includes an unreported additive centering step.",
                        "Mendeley February Y meanField is byte-identical to Z meanField; Y excluded from calendar mapping vote.",
                        "WDC data may differ from data used by authors; no D2 comparison performed.",
                        "V0–V3 SVD results diagnose calendar only and do not choose preprocessing.",
                        "Potential source/protocol inconsistency (S7) in benchmark Sq baseline and duplicated Y/Z meanField requires review before later gates."],
        "errors": [], "evidence_rows": len(evidence), "python": sys.version,
        "numpy_version": np.__version__, "platform": platform.platform(), "script_sha256": sha(Path(__file__)),
    }
    (D1 / "D1_validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(validation, evidence)
    write_checksums_and_review_zip()


def fnum(x: float, digits: int = 3) -> str:
    return f"{x:.{digits}f}"


def write_report(v: dict, evidence: list[dict]) -> None:
    s = v["sq_iqd_metrics"]["2016"]
    lines = [
        "# D1 — Diagnosis 29 Februari pada PCA dan Sq IQD",
        "",
        f"**D1-PCA: {v['decisions']['D1-PCA']['status']}. D1-IQD: {v['decisions']['D1-IQD']['status']}.** G1 belum dinilai karena D2 belum dijalankan.",
        "",
        "## Acuan dan parameter yang dikunci untuk D1",
        "",
        "Protokol `G0-registration-1` (DOCX SHA-256 tercatat di `D1_validation.json`) membatasi D1 pada U1/U2. Artikel data asli menyatakan semua matriks PCA Februari 24×28, Sq adalah rata-rata lima IQD GFZ, dan baseline malam per hari memakai 00:30, 01:30, 02:30, 03:30, 23:30 UTC. Artikel mencetak `02:03`; Tabel 2 memetakan indeks 3 ke 02:30, sehingga D1 memakai indeks jam 0,1,2,3,23. [Artikel data Morozova dkk. 2021](https://arxiv.org/pdf/2103.13899), hlm. 11–13.",
        "",
        "Deret WDC berstempel HH:00 dipasangkan sementara dengan jam bernomor 1–24 pada Mendeley. Makna HH:00 terhadap HH:30 baru diuji di D2. Tidak ada interpolasi untuk Sq; semua jam pada IQD terpilih harus valid. Baseline malam dikurangi **pada setiap hari sebelum** lima kurva dirata-ratakan. Semua selisih dan amplitudo memakai nT berdasarkan artikel sumber.",
        "",
        "## A. Struktur Mendeley dan kalender",
        "",
        "| Komponen | meanField per tahun | EOF1 per tahun | meanField gabungan | EOF1 gabungan | VF1 | Sq Februari |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for c in "XYZ":
        q = v["mendeley_structure"][c]
        lines.append(f"| {c} | {q['meanField']['rows']}×{q['meanField']['columns']} | {q['EOF1']['rows']}×{q['EOF1']['columns']} | {q['meanField_y_all']['rows']}×{q['meanField_y_all']['columns']} | {q['EOF1_y_all']['rows']}×{q['EOF1_y_all']['columns']} | {q['VF1']['rows']}×2 | {q['Sq']['rows']}×{q['Sq']['columns']} |")
    lines += [
        "",
        "Per tahun, indeks `day` adalah tepat 1–28 untuk ketiga komponen dan semua kolom 2007–2017. `meanField_m02_y_all` mempunyai indeks 1–308 dan isinya **identik secara teks** dengan sebelas blok tahun × 28 hari dalam urutan tahun lalu hari. `EOF1_y_all_m02` memiliki 341 indeks, tetapi hanya 1–308 numerik; 309–341 adalah 33 `NA` di ujung. Nilai EOF gabungan berasal dari PCA gabungan dan bukan salinan EOF per tahun. `VF1_m02.dat` tidak mempunyai header: 11 baris `y.YYYY` serta `y.all`. Sq Februari mempunyai indeks jam `h=1–24`, kolom `Sq.y.2007` sampai `Sq.y.2017` dan kolom SD/S.",
        "",
        "WDC Februari 2008, 2012, dan 2016 masing-masing mempunyai 696 timestamp unik HH:00 dan **24 jam pada 29 Februari** untuk X/Y/Z. IQD GFZ Q1–Q5: 2008 = 24,25,22,26,9; 2012 = 17,23,12,2,16; 2016 = 22,28,27,21,29. Jadi 29 Februari hanya berada dalam lima IQD pada 2016. Seluruh jam pada enam kandidat hari tenang 2016 tersedia tanpa sentinel.",
        "",
        "### Hari mana yang tidak dipakai PCA?",
        "",
        "Untuk setiap kemungkinan penghapusan satu hari dari 1–29, rerata 24 jam WDC X/Z dicocokkan ke `meanField` Mendeley dengan satu offset konstan yang diperkirakan dari median selisih. Hari WDC yang tak lengkap tidak ikut skor; Februari 2016 memiliki tiga nilai XYZ hilang pada hari 4. Offset hanya membantu identifikasi indeks kalender, bukan keputusan centering D3.",
        "",
        "| Tahun | Komponen | Hari dibuang terbaik: RMSE | Pesaing terbaik berikutnya: RMSE | Hari valid |",
        "|---:|:---:|---:|---:|---:|",
    ]
    for year in YEARS:
        for component in "XZ":
            top = v["calendar_mapping_sorted"][str(year)][component]
            lines.append(f"| {year} | {component} | {top[0]['dropped_day']}: {fnum(top[0]['rmse_nT'], 4)} nT | {top[1]['dropped_day']}: {fnum(top[1]['rmse_nT'], 4)} nT | {top[0]['valid_days']} |")
    lines += [
        "",
        "Berkas `COI_Y_meanField_m02.dat` dan `COI_Z_meanField_m02.dat` memiliki SHA-256 identik. Karena anomali sumber itu, Y **tidak** dipakai sebagai suara independen untuk pemetaan hari. X dan Z masing-masing memilih hari 29 pada ketiga tahun, dengan galat terendah <0,1 nT dan pesaing yang lebih buruk. Indeks serta blok gabungan mendukung pemakaian tanggal 1–28, tanpa penggantian hari lain.",
        "",
        "### SVD terbatas: Februari 2008 X",
        "",
        "| Centering diagnostik | 28 hari: VF1 / abs(r EOF1) | 29 hari: VF1 / abs(r EOF1) |",
        "|---|---:|---:|",
    ]
    svd = {(x["variant"], x["days"]): x for x in v["limited_svd_2008_X"]}
    for variant in ("V0", "V1", "V2", "V3"):
        a, b = svd[variant, 28], svd[variant, 29]
        lines.append(f"| {variant} | {a['vf1']:.6f} / {a['eof1_abs_corr']:.6f} | {b['vf1']:.6f} / {b['eof1_abs_corr']:.6f} |")
    lines += [
        "",
        f"Benchmark VF1 X 2008 = {svd['V1', 28]['benchmark_vf1']:.6f}. SVD hanya menguji panjang kalender pada X Februari 2008, tanpa interpolasi karena seluruh nilainya valid. Perbandingan EOF memakai korelasi absolut karena tanda SVD bebas dan 29 hari dibandingkan pada 28 posisi pertama. VF/EOF mendukung 28 hari pada V1, tetapi tidak dipakai untuk memilih centering final; V0–V3 tetap urusan D3.",
        "",
        "## B. Tiga kandidat Sq IQD Februari 2016",
        "",
        "1. `official_Q1_Q5`: 22,28,27,21,29.",
        "2. `replace_29_with_Q6`: 22,28,27,21,10.",
        "3. `omit_29_no_replacement`: 22,28,27,21.",
        "",
        "Setiap kurva dihitung dari data WDC hourly setelah rerata lima jam malam **per hari** dikurangi. Kolom RMSE dan maksimum adalah selisih absolut terhadap `Sq.y.2016` Mendeley. RMSE bentuk menghilangkan **hanya offset aditif** dari masing-masing kurva untuk diagnosis; itu bukan perubahan baseline metode. Amplitudo ialah maksimum–minimum 24 jam.",
        "",
        "| Komp. | Kandidat | r | RMSE (nT) | Maks. (nT) | RMSE bentuk (nT) | Amplitudo (nT) | Δ amplitudo vs acuan (nT) |",
        "|:---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for c in "XYZ":
        for name in ("official_Q1_Q5", "replace_29_with_Q6", "omit_29_no_replacement"):
            m = s[c][name]
            lines.append(f"| {c} | `{name}` | {m['correlation']:.6f} | {m['rmse_nT']:.4f} | {m['max_abs_nT']:.4f} | {m['shape_rmse_nT']:.4f} | {m['amplitude_nT']:.3f} | {m['amplitude_delta_nT']:+.3f} |")
    lines += [
        "",
        "Pada X/Y/Z, kandidat resmi mempunyai korelasi tertinggi dan RMSE bentuk terkecil. RMSE absolut **tidak** selalu memilihnya karena offset benchmark: semua kolom Sq Mendeley yang diperiksa mempunyai mean 24 jam mendekati nol, sedangkan baseline malam per hari membuat mean **lima jam malam** kurva kandidat nol. Sebagai kontrol, IQD resmi 2008/2012 juga memperlihatkan offset tetapi kesesuaian bentuk tinggi; metriknya ada di `D1_validation.json` dan `D1_evidence.csv`. Ketidaksesuaian level ini menunjukkan langkah pemusatan tambahan atau perbedaan ekspor/metode yang belum dijelaskan oleh teks artikel. D1 tidak mengubah baseline atau menyesuaikan offset untuk metrik absolut.",
        "",
        "## Keputusan terpisah dan batas bukti",
        "",
        "**D1-PCA — CONFIRMED:** tanggal 1–28 dipakai dalam matriks PCA Februari 2008/2012/2016; 29 Februari dikeluarkan. Dasarnya indeks per tahun, 308 posisi gabungan, dan pencocokan urutan harian X/Z terhadap WDC untuk semua kemungkinan satu hari dibuang. Y `meanField` duplikat Z adalah anomali berkas yang harus dibawa ke D3.",
        "",
        "**D1-IQD — PROVISIONAL:** referensi Sq IQD Februari 2016 paling konsisten secara bentuk dengan lima IQD resmi, **termasuk 29 Februari**; penggantian dengan Q6 atau penghapusan tanpa penggantian lebih buruk pada X/Y/Z. Konvensi HH:00 WDC terhadap HH:30 artikel menunggu D2; offset absolut Mendeley juga belum terjelaskan. Karena itu belum ada klaim reproduksi numerik penuh atau atribusi seluruh selisih kepada hari kabisat.",
        "",
        "**G1 belum PASS:** G1 mensyaratkan D1 dan D2. D2 tidak dijalankan di sini. Anomali meanField Y/Z dan mean Sq yang bertentangan dengan ekspektasi baseline malam ditandai sebagai potensi kondisi S7 dan memerlukan investigasi sebelum gate berikutnya; protokol tidak diubah. SVD V0–V3 dan RMSE bentuk adalah diagnostik tambahan, bukan pemilihan preprocessing atau toleransi baru.",
        "",
        "## Jejak audit",
        "",
        f"`D1_validation.json` mencatat SHA-256 {len(v['input_sha256'])} berkas input yang dipakai, parameter, seluruh 29 alternatif penghapusan/tahun/komponen, metrik kandidat, dan versi Python/NumPy. Semua {v['raw_integrity']['files_checked_before']:,} berkas raw cocok dengan SHA-256 manifest G0 **sebelum dan sesudah** eksekusi; SHA-256 laporan, validasi, dan manifest G0 juga tidak berubah. `D1_evidence.csv` berisi {v['evidence_rows']} baris bukti, termasuk input hash per baris. `D1_review.zip` hanya memuat laporan, kode, tabel, JSON, checksum, dan log kecil; tidak berisi data mentah.",
        "",
    ]
    (D1 / "D1_feb29_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_checksums_and_review_zip() -> None:
    included = ["D1_feb29_report.md", "D1_evidence.csv", "D1_validation.json",
                "D1_execution.log", "d1_feb29.py"]
    checksum_file = D1 / "D1_checksums.sha256"
    checksum_file.write_text("".join(f"{sha(D1 / name)}  {name}\n" for name in included), encoding="ascii")
    included.append(checksum_file.name)
    archive_path = D1 / "D1_review.zip"
    with zipfile.ZipFile(archive_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in included:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (D1 / name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None or sorted(archive.namelist()) != sorted(included):
            raise RuntimeError("D1_review.zip CRC/member verification failed")
    (D1 / "D1_review.sha256").write_text(f"{sha(archive_path)}  D1_review.zip\n", encoding="ascii")


if __name__ == "__main__":
    main()
