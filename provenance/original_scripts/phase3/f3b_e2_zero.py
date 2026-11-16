"""Descriptive E2 holdout abstention on alpha=0 residual-only SSB cases."""
from __future__ import annotations

import csv
import json
import math
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from f3b_e2_cases import MANIFEST, OUT, process_month, seed
from f3b_e2_eval import assess, asfloat
from f3_preflight import sha, verify_snapshot


def main() -> None:
    verify_snapshot()
    frozen = json.loads((OUT / "F3_E2_frozen.json").read_text(encoding="utf-8"))
    if sha(OUT / "f3b_e2_zero.py") != frozen["E2_zero_code_sha256"]:
        raise RuntimeError("Alpha-zero code changed after E2 freeze")
    source = list(csv.DictReader(MANIFEST.open(encoding="utf-8", newline="")))
    source = [r for r in source if r["split"] == "holdout" and r["alpha"] == "1" and r["mask"] == "NONE" and r["replicate"] == "0"]
    if len(source) != 104 * 3:
        raise RuntimeError(f"Expected 312 alpha-zero source components, got {len(source)}")
    cases = []
    for r in source:
        x = r.copy()
        x["case_id"] = f"{r['station']}_{r['year']}_{int(r['month']):02d}_{r['component']}_a0_NONE_r0"
        x["alpha"] = "0"
        x["amplitude_seed"] = seed(x["case_id"], "amplitude")
        x["mask_seed"] = seed(x["case_id"], "mask")
        cases.append(x)
    rows = []
    with ProcessPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(process_month, [r]) for r in cases]
        for future in as_completed(futures):
            rows.extend(future.result())
    if len(rows) != len(cases):
        raise RuntimeError("Alpha-zero result count mismatch")
    theta_s, theta_d, theta_w = float(frozen["theta_s"]), float(frozen["theta_d"]), asfloat(frozen["theta_w"])
    reasons = Counter()
    accepted = 0
    out = []
    for r in rows:
        why = assess(r, theta_s, theta_d, theta_w)
        accepted += not why
        for a in why: reasons[a] += 1
        out.append({"case_id": r["case_id"], "station": r["station"], "component": r["component"],
                    "status": r["status"], "error_original": r["error_original"],
                    "selected": r["AUTO_candidate"], "stability": r["stability"],
                    "relative_width": r["relative_width"], "reasons": ";".join(why), "abstained": bool(why)})
    fields = list(out[0])
    with (OUT / "F3_E2_alpha0_cases.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(out)
    result = {"cases": len(rows), "accepted": accepted, "abstained": len(rows) - accepted,
              "abstain_fraction": (len(rows) - accepted) / len(rows),
              "reason_counts_overlapping": dict(reasons), "case_csv_sha256": sha(OUT / "F3_E2_alpha0_cases.csv"),
              "note": "Alpha=0 uses original monthly residual R only; this residual still contains real Sq variability by SSB construction."}
    (OUT / "F3_E2_alpha0.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"E2 alpha=0: abstain {len(rows)-accepted}/{len(rows)}")
    verify_snapshot()


if __name__ == "__main__":
    main()
