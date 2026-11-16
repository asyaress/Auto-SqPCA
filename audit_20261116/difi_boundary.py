"""Sensitivity of DIFI-8 local-month curves to UTC samples before 2014-01-01."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

import DIFI
import numpy as np

REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO.parents[1]
OUT = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f: return list(csv.DictReader(f))


def corr(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.corrcoef(a, b)[0, 1])


def main() -> None:
    prov = json.loads((REPO / "phase3/F3_ssb_month_provenance.json").read_text(encoding="utf-8"))
    model_dir = Path(DIFI.__file__).parent / "coefs"
    assert sha(model_dir / "DIFI8.DBL") == prov["DIFI8_coeff_sha256"]
    assert sha(model_dir / "f107.DBL") == prov["f107_coeff_sha256"]
    inventory = rows(REPO / "phase3/F3_data_inventory.csv")
    e3 = rows(REPO / "phase3/F3_E3_cases.csv")
    output = []
    for station in ("GUA", "KDU"):
        row = next(r for r in inventory if r["station"] == station and r["year"] == "2014" and r["month"] == "1")
        local_start = dt.datetime(2014, 1, 1)
        shift = int(row["delta_LT_hours"])
        utc = [local_start + dt.timedelta(hours=i-shift, minutes=30) for i in range(31*24)]
        valid = np.array([t >= local_start for t in utc]).reshape(31, 24)
        n_outside = int((~valid).sum())
        lon = ((float(row["longitude_east_deg"]) + 180) % 360) - 180
        b = DIFI.getSQfield(float(row["latitude_deg"]), lon,
            [t.year for t in utc], [t.month for t in utc], [t.day for t in utc],
            hour=[t.hour for t in utc], minutes=[t.minute for t in utc], h=0, model_name="DIFI8")
        all_curve = np.column_stack([np.asarray(b[c],dtype=float).reshape(31,24).mean(axis=0) for c in "XYZ"])
        all_curve -= all_curve.mean(axis=0)
        sensitivity = np.column_stack([np.array([np.mean(np.asarray(b[c],dtype=float).reshape(31,24)[valid[:,h],h])
            for h in range(24)]) for c in "XYZ"])
        sensitivity -= sensitivity.mean(axis=0)
        cache = PROJECT / "phase3/work/ssb_months" / f"{station}_2014_01.npz"
        archived = np.load(cache, allow_pickle=False)["DIFI8_sq_true_nT"]
        assert np.max(np.abs(all_curve-archived)) < 1e-10
        for ci, comp in enumerate("XYZ"):
            old, new = all_curve[:,ci], sensitivity[:,ci]
            e3_case = next(r for r in e3 if r["station"] == station and r["year"] == "2014"
                           and r["month"] == "1" and r["component"] == comp)
            auto_old_r = auto_new_r = ""
            if e3_case["curve_cache_path"]:
                z = np.load(PROJECT / e3_case["curve_cache_path"], allow_pickle=False)
                auto_curve = z["AUTO"]
                auto_old_r, auto_new_r = corr(auto_curve, old), corr(auto_curve, new)
                assert np.max(np.abs(z["DIFI8"]-old)) < 1e-10
                if e3_case["abstained"] == "False":
                    assert abs(auto_old_r-float(e3_case["r_AUTO_DIFI"])) < 1e-10
            output.append({"station": station, "year": 2014, "month": 1, "component": comp,
                "out_of_range_utc_samples": n_outside, "max_abs_target_delta_nT": float(np.max(np.abs(new-old))),
                "relative_target_l2_delta": float(np.linalg.norm(new-old)/np.linalg.norm(old)),
                "target_correlation": corr(old,new), "old_amplitude_nT": float(np.ptp(old)),
                "new_amplitude_nT": float(np.ptp(new)), "E3_abstained": e3_case["abstained"], "E3_auto_old_r": auto_old_r,
                "E3_auto_new_r": auto_new_r})
    with (OUT / "difi_boundary_sensitivity.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(output[0]));w.writeheader();w.writerows(output)
    (OUT / "difi_boundary_summary.json").write_text(json.dumps({"label":"POST_HOC_SENSITIVITY",
        "model":"DIFI8", "outside_samples_total":19,"rows":output},indent=2),encoding="utf-8")
    print(json.dumps(output,indent=2))


if __name__ == "__main__": main()
