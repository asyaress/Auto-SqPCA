"""Frozen Auto-SqPCA transfer evaluation on real E3 and exploratory E3b months."""
from __future__ import annotations

import csv
import datetime as dt
import importlib.metadata
import json
import math
import os
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import ppigrf

from auto_sqpca import candidates, gaps, metrics, pca, selection
from classification_core import random_phase_surrogates
from f3b_e2_cases import bootstrap_fast, quiet_days, seed
from f3b_e2_eval import assess, asfloat
from f3b_ssb import truth_difi
from f3_preflight import ROOT, OUT, sha, verify_snapshot

CURVES = OUT / "work/E3_curves"
FIELDS = ("scope", "station", "year", "month", "component", "geographic_lat_deg", "dipole_geomag_lat_deg",
          "valid_observed_fraction", "status", "error_original", "AUTO_candidate", "ASAL_candidate",
          "abstained", "abstain_reasons", "stability", "relative_width", "bootstrap_successful",
          "r_AUTO_DIFI", "r_ASAL_DIFI", "r_AUTO_IQD_nonindependent",
          "AUTO_DIFI_amplitude_ratio", "ASAL_DIFI_amplitude_ratio", "AUTO_minus_ASAL_DIFI_r",
          "DIFI_amplitude_nT", "M_EM_iterations", "M_EM_final_change_nT", "curve_cache_path", "curve_cache_sha256")


def dipole_axis() -> tuple[np.ndarray, dict]:
    g, h = ppigrf.ppigrf.read_shc()
    date = "2015-01-01"
    coefficients = {"g10": float(g.loc[date, (1, 0)]), "g11": float(g.loc[date, (1, 1)]),
                    "h11": float(h.loc[date, (1, 1)])}
    axis = np.array([-coefficients["g11"], -coefficients["h11"], -coefficients["g10"]])
    axis /= np.linalg.norm(axis)
    return axis, coefficients


def dipole_lat(lat: float, lon: float, axis: np.ndarray) -> float:
    # Centered-dipole latitude uses a geocentric radial direction. Observatory
    # metadata latitude is geodetic WGS84; convert it at h=0 km first.
    geodetic, lo = np.deg2rad([lat, lon])
    wgs84_e2 = 0.00669437999014
    la = np.arctan((1 - wgs84_e2) * np.tan(geodetic))
    radial = np.array([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])
    return float(np.rad2deg(np.arcsin(np.clip(radial @ axis, -1, 1))))


def corr(a: np.ndarray, b: np.ndarray) -> float:
    if not np.isfinite(a).all() or not np.isfinite(b).all() or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def e3_rows() -> list[dict]:
    inv = list(csv.DictReader((OUT / "F3_data_inventory.csv").open(encoding="utf-8", newline="")))
    qc = {(r["station"], int(r["year"])): r for r in csv.DictReader(
        (ROOT / "audit_final/station_month_90_days.csv").open(encoding="utf-8", newline=""))}
    rows = []
    for r in inv:
        s, y, m = r["station"], int(r["year"]), int(r["month"])
        if (s == "COI" and 2014 <= y <= 2017) or (s in ("KDU", "GUA") and 2014 <= y <= 2018):
            rows.append({**r, "scope": "E3_primary"})
        elif s in ("PLR", "TUN") and y == 2017 and float(qc[(s, y)][f"{m:02d}"] or 0) >= 15:
            rows.append({**r, "scope": "E3_primary"})
    e3b = list(csv.DictReader((OUT / "F3_E3b_inventory.csv").open(encoding="utf-8", newline="")))
    rows.extend(e3b)
    if len([r for r in rows if r["scope"] == "E3_primary"]) != 190:
        raise RuntimeError("E3 primary station-month count changed")
    return rows


