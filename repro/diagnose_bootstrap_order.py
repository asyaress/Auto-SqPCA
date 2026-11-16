"""Audit E1 cluster-bootstrap order sensitivity without changing its evaluator."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


def clusters(path: Path):
    open_file = gzip.open if path.suffix == ".gz" else open
    groups = defaultdict(lambda: defaultdict(list))
    order = defaultdict(list)
    seen = defaultdict(set)
    with open_file(path, "rt", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["mask_kind"] not in ("MCAR", "BLOCK24", "DAY"):
                continue
            p = float(row["p_nominal"])
            if p not in (.20, .30, .40):
                continue
            setting = (row["mask_kind"], p)
            month = f"{row['station']}:{row['year']}-{int(row['month']):02d}"
            if month not in seen[setting]:
                order[setting].append(month)
                seen[setting].add(month)
            groups[(setting, month)][row["method"]].append(float(row["error_relative_l2"]))
    values = {}
    for key, methods in groups.items():
        values[key] = (float(np.median(methods["M-EM"])), float(np.median(methods["M-INT"])))
    return order, values


def main():
    parser = argparse.ArgumentParser()
    for name in ("original", "rerun", "original_superiority", "rerun_superiority", "output"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    old_order, old_values = clusters(args.original)
    new_order, new_values = clusters(args.rerun)
    with args.original_superiority.open(newline="", encoding="utf-8") as stream:
        old_summary = {(r["mask_kind"], float(r["p"])): r for r in csv.DictReader(stream)}
    with args.rerun_superiority.open(newline="", encoding="utf-8") as stream:
        new_summary = {(r["mask_kind"], float(r["p"])): r for r in csv.DictReader(stream)}
    result = []
    for setting in sorted(old_order):
        old_months, new_months = old_order[setting], new_order[setting]
        shared = set(old_months) & set(new_months)
        exact_median_pairs = sum(old_values[(setting, m)] == new_values[(setting, m)] for m in shared)
        a, b = old_summary[setting], new_summary[setting]
        result.append({
            "mask_kind": setting[0], "p": setting[1], "months_original": len(old_months),
            "months_rerun": len(new_months), "same_month_set": set(old_months) == set(new_months),
            "same_month_order": old_months == new_months,
            "exact_month_median_pairs": exact_median_pairs,
            "same_ratio": a["ratio"] == b["ratio"],
            "same_decision": a["better_real"] == b["better_real"],
            "ci_lower_original": float(a["ci_lower"]), "ci_lower_rerun": float(b["ci_lower"]),
            "ci_upper_original": float(a["ci_upper"]), "ci_upper_rerun": float(b["ci_upper"]),
        })
    output = {"source": "phase3/f3_e1_eval.py; seed 20261114; 2000 cluster resamples",
              "explanation": "The evaluator inserts months in case-CSV encounter order and applies fixed-seed integer draws to that array. A different worker completion order permutes the array and changes the finite bootstrap draw, without changing cases or cluster medians.",
              "settings": result,
              "max_absolute_CI_difference": max(abs(r[f"ci_{edge}_original"]-r[f"ci_{edge}_rerun"])
                                                for r in result for edge in ("lower", "upper")),
              "all_month_sets_and_medians_equal": all(r["same_month_set"] and
                                                  r["exact_month_median_pairs"] == r["months_original"] for r in result),
              "all_decisions_equal": all(r["same_ratio"] and r["same_decision"] for r in result)}
    args.output.write_text(json.dumps(output, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in output.items() if k != "settings"}, indent=2))
    if not result or not output["all_month_sets_and_medians_equal"] or not output["all_decisions_equal"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
