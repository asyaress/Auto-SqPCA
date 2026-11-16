"""Select and freeze E2 abstention thresholds from unmasked development cases."""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
from pathlib import Path

import numpy as np

from auto_sqpca.abstain import reasons
from f3_preflight import OUT, sha, verify_snapshot

GRID_S = (.5, .6, .7, .8, .9)
GRID_W = (.25, .5, 1.0, math.inf)
THETA_D = .90


def main() -> None:
    verify_snapshot()
    if (OUT / "work/E2_holdout_cases.csv").exists():
        raise RuntimeError("Holdout cases exist before E2 freeze")
    source = OUT / "work/E2_development_cases.csv"
    cases = list(csv.DictReader(source.open(encoding="utf-8", newline="")))
    unmasked = [r for r in cases if r["mask"] == "NONE"]
    if not cases or len(unmasked) * 2 != len(cases):
        raise RuntimeError("E2 development cases missing or mask strata not balanced")
    grid = []
    for theta_s in GRID_S:
        for theta_w in GRID_W:
            accepted = []
            reason_counts = {a: 0 for a in ("A1", "A2", "A3", "A4")}
            for r in unmasked:
                why = reasons(None if r["AUTO_A1"] == "True" else r["AUTO_candidate"],
                              float(r["stability"]), float(r["observed_fraction"]),
                              float(r["relative_width"]), theta_s, THETA_D, theta_w)
                if r["status"] != "OK":
                    why.append("ERROR")
                for a in reason_counts:
                    reason_counts[a] += a in why
                if not why:
                    accepted.append(float(r["AUTO_curve_error"]))
            coverage = len(accepted) / len(unmasked)
            median = float(np.median(accepted)) if accepted else float("inf")
            grid.append({"theta_s": theta_s, "theta_w": "INF" if math.isinf(theta_w) else theta_w,
                         "theta_d": THETA_D, "unmasked_cases": len(unmasked),
                         "accepted": len(accepted), "coverage": coverage,
                         "accepted_median_error": median,
                         **{f"reason_{a}_count": reason_counts[a] for a in reason_counts}})
    fields = list(grid[0])
    with (OUT / "F3_E2_development_grid.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(grid)
    feasible = [r for r in grid if r["coverage"] >= .8]
    if feasible:
        chosen = min(feasible, key=lambda r: (r["accepted_median_error"], -r["coverage"], r["theta_s"],
                                              GRID_W.index(math.inf if r["theta_w"] == "INF" else r["theta_w"])))
        rule = "minimum accepted median error among coverage>=0.80; tie higher coverage"
    else:
        chosen = min(grid, key=lambda r: (-r["coverage"], r["accepted_median_error"], r["theta_s"],
                                          GRID_W.index(math.inf if r["theta_w"] == "INF" else r["theta_w"])))
        rule = "F3-v1.1 A-4: maximum coverage, tie minimum accepted median error; C3 still fails if holdout coverage<0.80"
    freeze = {"created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "theta_s": chosen["theta_s"], "theta_w": chosen["theta_w"], "theta_d": THETA_D,
              "development_unmasked_coverage": chosen["coverage"],
              "development_unmasked_accepted_median_error": chosen["accepted_median_error"] if math.isfinite(chosen["accepted_median_error"]) else None,
              "selection_rule": rule, "feasible_grid_points": len(feasible),
              "grid_s": GRID_S, "grid_w": ["INF" if math.isinf(x) else x for x in GRID_W],
              "primary_stratum": "NONE", "masked_stratum": "MCAR20 descriptive only",
              "bootstrap_B": 200, "seed": 20261114, "E1_method": "M-EM",
              "E1_frozen_sha256": sha(OUT / "F3_E1_frozen.json"),
              "protocol_sha256": sha(OUT / "F3_protocol_v1.md"),
              "amendment_sha256": sha(OUT / "F3_amendment_v1.1.md"),
              "SSB_manifest_sha256": sha(OUT / "F3_ssb_manifest.csv"),
              "E2_case_code_sha256": sha(OUT / "f3b_e2_cases.py"),
              "E2_evaluator_code_sha256": sha(OUT / "f3b_e2_eval.py"),
              "E2_zero_code_sha256": sha(OUT / "f3b_e2_zero.py"),
              "E2_development_cases_sha256": sha(source),
              "E2_development_grid_sha256": sha(OUT / "F3_E2_development_grid.csv"),
              "E2_development_selection_code_sha256": sha(OUT / "f3b_e2_develop.py")}
    path = OUT / "F3_E2_frozen.json"
    if path.exists():
        raise RuntimeError("E2 frozen config already exists; refusing overwrite")
    path.write_text(json.dumps(freeze, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (OUT / "F3_E2_frozen.json.sha256").write_text(f"{sha(path)}  F3_E2_frozen.json\n", encoding="ascii")
    print(f"E2 frozen theta_s={chosen['theta_s']} theta_w={chosen['theta_w']} theta_d={THETA_D}, development coverage={chosen['coverage']:.4f}")
    verify_snapshot()


if __name__ == "__main__":
    main()
