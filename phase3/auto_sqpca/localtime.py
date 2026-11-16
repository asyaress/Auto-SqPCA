"""Integer-hour approximation to local solar time specified by F3-v1."""
from __future__ import annotations
import datetime as dt
import numpy as np


def delta_hours(longitude_east_deg: float) -> int:
    lon = ((float(longitude_east_deg) + 180) % 360) - 180
    return round(lon / 15)


def local_timestamps(utc_stamps: list[dt.datetime], longitude_east_deg: float) -> list[dt.datetime]:
    shift = dt.timedelta(hours=delta_hours(longitude_east_deg))
    return [stamp + shift for stamp in utc_stamps]


def month_matrix(utc_values: np.ndarray, utc_start: dt.datetime, longitude_east_deg: float,
                 year: int, month: int) -> np.ndarray:
    """Gather UTC hourly array into 24 x N full local-calendar days."""
    import calendar
    n = calendar.monthrange(year, month)[1]
    result = np.full((n*24, utc_values.shape[1]), np.nan, dtype=np.float64)
    shift = delta_hours(longitude_east_deg)
    first_utc = dt.datetime(year, month, 1) - dt.timedelta(hours=shift)
    first_index = int((first_utc-utc_start).total_seconds()//3600)
    source_lo = max(0, first_index)
    source_hi = min(len(utc_values), first_index+n*24)
    if source_hi > source_lo:
        target_lo = source_lo-first_index
        result[target_lo:target_lo+(source_hi-source_lo)] = utc_values[source_lo:source_hi]
    return result.reshape(n,24,utc_values.shape[1]).transpose(1,0,2)
