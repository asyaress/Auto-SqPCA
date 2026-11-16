"""G3-R descriptive PCA and G4-R four-pipeline decision comparison."""
from __future__ import annotations

import csv
import functools
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "phase2a/G2R"))
import g2r  # frozen source; do not edit or copy its numerical implementation
import g4r_preflight
from classification_core import CANDIDATES, SEED, candidate_curve, classify_curve, random_phase_surrogates
from pca_core import NIGHT, decompose, orient

# Memoization does not alter the frozen G2-R numerical code or input arrays.
g2r.find_dat = functools.lru_cache(maxsize=None)(g2r.find_dat)
g2r.target_files = functools.lru_cache(maxsize=None)(g2r.target_files)
g2r.load_month = functools.lru_cache(maxsize=None)(g2r.load_month)
g2r.tab = functools.lru_cache(maxsize=None)(g2r.tab)
_frozen_scalar_by_header = g2r.scalar_by_header


def vf_scalar_adapter(path: Path, header: str) -> float:
    """Recover the headerless VF DAT first record (y.2007) without changing G2-R."""
    first, _ = g2r.tab(path)
    if len(first) == 2 and first[0] == header:
        return float(first[1])
    return _frozen_scalar_by_header(path, header)


g2r.scalar_by_header = vf_scalar_adapter

YEARS = range(2007, 2018)
MONTHS = range(1, 13)
COMP = "XYZ"
PIPELINES = ("P-own", "P-pub", "P-mixA", "P-mixB")
CANDIDATE_NAMES = ("PC1", "PC2", "PC3", "PC1+PC2", "PC1+PC3", "PC2+PC3", "PC1+PC2+PC3")


