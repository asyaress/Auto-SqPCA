"""Acquire F3A WDC hourly station years, preserving Phase 1 minute fallback."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from auto_sqpca.io import load_hourly_zip
from f3_preflight import ROOT, OUT, sha, verify_snapshot

RAW = OUT / "raw/hourly"
TARGETS = [(s,y) for s in ("KDU","GUA") for y in range(2014,2019)] + [(s,2017) for s in ("PLR","TUN")]


def log(item: dict) -> None:
    with (OUT / "F3A_acquisition.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(item["station"], item["year"], item["status"], item.get("http_status"), item.get("bytes"), flush=True)


def acquire_one(station: str, year: int, freeze: dict) -> dict:
    url = f"https://wdcapi.bgs.ac.uk/data/zipped-data/hour/{station}?years={year}&file_format=iaga&orientation=XYZF"
    path = RAW / f"{station}_{year}_hour_iaga_XYZF.zip"
    item = {"station": station, "year": year, "url": url,
            "downloaded_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
    if path.exists():
        try:
            loaded = load_hourly_zip(path, station, year)
            item.update(status="WDC_HOURLY_REUSED", http_status="PREVIOUS_DOWNLOAD", bytes=path.stat().st_size,
                        sha256=sha(path), longitude=loaded["longitude"], latitude=loaded["latitude"])
            return item
        except Exception as e:
            raise RuntimeError(f"Existing hourly ZIP invalid {path}: {type(e).__name__}: {e}") from e
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Auto-SqPCA-F3A/1.0", "Accept-Encoding": "identity"})
        with urllib.request.urlopen(request, timeout=120) as response:
            status = response.status
            body = response.read()
            content_type = response.headers.get("Content-Type", "")
        item.update(http_status=status, response_content_type=content_type)
        if status == 200:
            temp = path.with_suffix(".zip.part")
            temp.write_bytes(body)
            try:
                with zipfile.ZipFile(temp) as archive:
                    bad = archive.testzip()
                    if bad: raise RuntimeError(f"ZIP CRC failed for member {bad}")
                loaded = load_hourly_zip(temp, station, year)
            except Exception:
                temp.unlink(missing_ok=True)
                raise
            temp.replace(path)
            item.update(status="WDC_HOURLY", bytes=len(body), sha256=sha(path),
                        longitude=loaded["longitude"], latitude=loaded["latitude"],
                        valid_xyz_hours=int(__import__("numpy").isfinite(loaded["values"]).all(axis=1).sum()))
            return item
        if status != 202:
            raise RuntimeError(f"Unexpected HTTP {status}: {body[:300]!r}")
        item["response_body_excerpt"] = body[:300].decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        item["http_status"] = e.code
        body = e.read()
        item["response_body_excerpt"] = body[:300].decode("utf-8", "replace")
        if e.code != 202:
            item.update(status="ACQUISITION_ERROR", error=f"HTTPError: {e}")
            return item
    except Exception as e:
        item.update(status="ACQUISITION_ERROR", error=f"{type(e).__name__}: {e}")
        return item
    frozen = freeze.get((station,year))
    if not frozen or frozen["status"] != "OK" or not frozen.get("archive"):
        item.update(status="NO_DATA_NO_FALLBACK", error="Hourly NO_DATA; Phase 1 minute archive unavailable")
        return item
    arc = frozen["archive"]
    source = ROOT / arc["path"]
    if sha(source) != arc["sha256"]:
        item.update(status="FALLBACK_HASH_ERROR", error=f"Phase 1 minute SHA mismatch: {arc['path']}")
        return item
    item.update(status="PHASE1_MINUTE_RULE_A", fallback_path=arc["path"],
                fallback_sha256=arc["sha256"], fallback_bytes=arc["bytes"])
    return item


def main() -> None:
    verify_snapshot()
    tests = json.loads((OUT / "F3_synthetic_tests.json").read_text(encoding="utf-8"))
    if set(tests) != {f"T{i}" for i in range(1,9)} or not all(v["passed"] for v in tests.values()):
        raise RuntimeError("Synthetic T1-T8 have not all passed")
    freeze = json.loads((ROOT / "audit_final/dataset_freeze.json").read_text(encoding="utf-8"))
    lookup = {(r["station"], r["year"]): r for r in freeze["inputs"]}
    entries = []
    for station, year in TARGETS:
        item = acquire_one(station, year, lookup)
        entries.append(item)
        log(item)
    for year in range(2007,2018):
        path = ROOT / "phase2a/raw/wdc_hourly" / f"COI_{year}_hour_iaga_XYZF.zip"
        entries.append({"station":"COI", "year":year, "status":"G0_WDC_HOURLY_REUSED",
                        "path":path.relative_to(ROOT).as_posix(), "sha256":sha(path), "bytes":path.stat().st_size})
    (OUT / "F3_data_sources.json").write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    verify_snapshot()
    print("Acquisition complete", len(entries), "station-years")


if __name__ == "__main__":
    main()
