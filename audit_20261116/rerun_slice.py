"""Targeted frozen E2 case rerun from authenticated SSB month cache, no writes to Phase 3."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO.parents[1]
sys.path.insert(0, str(PROJECT / "phase3"))
sys.path.insert(0, str(PROJECT / "phase2a/G4R"))
from f3b_e2_cases import process_month  # noqa: E402

OUT = Path(__file__).resolve().parent


def read(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f: return list(csv.DictReader(f))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    assert sha(PROJECT / "phase3/f3b_e2_cases.py") == sha(REPO / "phase3/f3b_e2_cases.py")
    chosen = [r for r in read(REPO / "phase3/F3_ssb_manifest.csv")
              if r["station"] == "GUA" and r["year"] == "2014" and r["month"] == "1"]
    assert len(chosen) == 54
    rerun = process_month(chosen)
    original = {r["case_id"]: r for r in read(PROJECT / "phase3/work/E2_holdout_cases.csv")}
    fields = ["status", "AUTO_A1", "AUTO_candidate", "AUTO_NA_candidate", "ASAL_candidate",
              "observed_fraction", "stability", "relative_width", "AUTO_curve_error",
              "AUTO_NA_error", "ASAL_error", "M_EM_iterations", "M_EM_final_change_nT",
              "bootstrap_successful", "bootstrap_seed"]
    differences = []
    for r in rerun:
        old = original[r["case_id"]]
        for field in fields:
            x, y = str(r[field]), old[field]
            try:
                a, b = float(x), float(y)
                equal = (math.isnan(a) and math.isnan(b)) or a == b or abs(a-b) <= 1e-12
            except ValueError:
                equal = x == y
            if not equal: differences.append({"case_id": r["case_id"], "field": field,
                                              "archived": y, "rerun": x})
    result = {"verification_level": "TARGETED_DERIVED_INPUT_RERUN", "month": "GUA 2014-01",
        "cases": len(chosen), "fields_checked": fields, "mismatches": len(differences),
        "source_script_sha256": sha(PROJECT / "phase3/f3b_e2_cases.py"),
        "source_cache_sha256": chosen[0]["cache_sha256"], "difference_details": differences}
    (OUT / "rerun_slice.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    assert not differences


if __name__ == "__main__": main()