def process_month(row: dict, axis: np.ndarray, theta: tuple[float, float, float]) -> list[dict]:
    path = ROOT / row["matrix_cache"]
    if sha(path) != row["matrix_cache_sha256"]:
        raise RuntimeError(f"E3 monthly matrix hash mismatch: {path}")
    matrix = np.load(path, allow_pickle=False)["XYZ_nT"]
    station, year, month = row["station"], int(row["year"]), int(row["month"])
    lat, lon = float(row["latitude_deg"]), float(row["longitude_east_deg"])
    geomag_lat = dipole_lat(lat, lon, axis)
    gfz_path = (OUT / "raw/gfz/QD_days2018.txt") if year == 2018 else (ROOT / "phase2a/raw/gfz" / f"QD_days{year}.txt")
    gfz_record = {"GFZ_IQD_path": gfz_path.relative_to(ROOT).as_posix(), "GFZ_IQD_sha256": sha(gfz_path),
                  "year": year, "month": month}
    days = quiet_days(gfz_record)
    difi = truth_difi(row, matrix.shape[1])
    out = []
    for ci, component in enumerate("XYZ"):
        observed = float(np.isfinite(matrix[:, :, ci]).mean())
        base = {"scope": row["scope"], "station": station, "year": year, "month": month,
                "component": component, "geographic_lat_deg": lat, "dipole_geomag_lat_deg": geomag_lat,
                "valid_observed_fraction": observed, "status": "OK", "error_original": "",
                "AUTO_candidate": "", "ASAL_candidate": "", "abstained": True, "abstain_reasons": "A1",
                "stability": float("nan"), "relative_width": float("inf"), "bootstrap_successful": 0,
                "r_AUTO_DIFI": float("nan"), "r_ASAL_DIFI": float("nan"),
                "r_AUTO_IQD_nonindependent": float("nan"), "AUTO_DIFI_amplitude_ratio": float("nan"),
                "ASAL_DIFI_amplitude_ratio": float("nan"), "AUTO_minus_ASAL_DIFI_r": float("nan"),
                "DIFI_amplitude_nT": float(np.ptp(difi[:, ci])), "M_EM_iterations": 0,
                "M_EM_final_change_nT": 0.0, "curve_cache_path": "", "curve_cache_sha256": ""}
        try:
            filled, keep, info = gaps.apply(matrix[:, :, ci], "M-EM")
            base["M_EM_iterations"] = info["iterations"]
            base["M_EM_final_change_nT"] = info["final_change_nT"]
            if not keep.all() or filled.shape[1] < 3 or not np.isfinite(filled).all():
                base["status"] = "NO_MATRIX_OR_DROPPED_DAY"
                base["error_original"] = "M-EM removed at least one local day or produced <3/nonfinite columns; fixed GFZ day indices cannot be retained"
                base["abstain_reasons"] = "A1" + (";A3" if observed < theta[1] else "")
                out.append(base)
                continue
            reference = selection.sq_iqd(filled, days)
            surrogates = random_phase_surrogates(reference)
            result = pca.decompose_v1(filled)
            curves = candidates.curves(result)
            abs_r = {name: abs(corr(curve, reference)) for name, curve in curves.items()}
            if any(not np.isfinite(x) for x in abs_r.values()):
                raise RuntimeError("E3 candidate-IQD correlation undefined")
            asal = max(candidates.NAMES[:3], key=lambda name: abs_r[name])
            chosen = selection.choose(result, reference, surrogates)
            base["ASAL_candidate"] = asal
            base["AUTO_candidate"] = chosen["selected"] or ""
            boot = bootstrap_fast(filled, reference, chosen["selected"], surrogates,
                                  seed("E3", station, year, month, component, "bootstrap"))
            base["stability"] = boot["stability"]
            base["relative_width"] = boot["relative_width"]
            base["bootstrap_successful"] = boot["successful"]
            frozen_row = {"AUTO_A1": str(chosen["selected"] is None), "AUTO_candidate": chosen["selected"] or "",
                          "stability": boot["stability"], "observed_fraction": observed,
                          "relative_width": boot["relative_width"], "status": "OK"}
            why = assess(frozen_row, *theta)
            base["abstained"] = bool(why)
            base["abstain_reasons"] = ";".join(why)
            truth = difi[:, ci]
            base["r_ASAL_DIFI"] = corr(curves[asal], truth)
            base["ASAL_DIFI_amplitude_ratio"] = float(np.ptp(curves[asal]) / np.ptp(truth))
            if chosen["curve"] is not None:
                base["r_AUTO_IQD_nonindependent"] = corr(chosen["curve"], reference)
                if not why:
                    base["r_AUTO_DIFI"] = corr(chosen["curve"], truth)
                    base["AUTO_DIFI_amplitude_ratio"] = float(np.ptp(chosen["curve"]) / np.ptp(truth))
                    base["AUTO_minus_ASAL_DIFI_r"] = base["r_AUTO_DIFI"] - base["r_ASAL_DIFI"]
            curve_path = CURVES / f"{station}_{year}_{month:02d}_{component}.npz"
            np.savez_compressed(curve_path, ASAL=curves[asal], AUTO=chosen["curve"] if chosen["curve"] is not None else np.full(24, np.nan),
                                DIFI8=truth, IQD=reference)
            base["curve_cache_path"] = curve_path.relative_to(ROOT).as_posix()
            base["curve_cache_sha256"] = sha(curve_path)
        except Exception as e:
            base["status"] = "ERROR"
            base["error_original"] = f"{type(e).__name__}: {e}"
            base["abstained"] = True
            base["abstain_reasons"] = "A1" + (";A3" if observed < theta[1] else "")
        out.append(base)
    return out


