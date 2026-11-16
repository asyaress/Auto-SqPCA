"""Document and correct the first WDC query's two-year selection; one full-range GET."""
from __future__ import annotations

import datetime as dt
import json
import os
import stat
import urllib.request
import zipfile
from pathlib import Path

from s7c_acquire import OUT, RAW_DIR, sha

URL = ("https://wdcapi.bgs.ac.uk/data/zipped-data/hour/COI"
       "?start_dt=2007-01-01&end_dt=2018-01-01&file_format=wdc&orientation=XYZF")
ARCHIVE = RAW_DIR / "COI_2007_to_2017_hour_wdc_XYZF.zip"
EVENT = OUT / "S7C_acquisition_correction.json"


def record(data: dict) -> None:
    EVENT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    if EVENT.exists() or ARCHIVE.exists():
        raise RuntimeError("Corrected WDC acquisition already attempted; no automatic repeat")
    first = json.loads((OUT / "S7C_acquisition.json").read_text(encoding="utf-8"))
    first_members = [m for m in first.get("members", []) if m.endswith("h.wdc")]
    if sorted(first_members) != ["coi2007h.wdc", "coi2017h.wdc"]:
        raise RuntimeError(f"First response differs from documented two-year selection: {first_members}")
    event = {"reason": "First years=2007-2017 query selected only endpoint years 2007 and 2017; preserve original raw response",
             "first_url": first["requested_url"], "first_archive_sha256": first["archive_sha256"],
             "first_wdc_members": first_members, "corrected_url": URL,
             "requested_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "attempts_this_correction": 1,
             "status": "STARTED"}
    part = RAW_DIR / "COI_2007_to_2017_hour_wdc_XYZF.response.part"
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "Auto-SqPCA-S7C-D2c/1.0"})
        with urllib.request.urlopen(req, timeout=180) as response:
            event["http_status"] = response.status
            event["final_url"] = response.geturl()
            event["headers"] = {k: v for k, v in response.headers.items()
                                if k.lower() in ("content-type", "content-length", "last-modified", "etag")}
            with part.open("wb") as stream:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    stream.write(block)
        event["received_bytes"] = part.stat().st_size
        event["received_sha256"] = sha(part)
        if event["http_status"] != 200 or not zipfile.is_zipfile(part):
            raise RuntimeError(f"Corrected WDC response not ZIP: HTTP {event['http_status']}, bytes={part.stat().st_size}")
        with zipfile.ZipFile(part) as archive:
            failed = archive.testzip()
            if failed:
                raise RuntimeError(f"Corrected WDC ZIP CRC failed: {failed}")
            names = sorted(n for n in archive.namelist() if n.endswith("h.wdc"))
            expected = [f"coi{year}h.wdc" for year in range(2007, 2018)]
            event["wdc_members"] = names
            event["all_members"] = archive.namelist()
            if names != expected:
                raise RuntimeError(f"Corrected WDC period incomplete: expected={expected}, got={names}")
        os.replace(part, ARCHIVE)
        ARCHIVE.chmod(stat.S_IREAD)
        event["status"] = "DOWNLOADED_COMPLETE_VALID_ZIP"
        event["raw_path"] = str(ARCHIVE)
        event["archive_sha256"] = sha(ARCHIVE)
        event["completed_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        record(event)
        with (OUT / "S7C_execution.log").open("a", encoding="utf-8") as log:
            log.write(f"INFO acquisition correction: first query returned only 2007/2017; corrected URL HTTP 200, 11 year files, bytes={event['received_bytes']}, sha256={event['archive_sha256']}\n")
        print(f"Corrected WDC ZIP: {event['received_bytes']} bytes, 11 year files, SHA-256 {event['archive_sha256']}")
    except Exception as error:
        event["status"] = "CORRECTED_ACQUISITION_FAILED"
        event["error_original"] = f"{type(error).__name__}: {error}"
        if part.exists():
            event["partial_path"] = str(part)
            event["partial_bytes"] = part.stat().st_size
            event["partial_sha256"] = sha(part)
        record(event)
        with (OUT / "S7C_execution.log").open("a", encoding="utf-8") as log:
            log.write(f"ERROR {event['error_original']}\n")
        print(event["error_original"])


if __name__ == "__main__":
    main()
