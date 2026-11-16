"""Audited geodetic-to-geocentric correction of E3 dipole latitude only."""
from __future__ import annotations

import csv
import datetime as dt
import json
import shutil

from f3b_e3 import dipole_axis, dipole_lat
from f3_preflight import OUT, sha, verify_snapshot


def main() -> None:
    verify_snapshot()
    source = OUT / "F3_E3_cases.csv"
    provenance_path = OUT / "F3_E3_provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if sha(source) != provenance["E3_cases_sha256"]:
        raise RuntimeError("E3 original cases hash mismatch")
    backup = OUT / "work/E3_cases_before_geocentric_lat_fix.csv"
    if backup.exists():
        raise RuntimeError("E3 original case backup already exists")
    shutil.copy2(source, backup)
    original_hash = sha(backup)
    axis, _ = dipole_axis()
    with source.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    longitude = {}
    for filename in ("F3_data_inventory.csv", "F3_E3b_inventory.csv"):
        with (OUT / filename).open(encoding="utf-8", newline="") as f:
            for item in csv.DictReader(f):
                longitude[(item["station"], item["year"], item["month"])] = float(item["longitude_east_deg"])
    differences = []
    for row in rows:
        old = float(row["dipole_geomag_lat_deg"])
        key = (row["station"], row["year"], str(int(row["month"])))
        new = dipole_lat(float(row["geographic_lat_deg"]), longitude[key], axis)
        row["dipole_geomag_lat_deg"] = str(new)
        differences.append(abs(new-old))
    temp = OUT / "work/E3_cases_geocentric_lat_corrected.csv"
    with temp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    with backup.open(encoding="utf-8", newline="") as f:
        before = list(csv.DictReader(f))
    if len(before) != len(rows) or any(
        any(a[field] != b[field] for field in fields if field != "dipole_geomag_lat_deg")
        for a, b in zip(before, rows)):
        raise RuntimeError("E3 latitude correction altered nonlatitude case fields")
    import os
    os.replace(temp, source)
    provenance.update({"original_E3_cases_sha256_before_geocentric_lat_fix": original_hash,
                       "E3_cases_sha256": sha(source),
                       "dipole_latitude_definition": "WGS84 geodetic latitude converted to geocentric radial latitude at h=0 km, then centered IGRF-13 dipole",
                       "latitude_correction_max_abs_deg": max(differences),
                       "latitude_correction_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                       "latitude_correction_script_sha256": sha(OUT / "f3b_e3_lat_correction.py"),
                       "original_case_rows_preserved": len(rows),
                       "all_nonlatitude_fields_preserved": True})
    provenance_path.write_text(json.dumps(provenance, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"E3 dipole latitude corrected for {len(rows)} cases; max change {max(differences):.5f} deg")
    verify_snapshot()


if __name__ == "__main__":
    main()
