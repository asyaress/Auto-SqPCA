"""Descriptive E1 secondary metrics from the immutable corrected holdout CSV."""
from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from f3_preflight import OUT, sha, verify_snapshot

EXPECTED = "1acbda1a8825b6b878704395973fea0c37b4fd1324ee470df106f2344d1aceb3"
FIELDS = ("method", "mask_kind", "p_nominal", "cases", "ok_cases", "no_output_cases",
          "fixed_error_finite_n", "fixed_error_median", "fixed_error_p90",
          "pc1_angle_finite_n", "pc1_angle_median_deg", "pc1_angle_p90_deg",
          "candidate_agree_all_fraction", "candidate_agree_ok_fraction")


def finite_stats(values: list[float]) -> tuple[int, float | None, float | None]:
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    if not len(a):
        return 0, None, None
    return len(a), float(np.median(a)), float(np.quantile(a, .9))


def main() -> None:
    verify_snapshot()
    path = OUT / "work/E1_holdout_cases.csv"
    if sha(path) != EXPECTED:
        raise RuntimeError("Frozen corrected E1 holdout CSV SHA-256 mismatch")
    groups = defaultdict(lambda: {"fixed": [], "angle": [], "ok": 0, "agree_all": 0, "agree_ok": 0, "n": 0})
    capped = []
    em_total = 0
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            g = groups[(row["method"], row["mask_kind"], row["p_nominal"])]
            g["n"] += 1
            ok = row["status"] == "OK"
            agree = row["candidate_agree"] == "True"
            g["ok"] += ok
            g["agree_all"] += agree
            g["agree_ok"] += ok and agree
            g["fixed"].append(float(row["fixed_candidate_error"]))
            g["angle"].append(float(row["pc1_angle_deg"]))
            if row["method"] == "M-EM":
                em_total += 1
                if int(row["em_iterations"]) >= 500:
                    capped.append(float(row["em_final_change_nT"]))
    rows = []
    for (method, kind, p), g in sorted(groups.items()):
        nf, mf, pf = finite_stats(g["fixed"])
        na, ma, pa = finite_stats(g["angle"])
        rows.append(dict(zip(FIELDS, (method, kind, p, g["n"], g["ok"], g["n"] - g["ok"],
                                     nf, mf, pf, na, ma, pa,
                                     g["agree_all"] / g["n"],
                                     g["agree_ok"] / g["ok"] if g["ok"] else None))))
    out = OUT / "F3_E1_secondary_metrics.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader(); writer.writerows(rows)
    a = np.asarray(capped, dtype=float)
    report = {"source_path": path.relative_to(OUT).as_posix(), "source_sha256": EXPECTED,
              "methods_and_mask_settings": len(rows), "M_EM_cases": em_total,
              "M_EM_reached_500_iterations": len(a),
              "capped_fraction_of_M_EM": len(a) / em_total,
              "capped_final_change_finite": int(np.isfinite(a).sum()),
              "capped_below_1e-4_nT": int((a < 1e-4).sum()),
              "capped_below_1e-4_fraction": float((a < 1e-4).mean()),
              "capped_below_1e-6_nT": int((a < 1e-6).sum()),
              "capped_below_1e-6_fraction": float((a < 1e-6).mean()),
              "capped_final_change_quantiles_nT": {str(q): float(np.quantile(a, q)) for q in (0, .25, .5, .75, .9, .99, 1)},
              "denominator_note": "All E1 method cases in secondary table; finite metrics exclude nonfinite values and report count. Capped EM fractions use all cases at 500 iterations."}
    (OUT / "F3_E1_convergence.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"E1 secondary: {len(rows)} settings; M-EM capped {len(a)}/{em_total}")
    verify_snapshot()


if __name__ == "__main__":
    main()
