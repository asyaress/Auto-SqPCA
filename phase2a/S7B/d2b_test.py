"""Synthetic checks for D2b rules; produces no scientific results."""
from __future__ import annotations

import numpy as np

from d2b_meanfield import classify, interpolate_month


def main() -> None:
    assert classify(.023, .01)["labels"] == ["MATCH", "QUANT"]
    assert classify(.05, .01)["labels"] == ["QUANT"]
    assert classify(.2, .01)["labels"] == ["SMALL_UNEXPLAINED"]
    assert classify(.6, .01)["labels"] == ["REVISION"]
    a = np.tile(np.arange(24, dtype=float), (3, 1))
    a[0, 2] = np.nan
    a[1, :] = np.nan
    a[2, 20] = np.nan
    processed, original, filled, whole = interpolate_month(a)
    assert processed[0, 2] == 2 and filled[0, 2]
    assert whole.tolist() == [False, True, False]
    assert np.isnan(processed[1]).all()
    assert processed[2, 20] == 20 and filled[2, 20]
    edge = np.arange(24, dtype=float).reshape(1, 24)
    edge[0, 0] = np.nan
    result, _, filled_edge, _ = interpolate_month(edge)
    assert np.isnan(result[0, 0]) and not filled_edge[0, 0]
    print("Synthetic D2b rule checks PASS: overlap, four classes, internal gap, full day, edge")


if __name__ == "__main__":
    main()
