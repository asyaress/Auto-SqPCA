"""Verify cached F3A final pipeline stages without rerunning frozen E1 holdout.

The amendment explicitly permits cached cases when their hash agrees. This
mode checks each stage in dependency order and records the result for C5.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import zipfile

from f3_preflight import OUT, ROOT, sha, verify_snapshot

EXPECTED = {
    "protocol": "617c96d0cbda26fa3f6333ea1638030a35db1836fd99ba35f2a3bb18ea091327",
    "frozen": "a2a2cd09ccf4c16c87a9033d792de80762d253c2db16455f81cc4329ad26981d",
    "holdout": "1acbda1a8825b6b878704395973fea0c37b4fd1324ee470df106f2344d1aceb3",
    "archive": "ece7681a70c886966f3ad6818288f5277f3cfe7f8203bbb8e29af2cf9be5c1d8",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help="Verify immutable cached F3A stages and final review package")
    args = parser.parse_args()
    if not args.verify:
        parser.error("Use --verify; F3-v1.1 prohibits recomputing frozen E1 for Tugas B")
    stages = []
    frozen_count = verify_snapshot()
    stages.append({"stage": "frozen_phase1_phase2", "status": "PASS", "count": frozen_count})
    for label, path in (("protocol", OUT / "F3_protocol_v1.md"),
                        ("frozen", OUT / "F3_E1_frozen.json"),
                        ("holdout", OUT / "work/E1_holdout_cases.csv")):
        actual = sha(path)
        if actual != EXPECTED[label]:
            raise RuntimeError(f"{label} SHA-256 mismatch: expected {EXPECTED[label]}, got {actual}")
        stages.append({"stage": label, "status": "PASS", "sha256": actual})
    config = json.loads((OUT / "F3_E1_frozen.json").read_text(encoding="utf-8"))
    for name, digest in config["code_sha256"].items():
        if sha(OUT / name) != digest:
            raise RuntimeError(f"Frozen E1 code mismatch: {name}")
    stages.append({"stage": "frozen_E1_code", "status": "PASS", "files": len(config["code_sha256"])})
    source = json.loads((OUT / "F3_GFZ2018_source.json").read_text(encoding="utf-8"))
    if sha(OUT / source["path"]) != source["sha256"] or source["http_status"] != 200 or source["months_validated"] != 12:
        raise RuntimeError("GFZ 2018 acquisition validation/hash mismatch")
    stages.append({"stage": "f3_gfz2018", "status": "PASS", "sha256": source["sha256"]})
    correction = json.loads((OUT / "F3_E1_2018_correction.json").read_text(encoding="utf-8"))
    if correction["final_holdout_sha256"] != EXPECTED["holdout"] or \
       correction["preliminary_rows_preserved_as_prefix"] is not True or \
       correction["recomputed_prior_case_months"] is not False or \
       sha(OUT / "work/E1_pre_GFZ2018/E1_holdout_cases.csv") != correction["preliminary_holdout_sha256"]:
        raise RuntimeError("GFZ 2018 correction provenance/hash mismatch")
    stages.append({"stage": "f3_e1_2018_correction", "status": "PASS", "supplement_cases": correction["supplement_cases"]})
    plan = json.loads((OUT / "F3_E1_analysis_plan.json").read_text(encoding="utf-8"))
    if sha(OUT / "f3_e1_eval.py") != plan["evaluation_code_sha256"]:
        raise RuntimeError("Pre-registered E1 evaluator code changed")
    c1 = json.loads((OUT / "F3_C1_result.json").read_text(encoding="utf-8"))
    if c1["holdout_cases_sha256"] != EXPECTED["holdout"] or c1["holdout_cases"] != correction["final_holdout_rows"]:
        raise RuntimeError("E1 evaluator result does not match corrected cases")
    stages.append({"stage": "f3_e1_eval", "status": "PASS", "C1_success": c1["C1_success"]})
    archive = OUT / "F3A_review.zip"
    if sha(archive) != EXPECTED["archive"] or sha(archive) != (OUT / "F3A_review.zip.sha256").read_text().split()[0]:
        raise RuntimeError("F3A archive SHA-256 mismatch")
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise RuntimeError("F3A review ZIP CRC failure")
        entries = z.namelist()
        if any(name.startswith(("raw/", "work/")) for name in entries):
            raise RuntimeError("F3A review ZIP includes raw/work data")
        lines = z.read("F3A_checksums.sha256").decode("utf-8").splitlines()
        import hashlib
        for line in lines:
            digest, name = line.split("  ", 1)
            if hashlib.sha256(z.read(name)).hexdigest() != digest:
                raise RuntimeError(f"F3A packaged file checksum mismatch: {name}")
    stages.append({"stage": "f3a_finalize", "status": "PASS", "archive_sha256": EXPECTED["archive"], "members": len(entries)})
    result = {"mode": "cached_hash_verification", "verified_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "all_pass": True, "stages": stages,
              "limitation": "Does not regenerate E1 simulations; this is the cache mode allowed by F3-v1.1 section 4."}
    (OUT / "F3_reproduce_check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"F3A cached reproduction verification: PASS ({len(stages)} stages)")


if __name__ == "__main__":
    main()
