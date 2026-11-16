"""Build preregistered E2 semi-synthetic source months and case manifest."""
from __future__ import annotations

import calendar
import csv
import datetime as dt
import hashlib
import importlib.metadata
import json
from pathlib import Path

import DIFI
import numpy as np

from auto_sqpca.gaps import apply
from f3_preflight import ROOT, OUT, sha, verify_snapshot

WORK = OUT / "work/ssb_months"
CASE_FIELDS = ("case_id", "split", "station", "year", "month", "component", "alpha", "mask", "replicate",
               "amplitude_seed", "mask_seed", "cache_path", "cache_sha256", "DIFI_model", "GFZ_IQD_path", "GFZ_IQD_sha256")


def seed(*parts: object) -> int:
    return int(hashlib.sha256("|".join(map(str, (20261114, "E2", *parts))).encode()).hexdigest()[:8], 16)


def split(station: str, year: int) -> str:
    if (station == "KDU" and 2014 <= year <= 2016) or (station == "COI" and 2014 <= year <= 2015):
        return "development"
    return "holdout"


def relevant(r: dict) -> bool:
    y = int(r["year"])
    return r["eligible_E2"] == "True" and ((r["station"] == "COI" and 2014 <= y <= 2017) or
           (r["station"] in ("KDU", "GUA") and 2014 <= y <= 2018))


def truth_difi(row: dict, n: int) -> np.ndarray:
    y, m = int(row["year"]), int(row["month"])
    shift = int(row["delta_LT_hours"])
    local_start = dt.datetime(y, m, 1)
    utc = [local_start + dt.timedelta(hours=i-shift, minutes=30) for i in range(n*24)]
    lon = ((float(row["longitude_east_deg"]) + 180) % 360) - 180
    b = DIFI.getSQfield(float(row["latitude_deg"]), lon,
                        [t.year for t in utc], [t.month for t in utc], [t.day for t in utc],
                        hour=[t.hour for t in utc], minutes=[t.minute for t in utc],
                        h=0, model_name="DIFI8")
    out = np.column_stack([np.asarray(b[c], dtype=float).reshape(n, 24).mean(axis=0) for c in "XYZ"])
    out -= out.mean(axis=0, keepdims=True)
    if out.shape != (24, 3) or not np.isfinite(out).all() or np.any(np.ptp(out, axis=0) <= 0):
        raise RuntimeError(f"Invalid DIFI8 truth {row['station']} {y}-{m:02d}")
    return out


