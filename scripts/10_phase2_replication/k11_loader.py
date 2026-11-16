"""K11 infrastructure only: read hourly IAGA-2002 XYZF ZIPs and map UTC to local solar time.

No station data are acquired or analyzed here. Callers supply a ZIP path and station code.
"""
from __future__ import annotations

import datetime as dt
import re
import zipfile
from pathlib import Path

import numpy as np

STATIONS = frozenset(("PLR", "TUN", "KDU", "GUA"))


def utc_to_local_solar_time(timestamp_utc: dt.datetime, longitude_east_deg: float) -> dt.datetime:
    if timestamp_utc.tzinfo is None or timestamp_utc.utcoffset() != dt.timedelta(0):
        raise ValueError("timestamp_utc must be timezone-aware UTC")
    if not -180 <= longitude_east_deg <= 360:
        raise ValueError("longitude_east_deg outside supported east-longitude range")
    return timestamp_utc.replace(tzinfo=None) + dt.timedelta(seconds=longitude_east_deg * 240)


def load_hourly_zip(path: str | Path, station: str, year: int) -> dict:
    station = station.upper()
    if station not in STATIONS or not 2014 <= year <= 2018:
        raise ValueError("K11 loader accepts PLR/TUN/KDU/GUA and 2014–2018 only")
    records = []
    longitude = None
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise ValueError(f"ZIP CRC failed: {bad}")
        names = [n for n in archive.namelist() if n.lower().endswith(".hor")]
        if len(names) != 12:
            raise ValueError(f"Expected 12 monthly HOR files, got {len(names)}")
        for name in sorted(names):
            lines = archive.read(name).decode("ascii").splitlines()
            flags = set()
            local_lon = None
            for line in lines:
                if line.startswith(" Format") and "IAGA-2002" in line: flags.add("format")
                if line.startswith(" IAGA Code") and station in line: flags.add("station")
                if line.startswith(" Reported") and "XYZF" in line: flags.add("orientation")
                if line.startswith(" Data Interval Type") and "1-hour" in line: flags.add("hourly")
                if line.startswith(" Geodetic Longitude"):
                    local_lon = float(line.split("|")[0].split()[-1])
                if not re.match(r"^\d{4}-\d{2}-\d{2} ", line):
                    continue
                fields = line.split()
                if len(fields) != 7:
                    raise ValueError(f"Invalid hourly row {name}: {line}")
                stamp = dt.datetime.fromisoformat(fields[0] + "T" + fields[1]).replace(tzinfo=dt.timezone.utc)
                if stamp.year != year or not fields[1].endswith(":00:00.000"):
                    raise ValueError(f"Invalid hourly timestamp {name}: {fields[:2]}")
                values = [float(x) for x in fields[3:7]]
                records.append((stamp, *(np.nan if abs(v) >= 88888 else v for v in values)))
            if flags != {"format", "station", "orientation", "hourly"} or local_lon is None:
                raise ValueError(f"Incomplete IAGA header {name}: {flags}, longitude={local_lon}")
            if longitude is not None and abs(longitude - local_lon) > 1e-8:
                raise ValueError(f"Longitude changed across monthly files: {longitude} to {local_lon}")
            longitude = local_lon
    records.sort(key=lambda r: r[0])
    if len({r[0] for r in records}) != len(records):
        raise ValueError("Duplicate hourly UTC timestamp")
    return {"station": station, "year": year, "longitude_east_deg": longitude,
            "utc": [r[0] for r in records], "XYZF_nT": np.array([r[1:] for r in records], dtype=np.float64)}
