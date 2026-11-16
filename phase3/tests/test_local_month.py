import datetime as dt
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from auto_sqpca.localtime import month_matrix


def test_month_boundary_minus_one_hour():
    start = dt.datetime(2016,12,31)
    data = np.arange(72,dtype=float)[:,None]
    jan = month_matrix(data,start,351.578,2017,1)
    assert jan.shape == (24,31,1)
    assert jan[0,0,0] == 25  # LT Jan 1 00 = UTC Jan 1 01
    assert jan[22,1,0] == 71
    assert np.isnan(jan[23,1,0])
