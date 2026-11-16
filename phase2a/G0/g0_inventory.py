"""Read-only Gate G0 inventory of acquired and frozen Auto-SqPCA inputs.

This script does not calculate Sq, PCA, D1, D2, or any scientific comparison.
It writes only under phase2a/G0 and reads phase2a/raw and Phase-1 freeze files.
"""
from __future__ import annotations

import calendar
import csv
import datetime as dt
import hashlib
import json
import platform
import re
import sys
import zipfile
import zlib
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
G0 = ROOT / "phase2a" / "G0"
RAW = ROOT / "phase2a" / "raw"
ZIP = RAW / "mendeley" / "jcmdrm5f5x-1.zip"
MEN = RAW / "mendeley" / "jcmdrm5f5x-1"
DOI = "10.17632/jcmdrm5f5x.1"
MEN_URL = "https://data.mendeley.com/public-api/zip/jcmdrm5f5x/download/1"
GFZ_BASE = "https://datapub.gfz-potsdam.de/download/10.5880.Kp.0001/Quiet_Disturbed_Days/"
SENTINEL = re.compile(r"^(?:99999|88888)(?:\.\d+)?$")
MONTHS = {calendar.month_abbr[i]: i for i in range(1, 13)}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_events() -> dict[str, dict]:
    result = {}
    for line in (G0 / "download_events.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("status") == "DOWNLOADED":
            result[row["path"]] = row
    return result


events = load_events()
manifest = []
issues = []
checks = {}


def add_file(path: Path, source: str, url: str, version: str,
             acquired: str = "", parent: str = "", expected_hash: str = "") -> str:
    if not path.is_file():
        issues.append(f"File tidak ada: {path}")
        digest = ""
        size = None
        status = "MISSING"
    else:
        digest = sha256(path)
        size = path.stat().st_size
        status = "OK" if not expected_hash or digest.lower() == expected_hash.lower() else "HASH_MISMATCH"
        if status != "OK":
            issues.append(f"SHA-256 mismatch: {path}; expected={expected_hash}; actual={digest}")
    ev = events.get(str(path), {}) or events.get(str(ROOT / parent), {})
    manifest.append({"source": source, "relative_path": rel(path), "bytes": size,
                     "sha256": digest, "source_url": url, "downloaded_utc": acquired or ev.get("recorded_utc", ""),
                     "dataset_version": version, "parent_archive": parent, "status": status})
    return digest


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def mendeley() -> dict:
    add_file(ZIP, "Mendeley_archive", MEN_URL, DOI)
    snap = json.loads((G0 / "mendeley_snapshot.json").read_text(encoding="utf-8"))
    snapshot_text = json.dumps(snap)
    snapshot_ok = "jcmdrm5f5x" in snapshot_text and ('"version": 1' in snapshot_text or '"version": "1"' in snapshot_text)
    dat_rows = []
    families = Counter()
    shape_counts = Counter()
    invalid_numeric = Counter()
    missing_tokens = Counter()
    precision = defaultdict(list)
    member_errors = []
    with zipfile.ZipFile(ZIP) as archive:
        bad = archive.testzip()
        members = [x for x in archive.infolist() if not x.is_dir()]
        names = [x.filename for x in members]
        if len(names) != len(set(names)):
            member_errors.append("Duplicate member path in Mendeley ZIP")
        for item in members:
            target = MEN / Path(item.filename)
            if not target.is_file():
                member_errors.append(f"Missing extracted member: {item.filename}")
                continue
            if target.stat().st_size != item.file_size:
                member_errors.append(f"Size mismatch: {item.filename}")
            crc = 0
            with target.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    crc = zlib.crc32(block, crc)
            if crc != item.CRC:
                member_errors.append(f"Extracted CRC mismatch: {item.filename}")
            # SHA-256 of every physical extracted file is recorded in the manifest.
            add_file(target, "Mendeley_extracted", MEN_URL, DOI, parent=rel(ZIP))
        extracted = [p for p in MEN.rglob("*") if p.is_file()]
        extra = {p.relative_to(MEN).as_posix() for p in extracted} - set(names)
        if extra:
            member_errors.append(f"Unexpected extracted files: {len(extra)}")
        for path in sorted(p for p in extracted if p.suffix.lower() == ".dat"):
            parts = path.relative_to(MEN).parts
            family = parts[1] if len(parts) > 1 else "UNKNOWN"
            families[family] += 1
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError as exc:
                member_errors.append(f"{rel(path)}: {type(exc).__name__}: {exc}")
                continue
            if not lines:
                member_errors.append(f"Empty DAT file: {rel(path)}")
                continue
            rows = [line.split("\t") for line in lines]
            widths = Counter(map(len, rows))
            if len(widths) != 1:
                member_errors.append(f"Ragged DAT: {rel(path)}; widths={dict(widths)}")
            header = not _is_number(rows[0][1]) if len(rows[0]) > 1 else False
            payload = rows[1:] if header else rows
            columns = rows[0] if header else []
            bad_values = 0
            miss = 0
            decimals = []
            for row in payload:
                for value in row[1:]:
                    token = value.strip()
                    if token.lower() in {"", "na", "nan", "null", "-"} or SENTINEL.fullmatch(token):
                        missing_tokens[token] += 1
                        miss += 1
                    elif not _is_number(token):
                        invalid_numeric[token] += 1
                        bad_values += 1
                    elif "." in token:
                        decimals.append(len(token.split(".", 1)[1].split("e", 1)[0].split("E", 1)[0]))
                    else:
                        decimals.append(0)
            precision[family].extend(decimals)
            shape_counts[f"{family}:{len(payload)}x{len(rows[0])}"] += 1
            dat_rows.append({"relative_path": rel(path), "family": family, "rows_total": len(rows),
                             "data_rows": len(payload), "columns": len(rows[0]), "header_present": header,
                             "first_column": rows[0][0] if header else "(first data row)",
                             "column_names": "|".join(columns), "missing_cells": miss,
                             "non_numeric_cells": bad_values,
                             "printed_decimals_min": min(decimals) if decimals else "",
                             "printed_decimals_max": max(decimals) if decimals else ""})
    write_csv(G0 / "mendeley_dat_inventory.csv", dat_rows,
              ["relative_path", "family", "rows_total", "data_rows", "columns", "header_present",
               "first_column", "column_names", "missing_cells", "non_numeric_cells",
               "printed_decimals_min", "printed_decimals_max"])
    if bad:
        member_errors.append(f"ZIP CRC failed: {bad}")
    expected = {"IQD Sq and SD": 36, "PCA modes": 648}
    if dict(families) != expected:
        member_errors.append(f"DAT family counts expected={expected}, actual={dict(families)}")
    d1 = {name: len(list(MEN.rglob(name))) for name in
          ["COI_X_meanField_m02.dat", "COI_X_EOF1_m02.dat", "COI_X_Sq.SD.S_m02.dat"]}
    if any(v != 1 for v in d1.values()):
        member_errors.append(f"D1 February file counts: {d1}")
    iq = [r for r in dat_rows if r["family"] == "IQD Sq and SD"]
    if not all(r["data_rows"] == 24 and r["columns"] == 37 for r in iq):
        member_errors.append("IQD Sq/SD DAT expected 24 data rows x 37 columns in each file")
    if invalid_numeric:
        member_errors.append(f"Non-numeric DAT tokens: {dict(invalid_numeric)}")
    checks["mendeley_integrity"] = {"pass": not member_errors and snapshot_ok,
        "errors": member_errors + ([] if snapshot_ok else ["Snapshot id/version not verified"])}
    return {"zip_bytes": ZIP.stat().st_size, "zip_members": len(members),
            "extracted_files": len(extracted), "dat_files": len(dat_rows),
            "png_files": sum(p.suffix.lower() == ".png" for p in extracted),
            "families": dict(families), "data_shapes": dict(shape_counts),
            "d1_february_files": d1, "iqd_files": len(iq),
            "iqd_series_annual": len(iq) * 11,
            "missing_token_counts": dict(missing_tokens),
            "non_numeric_token_counts": dict(invalid_numeric),
            "printed_decimals_by_family": {k: {"min": min(v), "max": max(v)} for k, v in precision.items() if v},
            "errors": member_errors}


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def wdc_hourly() -> dict:
    rows = []
    errors = []
    total = 0
    missing = Counter()
    leap_hours = 0
    all_timestamps = set()
    for year in range(2007, 2018):
        path = RAW / "wdc_hourly" / f"COI_{year}_hour_iaga_XYZF.zip"
        url = f"https://wdcapi.bgs.ac.uk/data/zipped-data/hour/COI?years={year}&file_format=iaga&orientation=XYZF"
        add_file(path, "WDC_COI_hourly_archive", url, "WDC IAGA-2002 XYZF; retrieval 2026-11-13")
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                errors.append(f"{path.name}: ZIP CRC failed: {bad}")
            hor = [x for x in archive.namelist() if x.lower().endswith(".hor")]
            if len(hor) != 12:
                errors.append(f"{path.name}: expected 12 HOR members, got {len(hor)}")
            year_times = set()
            for name in hor:
                lines = archive.read(name).decode("ascii", errors="replace").splitlines()
                header = "\n".join(lines[:30])
                for required in ["IAGA-2002", "IAGA Code              COI", "Reported               XYZF", "Data Interval Type     1-hour", "COIX", "COIY", "COIZ", "COIF"]:
                    if required not in header:
                        errors.append(f"{name}: missing header {required!r}")
                count = 0
                month_times = set()
                local_missing = Counter()
                for line in lines:
                    if not re.match(r"^\d{4}-\d{2}-\d{2}\s", line):
                        continue
                    fields = line.split()
                    if len(fields) != 7:
                        errors.append(f"{name}: invalid data columns: {line[:100]!r}")
                        continue
                    try:
                        stamp = dt.datetime.strptime(fields[0] + " " + fields[1], "%Y-%m-%d %H:%M:%S.%f")
                        if stamp.year != year or stamp.minute or stamp.second or stamp.microsecond:
                            errors.append(f"{name}: invalid year or HH:00 timestamp {stamp.isoformat()}")
                        if int(fields[2]) != stamp.timetuple().tm_yday:
                            errors.append(f"{name}: DOY mismatch {stamp.isoformat()} {fields[2]}")
                        if stamp in month_times or stamp in year_times or stamp in all_timestamps:
                            errors.append(f"Duplicate WDC timestamp: {stamp.isoformat()}")
                        month_times.add(stamp)
                        year_times.add(stamp)
                        all_timestamps.add(stamp)
                        if stamp.date() == dt.date(2008, 2, 29):
                            leap_hours += 1
                        for component, token in zip("XYZF", fields[3:]):
                            float(token)
                            if SENTINEL.fullmatch(token):
                                local_missing[component] += 1
                                missing[component] += 1
                    except (ValueError, OverflowError) as exc:
                        errors.append(f"{name}: {type(exc).__name__}: {exc}; line={line[:100]!r}")
                    count += 1
                match = re.search(r"coi(\d{4})(\d{2})dhor", name, re.I)
                if not match:
                    errors.append(f"Unexpected WDC member name: {name}")
                    expected = None
                else:
                    mon = int(match.group(2))
                    expected = calendar.monthrange(year, mon)[1] * 24
                    if count != expected or len(month_times) != expected:
                        errors.append(f"{name}: expected {expected} unique hours, got {count} rows/{len(month_times)} unique")
                rows.append({"year": year, "member": name, "rows": count, "expected_rows": expected,
                             "first_timestamp": min(month_times).isoformat() if month_times else "",
                             "last_timestamp": max(month_times).isoformat() if month_times else "",
                             **{f"missing_{c}": local_missing[c] for c in "XYZF"}})
                total += count
            expected_year = (366 if calendar.isleap(year) else 365) * 24
            if len(year_times) != expected_year:
                errors.append(f"{year}: expected {expected_year} unique hours, got {len(year_times)}")
    write_csv(G0 / "wdc_hourly_inventory.csv", rows,
              ["year", "member", "rows", "expected_rows", "first_timestamp", "last_timestamp",
               "missing_X", "missing_Y", "missing_Z", "missing_F"])
    if leap_hours != 24:
        errors.append(f"2008-02-29 expected 24 hours, got {leap_hours}")
    checks["wdc_hourly_integrity"] = {"pass": not errors, "errors": errors}
    return {"archives": 11, "monthly_hor_files": len(rows), "hourly_rows": total,
            "expected_hourly_rows": sum((366 if calendar.isleap(y) else 365) * 24 for y in range(2007, 2018)),
            "unique_timestamps": len(all_timestamps), "leap_day_2008_hours": leap_hours,
            "missing_by_component": dict(missing), "errors": errors}


def gfz() -> dict:
    rows = []
    errors = []
    qualifiers = Counter()
    for year in range(2007, 2018):
        path = RAW / "gfz" / f"QD_days{year}.txt"
        add_file(path, "GFZ_IQD_IDD", GFZ_BASE + path.name, "GFZ Kp DOI 10.5880/Kp.0001")
        content = path.read_text(encoding="utf-8", errors="replace")
        if "10.5880/Kp.0001" not in content or "Quietest Days" not in content or "Most Disturbed Days" not in content:
            errors.append(f"{path.name}: source/header not recognized")
        for line in content.splitlines():
            match = re.match(r"^\s*([A-Z][a-z]{2})\s+(\d{4})\s+(.+)$", line)
            if not match:
                continue
            mon_str, row_year, rest = match.groups()
            month = MONTHS.get(mon_str)
            if not month or int(row_year) != year:
                errors.append(f"{path.name}: invalid month/year {mon_str} {row_year}")
                continue
            tokens = rest.split()
            if len(tokens) != 15:
                errors.append(f"{path.name}: {mon_str} expected 15 Q/D days, got {len(tokens)}")
                continue
            days = []
            for token in tokens:
                m = re.fullmatch(r"(\d{1,2})([A-Za-z*]*)", token)
                if not m:
                    errors.append(f"{path.name}: invalid day token {token!r}")
                    continue
                day, suffix = int(m.group(1)), m.group(2)
                qualifiers[suffix] += 1
                if day < 1 or day > calendar.monthrange(year, month)[1]:
                    errors.append(f"{path.name}: invalid calendar day {mon_str} {token}")
                days.append(day)
            if len(set(days[:10])) != 10 or len(set(days[10:])) != 5:
                errors.append(f"{path.name}: duplicate Q or D days in {mon_str}")
            rows.append({"year": year, "month": month, "month_name": mon_str,
                         "quiet_days": "|".join(tokens[:10]), "disturbed_days": "|".join(tokens[10:])})
        if sum(r["year"] == year for r in rows) != 12:
            errors.append(f"{path.name}: expected 12 monthly records")
    if len({(r["year"], r["month"]) for r in rows}) != 132:
        errors.append("GFZ month/year coverage is not 132 unique months")
    write_csv(G0 / "gfz_day_inventory.csv", rows,
              ["year", "month", "month_name", "quiet_days", "disturbed_days"])
    checks["gfz_iqd_integrity"] = {"pass": not errors, "errors": errors}
    return {"annual_files": 11, "months": len(rows), "quiet_day_entries": len(rows) * 10,
            "disturbed_day_entries": len(rows) * 5, "day_suffix_counts": dict(qualifiers), "errors": errors}


def phase1() -> dict:
    freeze_path = ROOT / "audit_final" / "dataset_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    errors = []
    verified = 0
    minute = 0
    for record in freeze.get("inputs", []):
        archive = record.get("archive")
        if not archive:
            continue
        path = ROOT / archive["path"]
        digest = add_file(path, "Phase1_frozen_minute_archive", record.get("request_url", ""),
                          freeze.get("schema", ""), expected_hash=archive["sha256"])
        verified += bool(digest)
        if record.get("station") == "COI" and 2007 <= record.get("year", 0) <= 2017:
            minute += bool(digest)
        if digest.lower() != archive["sha256"].lower():
            errors.append(f"Frozen Phase1 input changed: {archive['path']}")
    for section in ("code", "source_audit_outputs", "final_outputs"):
        for item in freeze.get(section, []):
            if not isinstance(item, dict) or "path" not in item or "sha256" not in item:
                continue
            path = ROOT / item["path"]
            if not path.is_file() or sha256(path).lower() != item["sha256"].lower():
                errors.append(f"Frozen Phase1 artifact changed: {item['path']}")
    for section in ("historical_output_archive",):
        item = freeze.get(section, {})
        if isinstance(item, dict) and "path" in item and "sha256" in item:
            path = ROOT / item["path"]
            if not path.is_file() or sha256(path).lower() != item["sha256"].lower():
                errors.append(f"Frozen Phase1 artifact changed: {item['path']}")
    if minute != 11:
        errors.append(f"Expected 11 COI minute archives 2007–2017, got {minute}")
    checks["phase1_freeze_unchanged"] = {"pass": not errors, "errors": errors}
    return {"freeze_created_utc": freeze.get("created_utc"), "frozen_input_archives_verified": verified,
            "coi_minute_archives_2007_2017": minute, "errors": errors}


def environment() -> dict:
    packages = {}
    try:
        from importlib import metadata
        for package in ("requests", "numpy", "pandas", "scipy", "python-docx"):
            try:
                packages[package] = metadata.version(package)
            except metadata.PackageNotFoundError:
                packages[package] = "not installed"
    except ImportError:
        pass
    env = {"python": sys.version, "executable": sys.executable, "platform": platform.platform(),
           "architecture": platform.machine(), "packages": packages,
           "inventory_script_sha256": sha256(Path(__file__))}
    (G0 / "python_environment.json").write_text(json.dumps(env, ensure_ascii=False, indent=2), encoding="utf-8")
    return env


def main() -> None:
    protocol = next(G0.glob("Protokol Final Fase 2A*.docx"))
    registration_time = dt.datetime.now(dt.timezone.utc).isoformat()
    protocol_digest = add_file(protocol, "Phase2A_protocol", str(protocol),
                               "G0-registration-1 (local; original has no explicit version number)",
                               acquired=registration_time)
    registration = {"local_version": "G0-registration-1", "version_source": "Assigned during Gate G0; no explicit version number in DOCX",
                    "document_date": "2026-11-13", "document_sha256": protocol_digest,
                    "registered_utc": registration_time}
    (G0 / "protocol_registration.json").write_text(json.dumps(registration, indent=2), encoding="utf-8")
    men = mendeley()
    wdc = wdc_hourly()
    days = gfz()
    frozen = phase1()
    env = environment()
    write_csv(G0 / "input_manifest.csv", manifest,
              ["source", "relative_path", "bytes", "sha256", "source_url", "downloaded_utc",
               "dataset_version", "parent_archive", "status"])
    checks["d1_inputs_available"] = {"pass": all(v == 1 for v in men["d1_february_files"].values()) and days["months"] == 132,
                                      "errors": []}
    checks["d2_inputs_available"] = {"pass": checks["wdc_hourly_integrity"]["pass"] and frozen["coi_minute_archives_2007_2017"] == 11,
                                      "errors": []}
    checks["sq_iqd_inputs_available"] = {"pass": men["iqd_files"] == 36 and days["months"] == 132,
                                         "errors": []}
    complete = all(v["pass"] for v in checks.values()) and not issues
    concerns = []
    if wdc["missing_by_component"].get("F", 0):
        concerns.append("WDC COI hourly has missing sentinel values in F and X/Y/Z; the later missing-data policy must preserve these gaps.")
    if men["missing_token_counts"]:
        concerns.append("Mendeley DAT contains missing-value tokens; see inventory and validation counts.")
    concerns.append("Mendeley DAT files do not encode physical units; units are only specified in the research protocol/source context.")
    concerns.append("Original protocol has no explicit version number; local G0-registration-1 is bound to DOCX SHA-256.")
    attempts = [json.loads(line) for line in (G0 / "download_events.jsonl").read_text(encoding="utf-8").splitlines()]
    failed_attempts = [{"source": a.get("source"), "year": a.get("year"), "url": a.get("url"),
                        "recorded_utc": a.get("recorded_utc"), "error_original": a.get("error")}
                       for a in attempts if a.get("error")]
    decision = "FAIL" if not complete else ("CONDITIONAL PASS" if concerns else "PASS")
    validation = {"schema": "Auto-SqPCA-Phase2A-G0-validation-v1", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "scope": "Inventory only; no D1/D2/PCA/DTW/DIFI/PC classification",
                  "decision": f"G0 {decision}", "protocol": registration, "checks": checks,
                  "mendeley": men, "wdc_hourly": wdc, "gfz": days, "phase1": frozen,
                  "environment": env, "manifest_rows": len(manifest), "concerns": concerns,
                  "failed_download_attempts_recovered": failed_attempts,
                  "units_and_time_metadata": {
                      "WDC": "IAGA-2002 XYZF; XYZF magnetic field components in nT per INTERMAGNET format documentation; source timestamps HH:00, UTC per WDC convention",
                      "Mendeley": "DAT headers use h/hour/day and y.YYYY labels; no timezone or physical-unit metadata embedded in DAT; protocol assigns PC arbitrary unit and EOF nT",
                      "GFZ": "Calendar day ranks Q1–Q10 and D1–D5 by month/year; no physical units"},
                  "errors": issues + [e for v in checks.values() for e in v["errors"]]}
    (G0 / "G0_validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"decision": validation["decision"], "checks": checks, "mendeley": {k: men[k] for k in ("zip_members", "dat_files", "png_files", "families", "missing_token_counts")},
                      "wdc": {k: wdc[k] for k in ("hourly_rows", "expected_hourly_rows", "missing_by_component")},
                      "gfz": {k: days[k] for k in ("months", "quiet_day_entries")},
                      "phase1": frozen, "manifest_rows": len(manifest)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
