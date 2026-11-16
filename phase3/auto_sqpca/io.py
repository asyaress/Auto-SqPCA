"""IAGA-2002 XYZF hourly and strict 60-minute fallback readers."""
from __future__ import annotations
import calendar
import datetime as dt
import re
import zipfile
from pathlib import Path
import numpy as np


def _header(lines: list[str], station: str, cadence: str) -> tuple[float,float]:
    text = "\n".join(lines[:35])
    if "IAGA-2002" not in text or "XYZF" not in text or station.upper() not in text or cadence not in text:
        raise ValueError(f"Invalid IAGA-2002 XYZF {cadence} header for {station}")
    def field(label):
        line = next((x for x in lines[:35] if x.startswith(label)), None)
        if line is None: raise ValueError(f"Missing {label} in {station} header")
        return float(line.split("|")[0].split()[-1])
    return field(" Geodetic Latitude"), field(" Geodetic Longitude")


def load_hourly_zip(path: Path, station: str, year: int) -> dict:
    n = 366 if calendar.isleap(year) else 365
    data = np.full((n*24, 3), np.nan)
    seen = np.zeros(n*24, dtype=bool)
    lon = lat = None
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad: raise ValueError(f"ZIP CRC failed: {bad}")
        names = [name for name in z.namelist() if name.lower().endswith(".hor")]
        if len(names) != 12: raise ValueError(f"Expected 12 HOR members in {path}, got {len(names)}")
        for name in names:
            lines = z.read(name).decode("ascii").splitlines()
            lt, ln = _header(lines, station, "1-hour")
            if lon is not None and abs(lon-ln)>1e-6: raise ValueError(f"Longitude changes within {path}")
            lat, lon = lt, ln
            for line in lines:
                if not re.match(r"^\d{4}-\d{2}-\d{2} ", line): continue
                fields = line.split()
                if len(fields) != 7 or not fields[1].endswith(":00:00.000"):
                    raise ValueError(f"Invalid hourly row in {name}: {line}")
                date = dt.date.fromisoformat(fields[0])
                pos = (date - dt.date(year,1,1)).days*24 + int(fields[1][:2])
                if not 0 <= pos < len(data) or seen[pos]: raise ValueError(f"Invalid/duplicate hour: {fields[:2]}")
                seen[pos] = True
                values = np.array([float(x) for x in fields[3:6]])
                values[np.abs(values)>=88888] = np.nan
                data[pos] = values
    if not seen.all(): raise ValueError(f"Incomplete hourly timestamps {station} {year}: {seen.sum()}/{len(seen)}")
    return {"station": station, "year": year, "latitude": lat, "longitude": lon,
            "utc_start": dt.datetime(year,1,1), "values": data, "source": "WDC_HOURLY",
            "path": str(path)}


def minute_hourly_zip(path: Path, station: str, year: int, values: bool = True) -> dict:
    n = 366 if calendar.isleap(year) else 365
    output = np.full((n*24, 3), np.nan)
    complete = np.zeros(n*24, dtype=bool)
    seen_days = set()
    lat = lon = None
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad: raise ValueError(f"ZIP CRC failed: {bad}")
        names = [x for x in z.namelist() if x.lower().endswith(".min")]
        for name in names:
            lines = z.read(name).decode("ascii").splitlines()
            lt, ln = _header(lines, station, "1-minute")
            if lon is not None and abs(lon-ln)>1e-6: raise ValueError(f"Longitude changes within {path}")
            lat, lon = lt, ln
            day_values = np.full((24,60,3), np.nan)
            day_seen = np.zeros((24,60), dtype=bool)
            day_date = None
            for line in lines:
                if not re.match(r"^\d{4}-\d{2}-\d{2} ", line): continue
                fields = line.split()
                if len(fields) != 7 or not fields[1].endswith(":00.000"):
                    raise ValueError(f"Invalid minute row in {name}: {line}")
                date = dt.date.fromisoformat(fields[0])
                if day_date is not None and date != day_date: raise ValueError(f"Multiple days in {name}")
                day_date = date
                h, m = int(fields[1][:2]), int(fields[1][3:5])
                if day_seen[h,m]: raise ValueError(f"Duplicate minute {name} {fields[:2]}")
                day_seen[h,m] = True
                v = np.array([float(x) for x in fields[3:6]])
                v[np.abs(v)>=88888] = np.nan
                day_values[h,m] = v
            if day_date is None: continue
            if day_date.year != year or day_date in seen_days: raise ValueError(f"Invalid/duplicate minute day: {name}")
            seen_days.add(day_date)
            d = (day_date-dt.date(year,1,1)).days
            full = day_seen.all(axis=1) & np.isfinite(day_values).all(axis=(1,2))
            complete[d*24:(d+1)*24] = full
            if values:
                sums_tenths = np.rint(day_values[full]*10).astype(np.int64).sum(axis=1)
                output[d*24:(d+1)*24][full] = np.trunc(sums_tenths/60)/10
    return {"station": station, "year": year, "latitude": lat, "longitude": lon,
            "utc_start": dt.datetime(year,1,1), "values": output,
            "strict_xyz_complete": complete, "source": "PHASE1_MINUTE_RULE_A",
            "path": str(path), "minute_days_present": len(seen_days)}
