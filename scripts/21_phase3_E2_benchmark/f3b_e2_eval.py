"""Frozen-rule E2 holdout C2/C3, masked stratum, and risk-coverage analysis."""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict

import numpy as np

from auto_sqpca.abstain import reasons
from f3_preflight import OUT, sha, verify_snapshot


def asfloat(s: str | float) -> float:
    return math.inf if str(s) == "INF" else float(s)


def monthkey(r: dict) -> tuple:
    return (r["station"], int(r["year"]), int(r["month"]))


def assess(r: dict, theta_s: float, theta_d: float, theta_w: float) -> list[str]:
    why = reasons(None if r["AUTO_A1"] == "True" else r["AUTO_candidate"],
                  float(r["stability"]), float(r["observed_fraction"]),
                  float(r["relative_width"]), theta_s, theta_d, theta_w)
    if r["status"] != "OK":
        why.append("ERROR")
    return why


def write_csv(name: str, rows: list[dict], fields: list[str]) -> None:
    with (OUT / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)


def main() -> None:
    verify_snapshot()
    frozen_path = OUT / "F3_E2_frozen.json"
    if sha(frozen_path) != (OUT / "F3_E2_frozen.json.sha256").read_text().split()[0]:
        raise RuntimeError("E2 frozen config hash mismatch")
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    if sha(OUT / "f3b_e2_eval.py") != frozen["E2_evaluator_code_sha256"]:
        raise RuntimeError("E2 holdout evaluator code changed after freeze")
    path = OUT / "work/E2_holdout_cases.csv"
    data = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    if len(data) != 5616 or any(r["split"] != "holdout" for r in data):
        raise RuntimeError(f"E2 holdout case count/split mismatch: {len(data)}")
    unmasked = [r for r in data if r["mask"] == "NONE"]
    masked = [r for r in data if r["mask"] == "MCAR20"]
    if len(unmasked) != len(masked) or len(unmasked) != 2808:
        raise RuntimeError("E2 holdout mask strata mismatch")
    theta_s, theta_d, theta_w = float(frozen["theta_s"]), float(frozen["theta_d"]), asfloat(frozen["theta_w"])
    if theta_d != .90:
        raise RuntimeError("E2 theta_d changed from F3-v1.1 A-1")
    if any(r["status"] != "OK" for r in data):
        bad = Counter(r["error_original"] for r in data if r["status"] != "OK")
        raise RuntimeError(f"E2 holdout contains case errors; C2/C3 unresolved: {dict(bad)}")
    if any(not np.isfinite(float(r[m])) for r in unmasked for m in ("ASAL_error", "AUTO_NA_error")):
        raise RuntimeError("E2 unmasked ASAL/AUTO-NA errors not finite; C2/C3 unresolved")
    by_comp = {}
    rng = np.random.default_rng(20261114)
    c2_rows = []
    for comp in "XYZ":
        subset = [r for r in unmasked if r["component"] == comp]
        by_month = defaultdict(list)
        for r in subset:
            by_month[monthkey(r)].append(float(r["ASAL_error"]) - float(r["AUTO_NA_error"]))
        keys = sorted(by_month)
        clusters = [np.asarray(by_month[k]) for k in keys]
        observed = float(np.median(np.concatenate(clusters)))
        draws = []
        for _ in range(2000):
            indices = rng.integers(0, len(clusters), size=len(clusters))
            draws.append(float(np.median(np.concatenate([clusters[i] for i in indices]))))
        lower, upper = np.percentile(draws, [2.5, 97.5])
        c2_rows.append({"component": comp, "months": len(clusters), "cases": len(subset),
                        "median_paired_ASAL_minus_AUTO_NA": observed,
                        "CI95_lower": float(lower), "CI95_upper": float(upper),
                        "C2_success_if_X": bool(lower > 0) if comp == "X" else "DESCRIPTIVE"})
    write_csv("F3_E2_C2.csv", c2_rows, list(c2_rows[0]))
    by_month = defaultdict(list)
    accepted_errors = []
    reason_counts = Counter()
    for r in unmasked:
        why = assess(r, theta_s, theta_d, theta_w)
        for a in why: reason_counts[a] += 1
        accepted = not why
        if accepted:
            accepted_errors.append(float(r["AUTO_curve_error"]))
        by_month[monthkey(r)].append((float(r["AUTO_NA_error"]), float(r["AUTO_curve_error"]), accepted))
    if any(not np.isfinite(x) for x in accepted_errors):
        raise RuntimeError("Accepted AUTO error nonfinite")
    coverage = len(accepted_errors) / len(unmasked)
    baseline_median = float(np.median([float(r["AUTO_NA_error"]) for r in unmasked]))
    accepted_median = float(np.median(accepted_errors)) if accepted_errors else None
    difference = baseline_median - accepted_median if accepted_median is not None else None
    clusters = [by_month[k] for k in sorted(by_month)]
    draws = []
    for _ in range(2000):
        sample = [clusters[i] for i in rng.integers(0, len(clusters), size=len(clusters))]
        flat = [x for cluster in sample for x in cluster]
        yes = [x[1] for x in flat if x[2]]
        draws.append(float(np.median([x[0] for x in flat]) - np.median(yes)) if yes else float("nan"))
    valid = np.asarray(draws)[np.isfinite(draws)]
    lower, upper = (float(x) for x in np.percentile(valid, [2.5, 97.5])) if len(valid) else (None, None)
    c3 = {"unmasked_cases": len(unmasked), "months": len(clusters), "accepted": len(accepted_errors),
          "coverage": coverage, "AUTO_NA_all_median_error": baseline_median,
          "AUTO_accepted_median_error": accepted_median, "median_error_difference": difference,
          "CI95_lower": lower, "CI95_upper": upper,
          "bootstrap_finite_draws": len(valid), "C3_success": bool(lower is not None and lower > 0 and coverage >= .80),
          "unmasked_reason_counts_overlapping": dict(reason_counts)}
    (OUT / "F3_E2_C3.json").write_text(json.dumps(c3, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    masked_reasons = Counter()
    masked_primary = Counter()
    masked_accepted = []
    for r in masked:
        why = assess(r, theta_s, theta_d, theta_w)
        for a in why: masked_reasons[a] += 1
        masked_primary[next((a for a in ("A1", "A2", "A3", "A4", "ERROR") if a in why), "ACCEPTED")] += 1
        if not why:
            masked_accepted.append(float(r["AUTO_curve_error"]))
    masked_report = {"cases": len(masked), "accepted": len(masked_accepted),
                     "abstain_fraction": 1 - len(masked_accepted) / len(masked),
                     "reason_counts_overlapping": dict(masked_reasons),
                     "primary_reason_counts_fixed_priority": dict(masked_primary),
                     "accepted_median_error": float(np.median(masked_accepted)) if masked_accepted else None,
                     "theta_d": theta_d}
    (OUT / "F3_E2_masked_stratum.json").write_text(json.dumps(masked_report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    risk = []
    for s in np.linspace(0, 1, 21):
        valid_errors = [float(r["AUTO_curve_error"]) for r in unmasked if not assess(r, float(s), theta_d, theta_w)]
        risk.append({"theta_s": float(s), "AUTO_coverage": len(valid_errors) / len(unmasked),
                     "AUTO_accepted_median_error": float(np.median(valid_errors)) if valid_errors else None,
                     "AUTO_NA_coverage": 1.0, "AUTO_NA_all_median_error": baseline_median})
    write_csv("F3_E2_risk_coverage.csv", risk, list(risk[0]))
    summary = {"E2_frozen_sha256": sha(frozen_path), "holdout_cases_sha256": sha(path),
               "theta_s": theta_s, "theta_w": frozen["theta_w"], "theta_d": theta_d,
               "C2_X_success": c2_rows[0]["C2_success_if_X"], "C3_success": c3["C3_success"],
               "unmasked_coverage": coverage, "masked_abstain_fraction": masked_report["abstain_fraction"],
               "C2_CI_resamples": 2000, "C3_CI_resamples": 2000,
               "analysis_code_sha256": sha(OUT / "f3b_e2_eval.py")}
    (OUT / "F3_E2_result.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"E2 holdout: C2={summary['C2_X_success']} C3={summary['C3_success']} coverage={coverage:.4f} masked abstain={masked_report['abstain_fraction']:.4f}")
    verify_snapshot()


if __name__ == "__main__":
    main()
