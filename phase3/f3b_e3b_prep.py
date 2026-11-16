"""Prepare optional E3b hourly matrices from frozen Phase 1 minute archives."""
from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path

import numpy as np

from auto_sqpca.io import minute_hourly_zip
from auto_sqpca.localtime import delta_hours, month_matrix
from f3_preflight import ROOT, OUT, sha, verify_snapshot

STATIONS = ("HUA", "TTB", "MBO")
YEARS = tuple(range(2014, 2019))
WORK = OUT / "work/e3b_months"


def main() -> None:
    verify_snapshot()
    freeze = json.loads((ROOT / "audit_final/dataset_freeze.json").read_text(encoding="utf-8"))
    inputs = {(r["station"], r["year"]): r for r in freeze["inputs"]}
    phase1 = {(r["station"], int(r["year"])): r for r in csv.DictReader(
        (ROOT / "audit_final/station_month_90_days.csv").open(encoding="utf-8", newline=""))}
    WORK.mkdir(parents=True, exist_ok=True)
    output = []
    for station in STATIONS:
        annual = []
        for year in YEARS:
            record = inputs[(station, year)]
            if record["status"] != "OK":
                raise RuntimeError(f"E3b required Phase 1 archive unavailable: {station} {year}")
            arc = record["archive"]
            path = ROOT / arc["path"]
            if sha(path) != arc["sha256"]:
                raise RuntimeError(f"E3b Phase 1 archive SHA-256 mismatch: {path}")
            loaded = minute_hourly_zip(path, station, year)
            annual.append(loaded)
            print(f"E3b {station} {year}: minute days {loaded['minute_days_present']}", flush=True)
        full = np.concatenate([r["values"] for r in annual])
        utc_start = dt.datetime(YEARS[0], 1, 1)
        for year, loaded in zip(YEARS, annual):
            qc = phase1[(station, year)]
            eligible_months = [m for m in range(1, 13) if float(qc[f"{m:02d}"] or 0) >= 15]
            if len(eligible_months) < 6:
                raise RuntimeError(f"E3b station-year fails Phase 1 >=6 month condition: {station} {year}")
            arc = inputs[(station, year)]["archive"]
            for month in eligible_months:
                matrix = month_matrix(full, utc_start, loaded["longitude"], year, month)
                valid = np.isfinite(matrix).all(axis=2)
                out = WORK / f"{station}_{year}_{month:02d}.npz"
                if out.exists():
                    raise RuntimeError(f"E3b cache already exists: {out}")
                np.savez_compressed(out, XYZ_nT=matrix)
                output.append({"station": station, "year": year, "month": month,
                               "latitude_deg": loaded["latitude"], "longitude_east_deg": loaded["longitude"],
                               "delta_LT_hours": delta_hours(loaded["longitude"]),
                               "phase1_qualifying_days": qc[f"{month:02d}"],
                               "valid_xyz_hours": int(valid.sum()), "total_local_hours": int(valid.size),
                               "valid_xyz_fraction": float(valid.mean()),
                               "source_path": arc["path"], "source_sha256": arc["sha256"],
                               "matrix_cache": out.relative_to(ROOT).as_posix(), "matrix_cache_sha256": sha(out),
                               "scope": "E3b_exploratory"})
    fields = list(output[0])
    with (OUT / "F3_E3b_inventory.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(output)
    (OUT / "F3_E3b_provenance.json").write_text(json.dumps({"Phase1_freeze_sha256": sha(ROOT / "audit_final/dataset_freeze.json"),
        "Phase1_monthly_QC_sha256": sha(ROOT / "audit_final/station_month_90_days.csv"),
        "definition": "Only station-years with >=6 Phase 1 months containing >=15 days of >=90% valid XYZ minutes; strict 60 valid minutes/hour, Rule A truncation to 0.1 nT; all eligible months retained, including low hourly coverage for A3 abstention",
        "station_months": len(output), "inventory_sha256": sha(OUT / "F3_E3b_inventory.csv")}, indent=2) + "\n", encoding="utf-8")
    print(f"E3b prepared {len(output)} station-months")
    verify_snapshot()


if __name__ == "__main__":
    main()
