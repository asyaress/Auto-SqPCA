import datetime as dt
import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from k11_loader import load_hourly_zip, utc_to_local_solar_time


def test_local_solar_time_east_west_wrap():
    t = dt.datetime(2016, 1, 1, 23, 30, tzinfo=dt.timezone.utc)
    assert utc_to_local_solar_time(t, 150) == dt.datetime(2016, 1, 2, 9, 30)
    assert utc_to_local_solar_time(t, -75) == dt.datetime(2016, 1, 1, 18, 30)
    assert utc_to_local_solar_time(t, 285) == dt.datetime(2016, 1, 2, 18, 30)
    with pytest.raises(ValueError):
        utc_to_local_solar_time(t.replace(tzinfo=None), 0)


def test_loader_synthetic_zip(tmp_path):
    path = tmp_path / "plr2016.zip"
    with zipfile.ZipFile(path, "w") as z:
        for m in range(1, 13):
            content = (" Format IAGA-2002 |\n IAGA Code PLR |\n Reported XYZF |\n"
                       " Data Interval Type 1-hour |\n Geodetic Longitude 150.0 |\n"
                       f"2016-{m:02d}-01 00:00:00.000 001 1.0 2.0 3.0 99999.0\n")
            z.writestr(f"plr2016{m:02d}dhor.hor", content)
    data = load_hourly_zip(path, "PLR", 2016)
    assert data["station"] == "PLR" and data["longitude_east_deg"] == 150
    assert data["XYZF_nT"].shape == (12, 4)
    assert np.isnan(data["XYZF_nT"][:, 3]).all()
    assert data["utc"][0] == dt.datetime(2016, 1, 1, tzinfo=dt.timezone.utc)