def log(s: str) -> None:
    import datetime as dt
    line = f"{dt.datetime.now(dt.timezone.utc).isoformat()} {s}"
    print(line, flush=True)
    with (HERE / "G4R_execution.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def csv_write(name: str, data: list[dict], fields: list[str]) -> None:
    with (HERE / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(data)


def csv_read(name: str) -> list[dict]:
    with (HERE / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def jwrite(name: str, value: object) -> None:
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def verify_frozen() -> int:
    snapshot = json.loads((HERE / "G4R_preflight.json").read_text(encoding="utf-8"))["all_frozen_files_snapshot"]
    return g4r_preflight.verify_against_before(snapshot)


def targets():
    for year in YEARS:
        for month in MONTHS:
            for c in COMP:
                yield year, month, c
    for month in MONTHS:
        for c in COMP:
            yield None, month, c


def tid(year: int | None, month: int, c: str) -> str:
    return f"{year if year is not None else 'all'}_{month:02d}_{c}"


def scope_status(year: int | None, month: int, c: str) -> str:
    # Series-level interpretation specified explicitly in G4R-v1 section 4.
    if month == 2 and c == "Y": return "EXCLUDED"
    if month == 2 and c == "Z" and (year is None or year == 2014): return "SUSPECT_DIAGNOSTIC"
    if c == "X" and month in (4, 6, 9, 11) and (year is None or year == 2008): return "SUSPECT_DIAGNOSTIC"
    return "ELIGIBLE"


def policy_seen(files: dict, year: int | None, month: int) -> bool:
    base, _ = g2r.policy()
    if (year, month) in g2r.DEV: return True
    return any(base[g2r.rel(p)]["development_seen"].lower() == "true" for p in files.values())


def g3() -> None:
    verify_frozen()
    if "6 passed" not in (HERE / "G4R_unit_tests.log").read_text(encoding="utf-8") and "7 passed" not in (HERE / "G4R_unit_tests.log").read_text(encoding="utf-8"):
        raise RuntimeError("Six classification unit tests must pass before G3-R")
    log("G3-R start: frozen V1 PCA code and unit tests verified")
    rows: list[dict] = []
    cache: dict[str, np.ndarray] = {}
    manifest = {r["relative_path"]: r["sha256"] for r in g2r.read_csv(ROOT / "phase2a/G0/input_manifest.csv")}
    for idx, (year, month, c) in enumerate(targets(), 1):
        status = scope_status(year, month, c)
        base = {"year": year if year is not None else "combined", "month": month, "component": c,
                "scope": "annual" if year is not None else "combined", "policy_status": status,
                "february": month == 2, "development_seen": False, "status": status,
                "interpolated_hours": None, "unresolved_hours": None, "frob_relative": None,
                "vf1_diff": None, "vf2_diff": None, "vf3_diff": None,
                "pc1_abs_r": None, "pc2_abs_r": None, "pc3_abs_r": None,
                "vf_pass": None, "pc1_pass": None, "pc2_pass": None, "pc3_pass": None,
                "frob_pass": None, "structure_all_metrics_pass": None, "error": ""}
        try:
            files = g2r.target_files(year, month, c)
            base["development_seen"] = policy_seen(files, year, month)
            for p in files.values():
                if g2r.rel(p) not in manifest or g2r.sha(p) != manifest[g2r.rel(p)]:
                    raise RuntimeError(f"Mendeley hash mismatch: {g2r.rel(p)}")
            if status == "EXCLUDED":
                rows.append(base)
                continue
            a, info = g2r.matrix(year, month, c)
            base["interpolated_hours"] = info["interpolated_hours"]
            base["unresolved_hours"] = info["unresolved_hours"]
            if info["unresolved_hours"]:
                base["status"] = "UNRESOLVED_MISSING"
                rows.append(base)
                continue
            bench = g2r.benchmark(files, year, a.shape[1])
            pca = decompose(a, "V1")
            m = g2r.metrics(a, bench, pca, c, year, month, "V1", False)
            for key in ("frob_relative", "vf1_diff", "vf2_diff", "vf3_diff", "pc1_abs_r", "pc2_abs_r", "pc3_abs_r",
                        "vf_pass", "pc1_pass", "pc2_pass", "pc3_pass"):
                base[key] = m[key]
            base["frob_pass"] = m["frob_relative"] <= 0.01
            base["structure_all_metrics_pass"] = m["overall_pass"]
            own_pc, own_eof = [], []
            for k in range(3):
                pc, eof = orient(pca["pc"][:, k], pca["eof"][k], bench["pcs"][k])
                own_pc.append(pc); own_eof.append(eof)
            prefix = tid(year, month, c)
            cache[prefix + "_ownpc"] = np.stack(own_pc)
            cache[prefix + "_owneof"] = np.stack(own_eof)
            cache[prefix + "_pubpc"] = np.stack(bench["pcs"])
            cache[prefix + "_pubeof"] = np.stack(bench["eofs"])
            rows.append(base)
        except Exception as e:
            base["status"] = "UNRESOLVED_ERROR"
            base["error"] = f"{type(e).__name__}: {e}"
            rows.append(base)
            log(f"G3-R {tid(year,month,c)}: {base['error']}")
        if idx % 72 == 0: log(f"G3-R processed {idx}/432 targets")
    fields = list(rows[0])
    csv_write("G3R_structure_metrics.csv", rows, fields)
    np.savez_compressed(HERE / "G4R_pca_cache.npz", **cache)
    counts = Counter(r["status"] for r in rows)
    denom = {"target_total": len(rows), "annual_target": 396, "combined_target": 36,
             "status_counts": dict(counts), "development_seen": sum(bool(r["development_seen"]) for r in rows),
             "february": sum(bool(r["february"]) for r in rows),
             "comparable": sum(r["status"] in ("ELIGIBLE", "SUSPECT_DIAGNOSTIC") for r in rows),
             "main_eligible": counts["ELIGIBLE"],
             "main_frob_pass": sum(r["status"] == "ELIGIBLE" and r["frob_pass"] is True for r in rows),
             "main_all_metrics_pass": sum(r["status"] == "ELIGIBLE" and r["structure_all_metrics_pass"] is True for r in rows),
             "cache_sha256": g2r.sha(HERE / "G4R_pca_cache.npz")}
    jwrite("G3R_denominator.json", denom)
    log(f"G3-R done: {dict(counts)}, cache sha256={denom['cache_sha256']}")
    verify_frozen()


MONTH_ABBR = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def gfz_days(year: int, month: int) -> tuple[list[int], Path]:
    path = ROOT / "phase2a/raw/gfz" / f"QD_days{year}.txt"
    line = next((s for s in path.read_text(encoding="utf-8").splitlines()
                 if re.match(rf"^\s*{MONTH_ABBR[month-1]}\s+{year}\s", s)), None)
    if line is None: raise RuntimeError(f"GFZ month not found: {year}-{month:02d}")
    tokens = line.split()[2:7]
    days = [int(re.match(r"^\d+", t).group()) for t in tokens]
    if len(days) != 5 or len(set(days)) != 5:
        raise RuntimeError(f"GFZ Q1-Q5 malformed: {line}")
    return days, path


def own_sq(year: int, month: int, c: str) -> tuple[np.ndarray, list[int], int]:
    days, _ = gfz_days(year, month)
    month_values, interp, unresolved = g2r.load_month(year, month, c)
    if any(d < 1 or d > len(month_values) for d in days):
        raise RuntimeError(f"GFZ quiet day outside calendar: {year}-{month:02d} {days}")
    selected = month_values[np.array(days) - 1]
    if not np.isfinite(selected).all():
        raise RuntimeError(f"IQD WDC unresolved hour: {year}-{month:02d} {c} Q1-Q5={days}")
    baseline = selected[:, list(NIGHT)].mean(axis=1)
    return (selected - baseline[:, None]).mean(axis=0), days, int(interp[np.array(days)-1].sum())


def sq() -> None:
    verify_frozen()
    log("G4-R Sq_IQD own start: GFZ Q1-Q5, nightly baseline")
    refs: dict[str, np.ndarray] = {}
    rows: list[dict] = []
    for month in MONTHS:
        for c in COMP:
            yearly = []
            for year in YEARS:
                base = {"year": year, "month": month, "component": c,
                        "hour_index": None, "sq_iqd_nT": None, "status": "OK",
                        "gfz_quiet_days": "", "feb29_2016_included": year == 2016 and month == 2,
                        "interpolated_iqd_hours": None, "error": ""}
                try:
                    curve, days, filled = own_sq(year, month, c)
                    if year == 2016 and month == 2 and 29 not in days:
                        raise RuntimeError("Expected official GFZ 2016-02 Q1-Q5 to include 29")
                    refs[tid(year,month,c)] = curve
                    yearly.append(curve)
                    base["gfz_quiet_days"] = ",".join(map(str, days))
                    base["interpolated_iqd_hours"] = filled
                    for h, value in enumerate(curve): rows.append({**base, "hour_index": h, "sq_iqd_nT": float(value)})
                except Exception as e:
                    base["status"] = "UNRESOLVED"
                    base["error"] = f"{type(e).__name__}: {e}"
                    rows.append(base)
                    log(f"Sq {tid(year,month,c)}: {base['error']}")
            combined = {"year": "combined", "month": month, "component": c,
                        "hour_index": None, "sq_iqd_nT": None, "status": "OK" if len(yearly)==11 else "UNRESOLVED",
                        "gfz_quiet_days": "55 official Q1-Q5 across 2007-2017",
                        "feb29_2016_included": month == 2, "interpolated_iqd_hours": None,
                        "error": "" if len(yearly)==11 else f"Only {len(yearly)}/11 annual references available"}
            if len(yearly) == 11:
                curve = np.mean(yearly, axis=0)
                refs[tid(None,month,c)] = curve
                for h, value in enumerate(curve): rows.append({**combined, "hour_index": h, "sq_iqd_nT": float(value)})
            else:
                rows.append(combined)
        log(f"Sq_IQD month {month:02d}/12 complete")
    csv_write("G4R_sq_iqd_own.csv", rows, list(rows[0]))
    np.savez_compressed(HERE / "G4R_sq_cache.npz", **refs)
    jwrite("G4R_sq_provenance.json", {"method": "five GFZ Q1-Q5 days, each daily curve minus mean of WDC hourly indices 0,1,2,3,23; average five days; combined average 11 annual curves",
                                      "February_2016": "official Q1-Q5 includes 29, PROVISIONAL",
                                      "WDC_hashes": {str(y): g2r.sha(ROOT / "phase2a/raw/wdc_hourly" / f"COI_{y}_hour_iaga_XYZF.zip") for y in YEARS},
                                      "GFZ_hashes": {str(y): g2r.sha(ROOT / "phase2a/raw/gfz" / f"QD_days{y}.txt") for y in YEARS},
                                      "cache_sha256": g2r.sha(HERE / "G4R_sq_cache.npz"),
                                      "references_available": len(refs)})
    log(f"Sq_IQD own done: {len(refs)}/432 references available")
    verify_frozen()


def published_sq(month: int, c: str, year: int | None) -> np.ndarray:
    path = g2r.find_dat(f"COI_{c}_Sq.SD.S_m{month:02d}.dat")
    header = f"Sq.y.{year}" if year is not None else "Sq.y.all"
    curve = g2r.vector_by_header(path, header)
    if len(curve) != 24 or not np.isfinite(curve).all():
        raise RuntimeError(f"Mendeley Sq reference invalid: {g2r.rel(path)} {header}")
    return curve


def classification() -> None:
    verify_frozen()
    log("G4-R four-pipeline classification start")
    g3_rows = csv_read("G3R_structure_metrics.csv")
    own_refs = np.load(HERE / "G4R_sq_cache.npz", allow_pickle=False)
    pca = np.load(HERE / "G4R_pca_cache.npz", allow_pickle=False)
    long: list[dict] = []
    errors = []
    for idx, row in enumerate(g3_rows, 1):
        if row["status"] not in ("ELIGIBLE", "SUSPECT_DIAGNOSTIC"):
            continue
        year = None if row["year"] == "combined" else int(row["year"])
        month, c = int(row["month"]), row["component"]
        key = tid(year, month, c)
        if key not in own_refs:
            errors.append({"target": key, "error": "Own Sq_IQD reference unavailable"})
            continue
        try:
            own_ref = own_refs[key]
            pub_ref = published_sq(month, c, year)
            own_pc, own_eof = pca[key+"_ownpc"], pca[key+"_owneof"]
            pub_pc, pub_eof = pca[key+"_pubpc"], pca[key+"_pubeof"]
            refs = {"own": own_ref, "pub": pub_ref}
            surrogates = {name: random_phase_surrogates(ref) for name, ref in refs.items()}
            configurations = {"P-own": (own_pc, own_eof, "own"),
                              "P-pub": (pub_pc, pub_eof, "pub"),
                              "P-mixA": (own_pc, own_eof, "pub"),
                              "P-mixB": (pub_pc, pub_eof, "own")}
            for pipeline, (pcs, eofs, ref_name) in configurations.items():
                for subset, candidate in zip(CANDIDATES, CANDIDATE_NAMES):
                    curve = candidate_curve(pcs, eofs, subset)
                    result = classify_curve(curve, refs[ref_name], surrogates[ref_name])
                    long.append({"year": row["year"], "month": month, "component": c, "scope": row["scope"],
                                 "policy_status": row["status"], "development_seen": row["development_seen"],
                                 "february": row["february"], "pipeline": pipeline, "candidate": candidate,
                                 **result})
        except Exception as e:
            errors.append({"target": key, "error": f"{type(e).__name__}: {e}"})
            log(f"Classification {key}: {type(e).__name__}: {e}")
        if idx % 72 == 0: log(f"Classification processed {idx}/432 targets")
    fields = ["year", "month", "component", "scope", "policy_status", "development_seen", "february",
              "pipeline", "candidate", "r", "abs_r", "p", "decision", "sensitive_zone"]
    csv_write("G4R_classification_long.csv", long, fields)
    jwrite("G4R_classification_errors.json", errors)
    log(f"Classification done: {len(long)} candidate-pipeline rows, {len(errors)} unavailable/error targets")
    verify_frozen()


def run() -> None:
    g3(); sq(); classification()


if __name__ == "__main__":
    {"g3": g3, "sq": sq, "classify": classification, "run": run}[sys.argv[1]]()
