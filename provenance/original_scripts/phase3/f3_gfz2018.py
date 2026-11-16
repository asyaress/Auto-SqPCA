"""Acquire the GFZ 2018 IQD calendar omitted from Phase 3 acquisition."""
from __future__ import annotations

import calendar
import datetime as dt
import json
import re
import requests

from f3_preflight import OUT, sha, verify_snapshot

URL = "https://datapub.gfz-potsdam.de/download/10.5880.Kp.0001/Quiet_Disturbed_Days/QD_days2018.txt"
DEST = OUT / "raw/gfz/QD_days2018.txt"


def main() -> None:
    verify_snapshot()
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists():
        raise RuntimeError(f"GFZ 2018 input already exists; refusing overwrite: {DEST}")
    response = requests.get(URL, headers={"User-Agent": "Auto-SqPCA-F3A/1.0", "Accept-Encoding": "identity"}, timeout=120)
    status = response.status_code
    raw = response.content
    headers = dict(response.headers)
    if status != 200:
        raise RuntimeError(f"GFZ 2018 unexpected HTTP {status}: {raw[:300]!r}")
    text = raw.decode("utf-8-sig")
    lines = [x for x in text.splitlines() if re.match(r"^\s*[A-Z][a-z]{2}\s+2018\s", x)]
    if len(lines) != 12:
        raise RuntimeError(f"GFZ 2018 expected 12 monthly lines, got {len(lines)}")
    names = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    monthly = []
    for month, (name, line) in enumerate(zip(names, lines), 1):
        fields = line.split()
        if fields[:2] != [name, "2018"] or len(fields) < 17:
            raise RuntimeError(f"GFZ 2018 malformed {name} row: {line!r}")
        days = [int(re.match(r"^\d+", x).group()) for x in fields[2:12]]
        if len(set(days)) != 10 or not all(1 <= d <= calendar.monthrange(2018, month)[1] for d in days):
            raise RuntimeError(f"GFZ 2018 invalid quiet-day ranks {name}: {days}")
        monthly.append({"month": month, "Q1_Q5": days[:5], "Q1_Q10": days})
    DEST.write_bytes(raw)
    record = {"source": "GFZ International Quiet/Disturbed Days", "doi": "10.5880/Kp.0001",
              "url": URL, "downloaded_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "http_status": status, "response_headers": {k: headers.get(k) for k in ("Content-Type", "Content-Length", "Content-Encoding")},
              "path": DEST.relative_to(OUT).as_posix(), "bytes": len(raw), "sha256": sha(DEST),
              "months_validated": 12, "monthly_quiet_days": monthly}
    (OUT / "F3_GFZ2018_source.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    verify_snapshot()
    print(f"GFZ 2018 HTTP {status}, {len(raw)} bytes, SHA-256 {record['sha256']}")


if __name__ == "__main__":
    main()
