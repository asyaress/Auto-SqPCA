"""E3 primary/exploratory station summaries and four example bootstrap bands."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict

import numpy as np

from auto_sqpca import bootstrap, gaps, pca, selection
from f3b_e2_cases import quiet_days
from f3_preflight import ROOT, OUT, sha, verify_snapshot


def finite_median(rows: list[dict], field: str) -> float | None:
    a = np.asarray([float(r[field]) for r in rows], dtype=float)
    a = a[np.isfinite(a)]
    return float(np.median(a)) if len(a) else None


def main() -> None:
    verify_snapshot()
    path = OUT / "F3_E3_cases.csv"
    provenance = json.loads((OUT / "F3_E3_provenance.json").read_text(encoding="utf-8"))
    if sha(path) != provenance["E3_cases_sha256"]:
        raise RuntimeError("E3 cases SHA-256 mismatch")
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    if len(rows) != provenance["component_cases"]:
        raise RuntimeError("E3 cases count mismatch")
    groups = defaultdict(list)
    for r in rows:
        groups[(r["scope"], r["station"], r["component"])].append(r)
    summary = []
    for (scope, station, component), members in sorted(groups.items()):
        accepted = [r for r in members if r["status"] == "OK" and r["abstained"] == "False"]
        reason_counts = Counter(a for r in members for a in r["abstain_reasons"].split(";") if a)
        status_counts = Counter(r["status"] for r in members)
        summary.append({"scope": scope, "station": station, "component": component,
                        "dipole_geomag_lat_median_deg": finite_median(members, "dipole_geomag_lat_deg"),
                        "months": len(members), "accepted": len(accepted), "abstain_fraction": 1 - len(accepted)/len(members),
                        "A1_count": reason_counts["A1"], "A2_count": reason_counts["A2"],
                        "A3_count": reason_counts["A3"], "A4_count": reason_counts["A4"],
                        "NO_MATRIX_OR_DROPPED_DAY": status_counts["NO_MATRIX_OR_DROPPED_DAY"],
                        "ERROR": status_counts["ERROR"],
                        "median_r_AUTO_DIFI_accepted": finite_median(accepted, "r_AUTO_DIFI"),
                        "median_r_ASAL_DIFI_paired": finite_median(accepted, "r_ASAL_DIFI"),
                        "median_AUTO_minus_ASAL_DIFI_r_paired": finite_median(accepted, "AUTO_minus_ASAL_DIFI_r"),
                        "median_AUTO_DIFI_amplitude_ratio": finite_median(accepted, "AUTO_DIFI_amplitude_ratio"),
                        "median_r_AUTO_IQD_nonindependent": finite_median(accepted, "r_AUTO_IQD_nonindependent"),
                        "median_relative_bootstrap_width": finite_median(accepted, "relative_width")})
    fields = list(summary[0])
    with (OUT / "F3_E3_station_summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(summary)
    # Four representative X curves: accepted month nearest June 2017, with frozen pipeline.
    examples = {}
    inventory = list(csv.DictReader((OUT / "F3_data_inventory.csv").open(encoding="utf-8", newline="")))
    lookup = {(r["station"], r["year"], r["month"]): r for r in inventory}
    for station in ("COI", "KDU", "PLR", "TUN"):
        eligible = [r for r in rows if r["scope"] == "E3_primary" and r["station"] == station and
                    r["component"] == "X" and r["status"] == "OK" and r["abstained"] == "False"]
        if not eligible:
            examples[station] = {"status": "NO_ACCEPTED_X_MONTH"}
            continue
        chosen = min(eligible, key=lambda r: (abs(int(r["month"]) - 6), abs(int(r["year"]) - 2017), int(r["year"]), int(r["month"])))
        inv = lookup[(station, chosen["year"], chosen["month"])]
        raw = np.load(ROOT / inv["matrix_cache"], allow_pickle=False)["XYZ_nT"][:, :, 0]
        filled, keep, _ = gaps.apply(raw, "M-EM")
        if not keep.all():
            raise RuntimeError(f"Accepted E3 example dropped days: {station}")
        year = int(chosen["year"])
        gfz = (OUT / "raw/gfz/QD_days2018.txt") if year == 2018 else (ROOT / "phase2a/raw/gfz" / f"QD_days{year}.txt")
        days = quiet_days({"GFZ_IQD_path": gfz.relative_to(ROOT).as_posix(), "GFZ_IQD_sha256": sha(gfz),
                           "year": year, "month": int(chosen["month"])})
        ref = selection.sq_iqd(filled, days)
        selected = selection.choose(pca.decompose_v1(filled), ref)["selected"]
        if selected != chosen["AUTO_candidate"]:
            raise RuntimeError(f"Example candidate differs from E3 case: {station}")
        band = bootstrap.summarize(filled, ref, selected, seed=20261114)
        curve = np.load(ROOT / chosen["curve_cache_path"], allow_pickle=False)
        examples[station] = {"status": "OK", "year": year, "month": int(chosen["month"]),
                             "candidate": selected, "AUTO": curve["AUTO"].tolist(),
                             "ASAL": curve["ASAL"].tolist(), "DIFI8": curve["DIFI8"].tolist(),
                             "band_low": band["band_low"].tolist(), "band_high": band["band_high"].tolist(),
                             "bootstrap_stability": band["stability"],
                             "bootstrap_relative_width": band["relative_width"],
                             "curve_cache_sha256": chosen["curve_cache_sha256"]}
    (OUT / "F3_E3_examples.json").write_text(json.dumps(examples, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (OUT / "F3_E3_summary_validation.json").write_text(json.dumps({
        "E3_cases_sha256": sha(path), "summary_sha256": sha(OUT / "F3_E3_station_summary.csv"),
        "examples_sha256": sha(OUT / "F3_E3_examples.json"), "station_component_rows": len(summary),
        "primary_station_months": sum(r["scope"] == "E3_primary" for r in rows) // 3,
        "exploratory_station_months": sum(r["scope"] == "E3b_exploratory" for r in rows) // 3,
        "status_counts": dict(Counter(r["status"] for r in rows)),
        "example_status": {s: v["status"] for s, v in examples.items()}}, indent=2) + "\n", encoding="utf-8")
    print(f"E3 summary: {len(summary)} station-component rows, {len(rows)} cases")
    verify_snapshot()


if __name__ == "__main__":
    main()
