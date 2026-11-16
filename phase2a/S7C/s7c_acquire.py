"""One HTTP acquisition of official WDC hourly COI 2007-2017 in WDC/XYZF format."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import stat
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from s7c_prepare import ROOT, OUT, sha

URL = "https://wdcapi.bgs.ac.uk/data/zipped-data/hour/COI?years=2007-2017&file_format=wdc&orientation=XYZF"
RAW_DIR = ROOT / "phase2a/raw/wdc_format_hourly"
ARCHIVE = RAW_DIR / "COI_2007-2017_hour_wdc_XYZF.zip"


def record(data: dict) -> None:
    (OUT / "S7C_acquisition.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    if ARCHIVE.exists() or (OUT / "S7C_acquisition.json").exists():
        raise RuntimeError("S7C WDC acquisition already attempted; no automatic redownload")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    result = {"requested_url": URL, "requested_utc": now.isoformat(), "attempts": 1,
              "status": "STARTED"}
    part = RAW_DIR / "COI_2007-2017_hour_wdc_XYZF.response.part"
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "Auto-SqPCA-S7C-D2c/1.0"})
        with urllib.request.urlopen(req, timeout=180) as response:
            result["http_status"] = response.status
            result["final_url"] = response.geturl()
            result["headers"] = {k: v for k, v in response.headers.items()
                                  if k.lower() in ("content-type", "content-length", "last-modified", "etag")}
            with part.open("wb") as stream:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    stream.write(block)
        result["received_bytes"] = part.stat().st_size
        result["received_sha256"] = sha(part)
        if result["http_status"] != 200 or part.stat().st_size == 0 or not zipfile.is_zipfile(part):
            result["status"] = "UNAVAILABLE_OR_NONZIP"
            result["error"] = f"HTTP {result['http_status']}; bytes={part.stat().st_size}; is_zipfile={zipfile.is_zipfile(part)}"
            record(result)
            print(result["error"])
            return
        with zipfile.ZipFile(part) as archive:
            failed = archive.testzip()
            if failed is not None:
                raise RuntimeError(f"WDC ZIP CRC failed at member {failed}")
            members = archive.namelist()
            if not members:
                raise RuntimeError("WDC ZIP has no members")
            result["members"] = members
            result["member_count"] = len(members)
        os.replace(part, ARCHIVE)
        ARCHIVE.chmod(stat.S_IREAD)
        result["status"] = "DOWNLOADED_VALID_ZIP"
        result["raw_path"] = str(ARCHIVE)
        result["completed_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        result["archive_sha256"] = sha(ARCHIVE)
        record(result)
        with (OUT / "S7C_execution.log").open("a", encoding="utf-8") as log:
            log.write(f"INFO {result['completed_utc']} WDC format downloaded HTTP 200 bytes={result['received_bytes']} sha256={result['archive_sha256']} members={result['member_count']}\n")
        print(f"HTTP 200; {result['received_bytes']} bytes; SHA-256 {result['archive_sha256']}; {result['member_count']} members")
    except Exception as error:
        result["status"] = "ACQUISITION_FAILED"
        result["error_original"] = f"{type(error).__name__}: {error}"
        if part.exists():
            result["partial_path"] = str(part)
            result["partial_bytes"] = part.stat().st_size
            result["partial_sha256"] = sha(part)
        record(result)
        with (OUT / "S7C_execution.log").open("a", encoding="utf-8") as log:
            log.write(f"ERROR {result['error_original']}\n")
        print(result["error_original"])


if __name__ == "__main__":
    main()