def main() -> None:
    verify_snapshot()
    if sha(OUT / "F3_E1_frozen.json") != (OUT / "F3_E1_frozen.json.sha256").read_text().split()[0]:
        raise RuntimeError("E1 frozen config SHA-256 mismatch")
    WORK.mkdir(parents=True, exist_ok=True)
    inventory = list(csv.DictReader((OUT / "F3_data_inventory.csv").open(encoding="utf-8", newline="")))
    rows = [r for r in inventory if relevant(r)]
    if len(rows) != 162:
        raise RuntimeError(f"Expected 162 E2 eligible station-months, got {len(rows)}")
    manifest = []
    month_meta = []
    for index, row in enumerate(rows, 1):
        station, year, month = row["station"], int(row["year"]), int(row["month"])
        cache = ROOT / row["matrix_cache"]
        if sha(cache) != row["matrix_cache_sha256"]:
            raise RuntimeError(f"Monthly source matrix hash mismatch: {cache}")
        raw = np.load(cache, allow_pickle=False)["XYZ_nT"]
        n = calendar.monthrange(year, month)[1]
        if raw.shape != (24, n, 3):
            raise RuntimeError(f"Unexpected source shape: {station} {year}-{month:02d} {raw.shape}")
        filled = np.empty_like(raw)
        em_info = []
        for c in range(3):
            v, keep, info = apply(raw[:, :, c], "M-EM")
            if not keep.all() or v.shape != (24, n) or not np.isfinite(v).all():
                raise RuntimeError(f"SSB month loses days under frozen M-EM: {station} {year}-{month:02d} {'XYZ'[c]}")
            filled[:, :, c] = v
            em_info.append(info)
        centered = filled - filled.mean(axis=0, keepdims=True)
        residual = centered - centered.mean(axis=1, keepdims=True)
        if np.max(np.abs(residual.mean(axis=1))) > 1e-10:
            raise RuntimeError(f"SSB residual monthly mean nonzero: {station} {year}-{month:02d}")
        truth = truth_difi(row, n)
        gfz = (OUT / "raw/gfz/QD_days2018.txt") if year == 2018 else (ROOT / "phase2a/raw/gfz" / f"QD_days{year}.txt")
        gfz_hash = sha(gfz)
        out = WORK / f"{station}_{year}_{month:02d}.npz"
        if out.exists():
            raise RuntimeError(f"SSB cache already exists, refusing overwrite: {out}")
        np.savez_compressed(out, residual_nT=residual, DIFI8_sq_true_nT=truth, filled_observation_nT=filled)
        cache_rel = out.relative_to(ROOT).as_posix()
        digest = sha(out)
        month_meta.append({"station": station, "year": year, "month": month, "split": split(station, year),
                           "cache_path": cache_rel, "cache_sha256": digest,
                           "source_matrix_sha256": row["matrix_cache_sha256"],
                           "M_EM_iterations_XYZ": [x["iterations"] for x in em_info],
                           "M_EM_final_change_nT_XYZ": [x["final_change_nT"] for x in em_info],
                           "DIFI_amplitude_XYZ_nT": np.ptp(truth, axis=0).tolist(),
                           "GFZ_IQD_sha256": gfz_hash})
        for component in "XYZ":
            for alpha in (.5, 1, 2):
                for mask in ("NONE", "MCAR20"):
                    for rep in range(3):
                        ident = f"{station}_{year}_{month:02d}_{component}_a{alpha:g}_{mask}_r{rep}"
                        manifest.append({"case_id": ident, "split": split(station, year), "station": station,
                                         "year": year, "month": month, "component": component, "alpha": alpha,
                                         "mask": mask, "replicate": rep,
                                         "amplitude_seed": seed(ident, "amplitude"), "mask_seed": seed(ident, "mask"),
                                         "cache_path": cache_rel, "cache_sha256": digest, "DIFI_model": "DIFI8",
                                         "GFZ_IQD_path": gfz.relative_to(ROOT).as_posix(), "GFZ_IQD_sha256": gfz_hash})
        if index % 12 == 0 or index == len(rows):
            print(f"SSB source months {index}/{len(rows)}", flush=True)
    with (OUT / "F3_ssb_manifest.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CASE_FIELDS)
        writer.writeheader(); writer.writerows(manifest)
    (OUT / "F3_ssb_month_provenance.json").write_text(json.dumps({
        "model": "DIFI8", "pydifi_version": importlib.metadata.version("pyDIFI"),
        "DIFI8_coeff_sha256": sha(Path(DIFI.__file__).parent / "coefs/DIFI8.DBL"),
        "f107_coeff_sha256": sha(Path(DIFI.__file__).parent / "coefs/f107.DBL"),
        "height_km_WGS84": 0, "sample_time": "UTC HH:30 at each local-calendar hour after integer longitude/15 shift",
        "month_truth": "daily DIFI8 field averaged by local hour across all calendar days, then 24-hour mean removed",
        "residual": "frozen M-EM filled observation; V1 daily mean removed; monthly mean curve removed",
        "source_months": len(rows), "cases": len(manifest), "month_rows": month_meta,
        "manifest_sha256": sha(OUT / "F3_ssb_manifest.csv")}, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"SSB manifest: {len(rows)} source months, {len(manifest)} cases")
    verify_snapshot()


if __name__ == "__main__":
    main()