def main() -> None:
    verify_snapshot()
    config_path = OUT / "F3_E2_frozen.json"
    if sha(config_path) != (OUT / "F3_E2_frozen.json.sha256").read_text().split()[0]:
        raise RuntimeError("E2 frozen config hash mismatch")
    frozen = json.loads(config_path.read_text(encoding="utf-8"))
    if frozen["E1_method"] != "M-EM" or frozen["theta_d"] != .90:
        raise RuntimeError("E3 pipeline differs from E1/E2 freeze")
    theta = (float(frozen["theta_s"]), float(frozen["theta_d"]), asfloat(frozen["theta_w"]))
    axis, coeff = dipole_axis()
    CURVES.mkdir(parents=True, exist_ok=True)
    rows = e3_rows()
    out_path = OUT / "F3_E3_cases.csv"
    if out_path.exists():
        raise RuntimeError("E3 cases already exist; refusing rerun")
    print(f"E3: {len(rows)} station-months, theta={theta}", flush=True)
    n = 0
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        with ProcessPoolExecutor(max_workers=int(os.environ.get("F3_WORKERS", "8"))) as pool:
            futures = {pool.submit(process_month, row, axis, theta): row for row in rows}
            for index, future in enumerate(as_completed(futures), 1):
                row = futures[future]
                try:
                    cases = future.result()
                except Exception as e:
                    raise RuntimeError(f"E3 worker {row['station']} {row['year']}-{row['month']}: {type(e).__name__}: {e}") from e
                writer.writerows(cases); f.flush(); n += len(cases)
                if index % 20 == 0 or index == len(rows):
                    print(f"E3 completed {index}/{len(rows)} months, {n} component cases", flush=True)
    provenance = {"E2_frozen_sha256": sha(config_path), "E3_cases_sha256": sha(out_path),
                  "station_months": len(rows), "component_cases": n,
                  "DIFI_model": "DIFI8", "pydifi_version": importlib.metadata.version("pyDIFI"),
                  "ppigrf_version": importlib.metadata.version("ppigrf"), "IGRF_coeff_model": "IGRF13",
                  "IGRF13_coeff_sha256": sha(Path(ppigrf.__file__).parent / "IGRF13.shc"),
                  "dipole_epoch": 2015, "dipole_coefficients_nT": coeff,
                  "dipole_north_axis_unit_xyz": axis.tolist(),
                  "dipole_latitude_definition": "WGS84 geodetic latitude to geocentric at h=0 km; arcsin(r_geocentric unit dot normalized [-g11,-h11,-g10]); centered dipole",
                  "IQD_evaluation_note": "r(AUTO,Sq_IQD) is secondary and not independent of selection",
                  "scope_note": "E3b is exploratory; Phase 1 minute Rule A used for eligible station-years/months"}
    (OUT / "F3_E3_provenance.json").write_text(json.dumps(provenance, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    verify_snapshot()


if __name__ == "__main__":
    main()
