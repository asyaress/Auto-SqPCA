"""Synthetic fixed-width and overlap checks; no research result."""
from __future__ import annotations

from d2c import classify, parse_wdc_line


def main() -> None:
    line = b"COI0701X01    20 203" + b"5062"*24 + b"5062"
    assert len(line) == 120
    parsed = parse_wdc_line(line)
    assert parsed["date"].isoformat() == "2007-01-01"
    assert parsed["component"] == "X" and parsed["base"] == 203
    assert len(parsed["tabular"]) == 24 and parsed["tabular"][0] == 5062
    assert parsed["base"]*100 + parsed["tabular"][0] == 25362
    neg = b"COI0701Y01    20 -66" + b"4895"*24 + b"4895"
    y = parse_wdc_line(neg)
    assert y["base"] == -66 and y["base"]*100+y["tabular"][0] == -1705
    assert classify(.023, .01)["labels"] == ["MATCH", "QUANT"]
    assert classify(.6, .01)["labels"] == ["REVISION_LIKE"]
    print("Synthetic D2c parser/classification checks PASS")


if __name__ == "__main__":
    main()
