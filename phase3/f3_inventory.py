"""F3A local-time monthly inventory and deterministic TND 2017 masks."""
from __future__ import annotations
import csv
import datetime as dt
import json
from pathlib import Path
import numpy as np

from auto_sqpca.io import load_hourly_zip, minute_hourly_zip
from auto_sqpca.localtime import delta_hours, month_matrix
from f3_preflight import ROOT, OUT, sha, verify_snapshot

WORK = OUT / "work/months"


def maximum_missing_run(valid: np.ndarray) -> int:
    missing = ~valid.reshape(-1)
    if not missing.any(): return 0
    boundaries = np.diff(np.r_[0, missing.astype(int), 0])
    return int(max(np.flatnonzero(boundaries == -1) - np.flatnonzero(boundaries == 1)))


def sources() -> list[dict]:
    return json.loads((OUT / "F3_data_sources.json").read_text(encoding="utf-8"))


def source_path(item: dict) -> Path:
    if item["station"] == "COI": return ROOT / item["path"]
    if item["status"].startswith("WDC_HOURLY"):
        return OUT / "raw/hourly" / f"{item['station']}_{item['year']}_hour_iaga_XYZF.zip"
    if item["status"] == "PHASE1_MINUTE_RULE_A": return ROOT / item["fallback_path"]
    raise RuntimeError(f"No usable station-year source: {item}")


def load_source(item: dict) -> dict:
    p = source_path(item)
    expected = item["sha256"] if "sha256" in item else item["fallback_sha256"]
    if sha(p) != expected: raise RuntimeError(f"Source hash mismatch: {p}")
    if item["status"] == "PHASE1_MINUTE_RULE_A": return minute_hourly_zip(p, item["station"], item["year"])
    return load_hourly_zip(p, item["station"], item["year"])


def main() -> None:
    verify_snapshot()
    WORK.mkdir(parents=True, exist_ok=True)
    grouped = {}
    for item in sources(): grouped.setdefault(item["station"], []).append(item)
    output = []
    for station, items in sorted(grouped.items()):
        items.sort(key=lambda x:x["year"])
        good = [x for x in items if x["status"] in ("WDC_HOURLY","WDC_HOURLY_REUSED","G0_WDC_HOURLY_REUSED","PHASE1_MINUTE_RULE_A")]
        if not good: continue
        loaded = [load_source(x) for x in good]
        latitudes = [x["latitude"] for x in loaded]
        longitudes = [x["longitude"] for x in loaded]
        if len({delta_hours(lon) for lon in longitudes}) != 1:
            raise RuntimeError(f"Station integer LT shift changed across years: {station}, {longitudes}")
        first, last = good[0]["year"], good[-1]["year"]
        expected_years = list(range(first,last+1))
        if [x["year"] for x in good] != expected_years:
            raise RuntimeError(f"Station-year gap in {station}: {[x['year'] for x in good]}")
        full = np.concatenate([x["values"] for x in loaded])
        utc_start = dt.datetime(first,1,1)
        for year in expected_years:
            year_loaded = next(x for x in loaded if x["year"] == year)
            for month in range(1,13):
                matrix = month_matrix(full,utc_start,year_loaded["longitude"],year,month)
                valid = np.isfinite(matrix).all(axis=2)
                frac = float(valid.mean())
                maxgap = maximum_missing_run(valid)
                filename = f"{station}_{year}_{month:02d}.npz"
                np.savez_compressed(WORK / filename, XYZ_nT=matrix)
                output.append({"station":station,"year":year,"month":month,
                               "latitude_deg":year_loaded["latitude"], "longitude_east_deg":year_loaded["longitude"],
                               "delta_LT_hours":delta_hours(year_loaded["longitude"]),
                               "total_local_hours":valid.size, "valid_xyz_hours":int(valid.sum()),
                               "valid_xyz_fraction":frac,"max_missing_gap_hours":maxgap,
                               "eligible_E1": frac >= 0.99 and maxgap <= 2,
                               "eligible_E2": frac >= 0.95,
                               "source_station_year": next(x["status"] for x in good if x["year"]==year),
                               "source_path":str(source_path(next(x for x in good if x["year"]==year)).relative_to(ROOT).as_posix()),
                               "source_sha256":next(x.get("sha256",x.get("fallback_sha256")) for x in good if x["year"]==year),
                               "matrix_cache":f"phase3/work/months/{filename}",
                               "matrix_cache_sha256":sha(WORK/filename)})
        print(f"{station}: {len(expected_years)*12} local months inventoried",flush=True)
    fields=list(output[0])
    with (OUT / "F3_data_inventory.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(output)
    tnd_source = ROOT / "audit_sq_wdc/cache/TND_2017_minute_iaga_XYZF.zip"
    tnd = minute_hourly_zip(tnd_source,"TND",2017,values=False)
    masks = {}
    for month in range(1,13):
        utc_mask = tnd["strict_xyz_complete"].astype(float)[:,None]
        local_mask = month_matrix(utc_mask,dt.datetime(2017,1,1),tnd["longitude"],2017,month)[:,:,0]
        masks[f"m{month:02d}"] = np.isfinite(local_mask) & (local_mask == 1)
    mask_path = OUT / "work/TND_2017_hourly_masks.npz"
    np.savez_compressed(mask_path,**masks)
    (OUT / "F3_TND_provenance.json").write_text(json.dumps({"source":"audit_sq_wdc/cache/TND_2017_minute_iaga_XYZF.zip",
       "source_sha256":sha(tnd_source),"mask_cache_sha256":sha(mask_path),
       "definition":"hour observed iff all 60 minute timestamps and X/Y/Z values valid; integer LT shift from TND longitude; align target by flattened local day-hour index; cycle from start",
       "longitude_east_deg":tnd["longitude"],"delta_LT_hours":delta_hours(tnd["longitude"]),
       "mask_valid_hours":{k:int(v.sum()) for k,v in masks.items()},
       "mask_total_hours":{k:int(v.size) for k,v in masks.items()}},indent=2)+"\n",encoding="utf-8")
    verify_snapshot()
    print(f"Inventory complete: {len(output)} station-months, E1 eligible {sum(r['eligible_E1'] for r in output)}, E2 eligible {sum(r['eligible_E2'] for r in output)}")


if __name__ == "__main__":
    main()
