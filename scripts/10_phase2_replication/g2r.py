"""G2-R staged execution. Run preflight, development, holdout, final in order."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import platform
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np

from pca_core import NIGHT, VARIANTS, decompose, mode, orient

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RAW = ROOT / "phase2a/raw"
MEN = RAW / "mendeley/jcmdrm5f5x-1"
YEARS = range(2007, 2018)
DEV = ((2017, 6), (2017, 10), (None, 6))
HOLD = ((2009, 1), (2015, 3), (None, 10))
COMP = "XYZ"
CODE = ("pca_core.py", "g2r.py", "k11_loader.py", "tests/test_pca_core.py", "tests/test_k11_loader.py")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def dump(name: str, data: object) -> None:
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def table(name: str, records: list[dict], fields: list[str]) -> None:
    with (OUT / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(records)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def log(message: str) -> None:
    line = f"{now()} {message}"
    print(line, flush=True)
    with (OUT / "G2R_execution.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def assert_g0_manifest() -> dict:
    manifest = ROOT / "phase2a/G0/input_manifest.csv"
    rows = read_csv(manifest)
    mismatches = []
    for r in rows:
        p = ROOT / r["relative_path"]
        if not p.is_file() or sha(p).lower() != r["sha256"].lower():
            mismatches.append(r["relative_path"])
    if mismatches:
        raise RuntimeError(f"G0 manifest mismatch: {mismatches[:10]}")
    return {"rows": len(rows), "sha256": sha(manifest), "mismatches": 0}


def frozen_files() -> dict[str, str]:
    paths = []
    for folder in ("G0", "D1", "D2", "S7", "S7B", "S7C"):
        paths.extend(p for p in (ROOT / "phase2a" / folder).rglob("*") if p.is_file())
    paths.extend(p for p in (ROOT / "phase2a/raw/wdc_format_hourly").rglob("*") if p.is_file())
    return {rel(p): sha(p) for p in sorted(paths)}


def verify_frozen(stage: str) -> dict:
    before = json.loads((OUT / "G2R_preflight.json").read_text(encoding="utf-8"))["frozen_sha256_before"]
    after = frozen_files()
    bad = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    if bad:
        raise RuntimeError(f"Frozen artifacts changed at {stage}: {bad[:10]}")
    g0 = assert_g0_manifest()
    log(f"{stage}: frozen {len(before)} files unchanged; G0 {g0['rows']} hashes match")
    return g0


def policy() -> tuple[dict, dict]:
    base = {r["relative_path"]: r for r in read_csv(ROOT / "phase2a/S7B/S7B_benchmark_policy.csv")}
    delta = {r["relative_path"]: r for r in read_csv(ROOT / "phase2a/S7C/S7C_benchmark_policy_delta.csv")}
    return base, delta


def find_dat(name: str) -> Path:
    hits = list(MEN.rglob(name))
    if len(hits) != 1:
        raise RuntimeError(f"Mendeley DAT uniqueness {name}: {len(hits)} matches")
    return hits[0]


def target_files(year: int | None, month: int, component: str) -> dict[str, Path]:
    mm = f"m{month:02d}"
    f = {}
    for k in (1, 2, 3):
        f[f"pc{k}"] = find_dat(f"COI_{component}_PC{k}_{mm}.dat")
        f[f"eof{k}"] = find_dat(f"COI_{component}_EOF{k}_{mm}.dat" if year is not None else f"COI_{component}_EOF{k}_y_all_{mm}.dat")
        if k <= 2:  # Mendeley v1 has no mode3 DAT; PC3*EOF3 defines mode3.
            f[f"mode{k}"] = find_dat(f"COI_{component}_mode{k}_{mm}.dat" if year is not None else f"COI_{component}_mode{k}_{mm}_y_all.dat")
        f[f"vf{k}"] = find_dat(f"COI_{component}_VF{k}_{mm}.dat")
    f["meanfield"] = find_dat(f"COI_{component}_meanField_{mm}.dat" if year is not None else f"COI_{component}_meanField_{mm}_y_all.dat")
    return f


def eligibility(year: int | None, month: int, component: str, files: dict[str, Path]) -> tuple[bool, str]:
    base, delta = policy()
    failures = []
    for key, p in files.items():
        r = base.get(rel(p))
        if r is None:
            failures.append(f"{key}:NO_POLICY")
            continue
        if sha(p) != r["sha256"]:
            failures.append(f"{key}:HASH_MISMATCH")
        if r["allowed_use"] != "ORIGINAL_ABSOLUTE" or r["d3_eligible"].lower() != "true":
            failures.append(f"{key}:{r['allowed_use']}/d3={r['d3_eligible']}")
        d = delta.get(rel(p))
        if d and (year is None or str(year) == d["target_year"]):
            if d["allowed_use"] != "ORIGINAL_ABSOLUTE" or d["d3_eligible"].lower() != "true":
                failures.append(f"{key}:S7C_{d['allowed_use']}")
    return not failures, ";".join(failures)


def tab(path: Path) -> tuple[list[str], list[list[str]]]:
    rows = read_csv_tsv(path)
    if len(rows) < 2 or len(set(map(len, rows))) != 1:
        raise RuntimeError(f"Invalid DAT table {rel(path)}")
    return rows[0], rows[1:]


def read_csv_tsv(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.reader(f, delimiter="\t"))


def vector_by_header(path: Path, header: str) -> np.ndarray:
    headers, rows = tab(path)
    if header not in headers:
        raise RuntimeError(f"{rel(path)} lacks {header}")
    return np.array([float(r[headers.index(header)]) for r in rows], dtype=np.float64)


def eof_combined(path: Path, n: int) -> np.ndarray:
    h, rows = tab(path)
    if len(h) != 2 or len(rows) < n:
        raise RuntimeError(f"Combined EOF shape {rel(path)}: {len(rows)}")
    vals = [float(r[1]) for r in rows[:n]]
    if any(r[1] != "NA" for r in rows[n:]):
        raise RuntimeError(f"Combined EOF padding not NA: {rel(path)}")
    return np.array(vals, dtype=np.float64)


def scalar_by_header(path: Path, header: str) -> float:
    h, rows = tab(path)
    d = dict(rows)
    if header not in d:
        raise RuntimeError(f"{rel(path)} lacks {header}")
    return float(d[header])


def benchmark(files: dict[str, Path], year: int | None, n: int) -> dict:
    header = f"y.{year}" if year is not None else "y.all"
    pcs, eofs, modes, vfs = [], [], [], []
    for k in (1, 2, 3):
        pc = vector_by_header(files[f"pc{k}"], header)
        eof = vector_by_header(files[f"eof{k}"], header) if year is not None else eof_combined(files[f"eof{k}"], n)
        if len(pc) != 24 or len(eof) != n:
            raise RuntimeError(f"Benchmark PC/EOF dimension k{k}: {len(pc)},{len(eof)} expected 24,{n}")
        if k <= 2:
            raw = vector_by_header(files[f"mode{k}"], header) if year is not None else vector_by_header(files[f"mode{k}"], "meanField")
            if len(raw) != 24 * n:
                raise RuntimeError(f"Benchmark mode dimension k{k}: {len(raw)} expected {24*n}")
            observed_mode = raw.reshape(n, 24).T
        else:
            observed_mode = np.outer(pc, eof)
        pcs.append(pc)
        eofs.append(eof)
        modes.append(observed_mode)
        vfs.append(scalar_by_header(files[f"vf{k}"], header))
    mean = vector_by_header(files["meanfield"], header) if year is not None else None
    return {"pcs": pcs, "eofs": eofs, "modes": modes, "vf": np.array(vfs), "mean": mean}


def load_month(year: int, month: int, component: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    import calendar
    path = RAW / "wdc_hourly" / f"COI_{year}_hour_iaga_XYZF.zip"
    n = calendar.monthrange(year, month)[1]
    values = np.full((n, 24), np.nan)
    seen = np.zeros((n, 24), dtype=bool)
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"WDC ZIP CRC failed: {path}: {bad}")
        name = f"coi{year}{month:02d}dhor.hor"
        lines = archive.read(name).decode("ascii").splitlines()
    flags = set()
    for line in lines:
        if line.startswith(" Format") and "IAGA-2002" in line: flags.add("format")
        if line.startswith(" Reported") and "XYZF" in line: flags.add("xyzf")
        if line.startswith(" IAGA Code") and "COI" in line: flags.add("coi")
        if not re.match(r"^\d{4}-\d{2}-\d{2} ", line):
            continue
        fields = line.split()
        if len(fields) != 7:
            raise RuntimeError(f"WDC row width {name}: {line}")
        date = dt.date.fromisoformat(fields[0])
        if (date.year, date.month) != (year, month) or not re.fullmatch(r"\d\d:00:00\.000", fields[1]):
            raise RuntimeError(f"WDC timestamp {name}: {fields[:2]}")
        d, h = date.day - 1, int(fields[1][:2])
        if seen[d, h]: raise RuntimeError(f"WDC duplicate {name}: {fields[:2]}")
        seen[d, h] = True
        val = float(fields["XYZ".index(component) + 3])
        if abs(val) < 88888: values[d, h] = val
    if flags != {"format", "xyzf", "coi"} or not seen.all():
        raise RuntimeError(f"WDC header/clock incomplete {name}: flags={flags}, seen={seen.sum()}/{seen.size}")
    original_missing = ~np.isfinite(values)
    # Interpolate within a month only; never extrapolate boundaries.
    flat = values.reshape(-1)
    observed = np.flatnonzero(np.isfinite(flat))
    if len(observed) >= 2:
        interior = np.arange(observed[0], observed[-1] + 1)
        flat[interior] = np.interp(interior, observed, flat[observed])
    unresolved = (~np.isfinite(values)).sum(axis=1)
    interpolated = original_missing.sum(axis=1) - unresolved
    return values, interpolated, unresolved


def matrix(year: int | None, month: int, component: str) -> tuple[np.ndarray, dict]:
    years = [year] if year is not None else list(YEARS)
    blocks = []
    per_day = []
    for y in years:
        vals, interpolated, unresolved = load_month(y, month, component)
        if month == 2 and len(vals) == 29:
            vals, interpolated, unresolved = vals[:28], interpolated[:28], unresolved[:28]
        blocks.append(vals)
        per_day.extend({"year": y, "day": d + 1, "interpolated": int(interpolated[d]),
                        "flag_gt12": bool(interpolated[d] > 12), "unresolved": int(unresolved[d])} for d in range(len(vals)))
    a = np.concatenate(blocks, axis=0).T
    return a, {"days": per_day, "unresolved_hours": int(np.isnan(a).sum()),
               "interpolated_hours": sum(d["interpolated"] for d in per_day),
               "days_gt12_interpolated": sum(d["flag_gt12"] for d in per_day)}


def preflight() -> None:
    unit_log = (OUT / "G2R_unit_tests.log").read_text(encoding="utf-8")
    if "6 passed" not in unit_log and "8 passed" not in unit_log:
        raise RuntimeError("Six PCA unit tests must pass before observational data")
    source = Path("D:/Downloads/G2-R_protokol_K10.md")
    protocol = OUT / "G2R_protocol_v1.md"
    if sha(source) != sha(protocol): raise RuntimeError("Protocol copy mismatch")
    g0 = assert_g0_manifest()
    previous = json.loads((ROOT / "phase2a/S7C/S7C_preflight.json").read_text(encoding="utf-8"))["frozen_outputs_sha256_before"]
    current = frozen_files()
    mismatches = {k: [v, current.get(k)] for k, v in previous.items() if current.get(k) != v}
    if mismatches: raise RuntimeError(f"Pre-S7C frozen mismatch: {list(mismatches)[:10]}")
    data = {"utc": now(), "protocol_sha256": sha(protocol), "G0_manifest": g0,
            "prior_pre_S7C_files_checked": len(previous), "prior_hash_mismatches": mismatches,
            "frozen_sha256_before": current,
            "G1_registration2": "HOLD", "G1_registration3": "HOLD"}
    dump("G2R_preflight.json", data)
    log(f"preflight: protocol {data['protocol_sha256']}; {len(previous)} historical frozen hashes and {len(current)} current frozen hashes recorded; G0 {g0['rows']} match")


def corr(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.corrcoef(a, b)[0, 1])


def subspace_angle(a: np.ndarray, b: np.ndarray) -> float:
    qa, _ = np.linalg.qr(a)
    qb, _ = np.linalg.qr(b)
    s = np.linalg.svd(qa.T @ qb, compute_uv=False)
    return float(np.degrees(np.arccos(np.clip(s.min(), -1, 1))))


def metrics(a: np.ndarray, bench: dict, result: dict, component: str, year: int | None, month: int, variant: str, scale_ok: bool) -> dict:
    n = a.shape[1]
    singular = result["singular_values"]
    lam = singular * singular
    pc_corr = []
    pc_pass = []
    pc_degenerate = []
    angles = []
    for k in range(3):
        c = abs(corr(result["pc"][:, k], bench["pcs"][k]))
        deg = k < 2 and abs(lam[k] - lam[k+1]) < lam[k] * math.sqrt(2 / n)
        angle = subspace_angle(result["pc"][:, k:k+2], np.column_stack(bench["pcs"][k:k+2])) if deg else None
        pc_corr.append(c)
        pc_degenerate.append(deg)
        angles.append(angle)
        pc_pass.append(angle <= 5 if deg else c >= 0.999)
    vf_diff = np.abs(result["vf"][:3] - bench["vf"])
    model_modes = [mode(result, k) for k in range(3)]
    observed_sum = sum(bench["modes"])
    frob = float(np.linalg.norm(sum(model_modes) - observed_sum) / np.linalg.norm(observed_sum))
    eof_rmse = []
    for k in range(3):
        if scale_ok:
            _, eof = orient(result["pc"][:, k], result["eof"][k], bench["pcs"][k])
            eof_rmse.append(float(np.sqrt(np.mean((eof - bench["eofs"][k])**2))))
        else:
            eof_rmse.append(None)
    vf_pass = bool(np.all(vf_diff <= 0.005))
    overall = frob <= 0.01 and vf_pass and all(pc_pass) and (not scale_ok or all(e <= 0.1 for e in eof_rmse))
    return {"set": "development" if (year, month) in DEV else "holdout", "year": year if year is not None else "combined", "month": month,
            "component": component, "variant": variant, "status": "ELIGIBLE", "frob_relative": frob,
            "vf1_diff": float(vf_diff[0]), "vf2_diff": float(vf_diff[1]), "vf3_diff": float(vf_diff[2]), "vf_pass": vf_pass,
            "pc1_abs_r": pc_corr[0], "pc2_abs_r": pc_corr[1], "pc3_abs_r": pc_corr[2],
            "pc1_degenerate": pc_degenerate[0], "pc2_degenerate": pc_degenerate[1], "pc3_degenerate": pc_degenerate[2],
            "pc1_subspace_angle_deg": angles[0], "pc2_subspace_angle_deg": angles[1], "pc3_subspace_angle_deg": angles[2],
            "pc1_pass": pc_pass[0], "pc2_pass": pc_pass[1], "pc3_pass": pc_pass[2],
            "eof1_rmse": eof_rmse[0], "eof2_rmse": eof_rmse[1], "eof3_rmse": eof_rmse[2],
            "eof_scale_confirmed": scale_ok, "overall_pass": overall}


METRIC_FIELDS = ["set", "year", "month", "component", "variant", "status", "frob_relative", "vf1_diff", "vf2_diff", "vf3_diff", "vf_pass", "pc1_abs_r", "pc2_abs_r", "pc3_abs_r", "pc1_degenerate", "pc2_degenerate", "pc3_degenerate", "pc1_subspace_angle_deg", "pc2_subspace_angle_deg", "pc3_subspace_angle_deg", "pc1_pass", "pc2_pass", "pc3_pass", "eof1_rmse", "eof2_rmse", "eof3_rmse", "eof_scale_confirmed", "overall_pass"]
INV_FIELDS = ["set", "year", "month", "component", "status", "eligibility_reason", "rows_hours", "columns_days", "interpolated_hours", "days_gt12_interpolated", "unresolved_hours", "benchmark_hashes_sha256", "benchmark_files"]
DAY_FIELDS = ["set", "target_year", "month", "component", "year", "day", "interpolated", "flag_gt12", "unresolved"]
DAY_ROWS: list[dict] = []


def process_target(year: int | None, month: int, component: str, variants: tuple[str, ...], group: str) -> tuple[dict, list[dict], dict | None, dict | None]:
    files = target_files(year, month, component)
    eligible, reason = eligibility(year, month, component, files)
    hashes = {key: sha(p) for key, p in files.items()}
    inventory = {"set": group, "year": year if year is not None else "combined", "month": month, "component": component,
                 "status": "ELIGIBLE" if eligible else "NOT_ELIGIBLE", "eligibility_reason": reason,
                 "benchmark_hashes_sha256": hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
                 "benchmark_files": json.dumps({k: rel(v) for k, v in files.items()}, sort_keys=True)}
    if not eligible:
        log(f"{group} {year}/{month:02d} {component}: NOT_ELIGIBLE {reason}")
        return inventory, [], None, None
    a, info = matrix(year, month, component)
    DAY_ROWS.extend({"set": group, "target_year": year if year is not None else "combined",
                     "month": month, "component": component, **d} for d in info["days"])
    inventory.update(rows_hours=24, columns_days=a.shape[1], interpolated_hours=info["interpolated_hours"],
                     days_gt12_interpolated=info["days_gt12_interpolated"], unresolved_hours=info["unresolved_hours"])
    if info["unresolved_hours"]:
        inventory["status"] = "UNRESOLVED_MISSING"
        log(f"{group} {year}/{month:02d} {component}: unresolved boundary missing {info['unresolved_hours']}")
        return inventory, [], None, None
    bench = benchmark(files, year, a.shape[1])
    norms = [float(np.linalg.norm(x)) for x in bench["pcs"]]
    product_err = [float(np.max(np.abs(np.outer(bench["pcs"][k], bench["eofs"][k]) - bench["modes"][k]))) for k in range(3)]
    scale_ok = all(abs(v - 1) < 1e-8 for v in norms) and all(v <= 1e-8 for v in product_err)
    d4 = {"year": inventory["year"], "month": month, "component": component, "pc_norms": norms,
          "pc_eof_mode_max_abs_error": product_err, "mode3_source": "DERIVED_PC3_TIMES_EOF3_NO_MODE3_DAT",
          "eof_rmse_applicable": scale_ok}
    records = [metrics(a, bench, decompose(a, variant), component, year, month, variant, scale_ok) for variant in variants]
    daily = a.mean(axis=0)
    night = a[list(NIGHT), :].mean(axis=0)
    mf = None
    if year is not None and bench["mean"] is not None:
        mf = {"year": year, "month": month, "component": component,
              "s_daily": float(np.std(daily - bench["mean"], ddof=0)),
              "s_night": float(np.std(night - bench["mean"], ddof=0))}
    log(f"{group} {year}/{month:02d} {component}: {a.shape}, D4_norm={norms}, frob={[round(r['frob_relative'], 5) for r in records]}")
    return inventory, records, mf, d4


def development() -> None:
    verify_frozen("development start")
    inv, rows, mean, d4 = [], [], [], []
    for year, month in DEV:
        for c in COMP:
            i, r, m, scale = process_target(year, month, c, VARIANTS, "development")
            inv.append(i); rows.extend(r)
            if m: mean.append(m)
            if scale: d4.append(scale)
    table("G2R_matrix_inventory.csv", inv, INV_FIELDS)
    table("G2R_interpolated_hours_by_day.csv", DAY_ROWS, DAY_FIELDS)
    table("G2R_dev_metrics.csv", rows, METRIC_FIELDS)
    table("G2R_meanfield_test.csv", mean, ["year", "month", "component", "s_daily", "s_night"])
    dump("G2R_D4_scale.json", d4)
    selections = {}
    for variant in VARIANTS:
        rr = [r for r in rows if r["variant"] == variant]
        f = [r["frob_relative"] for r in rr]
        structure_pass = len(rr) == 9 and all(r["frob_relative"] <= 0.01 and r["vf_pass"] for r in rr) and all(r["pc1_pass"] for r in rr if r["component"] in "YZ")
        selections[variant] = {"eligible_matrices": len(rr), "frob_median": float(np.median(f)) if f else None,
                               "development_pass_all_9": structure_pass,
                               "frob_pass_count": sum(v <= 0.01 for v in f), "vf_pass_count": sum(r["vf_pass"] for r in rr),
                               "pc1_yz_pass_count": sum(r["pc1_pass"] for r in rr if r["component"] in "YZ")}
    passing = [v for v in VARIANTS if selections[v]["development_pass_all_9"]]
    if len(passing) == 1: chosen, rule = passing[0], "6.2 unique_pass"
    elif len(passing) > 1:
        daily_ok = all(m["s_daily"] <= 0.1 for m in mean)
        night_ok = all(m["s_night"] <= 0.1 for m in mean)
        consistent = [v for v in passing if (v == "V1" and daily_ok) or (v == "V3" and night_ok)]
        chosen = min(consistent or passing, key=lambda v: selections[v]["frob_median"])
        rule = "6.3 meanField_tiebreak" if len(consistent) == 1 else "6.3 frob_median_tiebreak"
    else:
        chosen = min(VARIANTS, key=lambda v: selections[v]["frob_median"])
        rule = "6.4 no_variant_pass; DEVIATION_STRUCTURAL"
    choice = {"utc": now(), "variants": selections, "passing": passing, "chosen": chosen, "selection_rule": rule,
              "label": "DEVIATION_STRUCTURAL" if not passing else "DEVELOPMENT_PASS",
              "not_eligible": [f"{i['year']}-{i['month']:02d}:{i['component']}" for i in inv if i["status"] != "ELIGIBLE"],
              "meanfield_tiebreak": {"daily_all_le_0p1": all(m["s_daily"] <= 0.1 for m in mean), "night_all_le_0p1": all(m["s_night"] <= 0.1 for m in mean)}}
    dump("G2R_variant_selection.json", choice)
    frozen = {"frozen_utc": now(), "variant": chosen, "selection_sha256": sha(OUT / "G2R_variant_selection.json"),
              "matrix": "24 hours x N days; hourly COI IAGA-2002 XYZF absolute nT; HH:00 means HH:00-HH:59 centered HH:30 UTC; year-major combined",
              "interpolation": "linear between observed values within each month; no extrapolation; count per day; flag >12; unresolved boundary prevents SVD",
              "feb29": "excluded from PCA", "mode_orientation": "outer(PC_hour,EOF_day), compared with day-major hour-fastest Mendeley",
              "sign": "flip both PC and EOF for negative correlation with Mendeley PC",
              "versions": {"python": sys.version.split()[0], "numpy": np.__version__, "platform": platform.platform()},
              "code_sha256": {n: sha(OUT / n) for n in CODE}}
    dump("G2R_frozen_config.json", frozen)
    (OUT / "G2R_frozen_config.json.sha256").write_text(f"{sha(OUT / 'G2R_frozen_config.json')}  G2R_frozen_config.json\n", encoding="ascii")
    log(f"development complete; chosen {chosen}, rule {rule}; frozen config sha256={sha(OUT / 'G2R_frozen_config.json')}")
    verify_frozen("development end")


def holdout() -> None:
    cfg_path = OUT / "G2R_frozen_config.json"
    line = (OUT / "G2R_frozen_config.json.sha256").read_text().split()[0]
    if not cfg_path.is_file() or sha(cfg_path) != line: raise RuntimeError("Frozen config hash invalid")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    for name, digest in cfg["code_sha256"].items():
        if sha(OUT / name) != digest: raise RuntimeError(f"Code changed after freeze: {name}")
    verify_frozen("holdout start")
    inv = read_csv(OUT / "G2R_matrix_inventory.csv")
    rows, d4 = [], []
    for year, month in HOLD:
        for c in COMP:
            i, r, _, scale = process_target(year, month, c, (cfg["variant"],), "holdout")
            inv.append(i); rows.extend(r)
            if scale: d4.append(scale)
    table("G2R_matrix_inventory.csv", inv, INV_FIELDS)
    existing_days = read_csv(OUT / "G2R_interpolated_hours_by_day.csv")
    table("G2R_interpolated_hours_by_day.csv", existing_days + DAY_ROWS, DAY_FIELDS)
    table("G2R_holdout_metrics.csv", rows, METRIC_FIELDS)
    dump("G2R_D4_holdout_scale.json", d4)
    eligible = [i for i in inv if i["set"] == "holdout" and i["status"] == "ELIGIBLE"]
    ineligible = [i for i in inv if i["set"] == "holdout" and i["status"] != "ELIGIBLE"]
    all_pass = len(rows) == 9 and all(r["overall_pass"] for r in rows)
    yz_pc1 = len([r for r in rows if r["component"] in "YZ"]) == 6 and all(r["pc1_pass"] for r in rows if r["component"] in "YZ")
    frob_count = sum(r["frob_relative"] <= 0.01 for r in rows)
    label = "S-AGREE" if all_pass else "S-PARTIAL" if frob_count >= 6 and yz_pc1 else "S-DEVIATE"
    result = {"label": label, "variant": cfg["variant"], "config_sha256": sha(cfg_path),
              "denominator": {"target_total": 9, "not_eligible": len(ineligible),
                              "suspect": sum("SUSPECT" in str(i["eligibility_reason"]) for i in ineligible),
                              "eligible": len(eligible), "pass": sum(r["overall_pass"] for r in rows),
                              "fail": sum(not r["overall_pass"] for r in rows)},
              "frob_pass": frob_count, "pc1_yz_all_pass": yz_pc1,
              "ineligible": [f"{i['year']}-{int(i['month']):02d}:{i['component']}:{i['eligibility_reason']}" for i in ineligible],
              "utc": now()}
    dump("G2R_result.json", result)
    log(f"holdout complete: {label}, denominator={result['denominator']}")
    verify_frozen("holdout end")


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    {"preflight": preflight, "development": development, "holdout": holdout}[command]()


if __name__ == "__main__":
    main()
