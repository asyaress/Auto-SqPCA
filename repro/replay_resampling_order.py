"""Replay frozen E1 and post-hoc random draws in their archived case order.

The script takes newly computed case values, independently verifies their
identities and relevant errors, then applies the archived order. It does not
edit the frozen evaluator, seed, source results, or manuscript tables.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def open_csv(path: Path):
    return gzip.open(path, "rt", newline="", encoding="utf-8") if path.suffix == ".gz" else path.open("r", newline="", encoding="utf-8")


def e1_clusters(path: Path):
    month_order = defaultdict(list)
    seen = defaultdict(set)
    groups = defaultdict(lambda: defaultdict(list))
    with open_csv(path) as stream:
        for row in csv.DictReader(stream):
            kind = row["mask_kind"]
            if kind not in ("MCAR", "BLOCK24", "DAY"):
                continue
            p = float(row["p_nominal"])
            if p not in (.20, .30, .40):
                continue
            setting = (kind, p)
            month = f"{row['station']}:{row['year']}-{int(row['month']):02d}"
            if month not in seen[setting]:
                month_order[setting].append(month)
                seen[setting].add(month)
            if row["method"] in ("M-EM", "M-INT"):
                groups[(setting, month)][row["method"]].append(float(row["error_relative_l2"]))
    median = {key: (float(np.median(methods["M-EM"])), float(np.median(methods["M-INT"])))
              for key, methods in groups.items()}
    return month_order, median


def replay_e1(args, out: Path):
    archived_order, old_median = e1_clusters(args.e1_archived)
    rerun_order, new_median = e1_clusters(args.e1_rerun)
    with args.e1_superiority.open(newline="", encoding="utf-8") as stream:
        reference = {(r["mask_kind"], float(r["p"])): r for r in csv.DictReader(stream)}
    rng = np.random.default_rng(20261114)
    results = []
    order_csv = out / "E1_archived_month_order.csv"
    with order_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("mask_kind", "p", "archived_ordinal", "month_key"))
        for kind in ("MCAR", "BLOCK24", "DAY"):
            for p in (.20, .30, .40):
                setting = kind, p
                order = archived_order[setting]
                if set(order) != set(rerun_order[setting]) or len(order) != 149:
                    raise RuntimeError(f"E1 month set mismatch: {setting}")
                if any(old_median[(setting, month)] != new_median[(setting, month)] for month in order):
                    raise RuntimeError(f"E1 month medians differ: {setting}")
                for ordinal, month in enumerate(order):
                    writer.writerow((kind, p, ordinal, month))
                array = np.array([new_median[(setting, month)] for month in order])
                base = float(np.median(array[:, 1]))
                ratio = float(np.median(array[:, 0]) / base)
                draws = []
                for _ in range(2000):
                    sample = array[rng.integers(0, len(array), size=len(array))]
                    denom = float(np.median(sample[:, 1]))
                    draws.append(float(np.median(sample[:, 0]) / denom) if denom > 0 else float("nan"))
                lower, upper = np.nanpercentile(draws, [2.5, 97.5])
                old = reference[setting]
                expected = float(old["ratio"]), float(old["ci_lower"]), float(old["ci_upper"])
                actual = ratio, float(lower), float(upper)
                results.append({"mask_kind": kind, "p": p, "months": len(order),
                                "archived_order_differs_from_rerun_order": order != rerun_order[setting],
                                "ratio": ratio, "ci_lower": float(lower), "ci_upper": float(upper),
                                "archived_ratio": expected[0], "archived_ci_lower": expected[1],
                                "archived_ci_upper": expected[2],
                                "max_absolute_difference": max(abs(x-y) for x, y in zip(expected, actual)),
                                "decision_matches": bool((upper < 1) == (old["better_real"] == "True"))})
    return {"archived_source_sha256": digest(args.e1_archived), "rerun_source_sha256": digest(args.e1_rerun),
            "archived_superiority_sha256": digest(args.e1_superiority),
            "order_file_sha256": digest(order_csv), "seed": 20261114, "resamples": 2000,
            "settings": results, "all_historical_values_exact": all(r["max_absolute_difference"] == 0 for r in results),
            "all_decisions_match": all(r["decision_matches"] for r in results)}


def replay_e2(args, out: Path):
    with args.e2_rerun.open(newline="", encoding="utf-8") as stream:
        rerun = {r["case_id"]: r for r in csv.DictReader(stream) if r["mask"] == "NONE"}
    with args.e2_ablation_cases.open(newline="", encoding="utf-8") as stream:
        archived = list(csv.DictReader(stream))
    if len(archived) != 2808 or set(r["case_id"] for r in archived) != set(rerun):
        raise RuntimeError("E2 unmasked case identity mismatch")
    eligible = [r for r in archived if r["eligible"] == "True"]
    if len(eligible) != 2561:
        raise RuntimeError(f"E2 eligible count differs: {len(eligible)}")
    errors = {}
    for row in eligible:
        case_id = row["case_id"]
        a = float(row["error"])
        b = float(rerun[case_id]["AUTO_curve_error"])
        if not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-12):
            raise RuntimeError(f"E2 error differs for {case_id}: archived={a} rerun={b}")
        errors[case_id] = b
    order_csv = out / "E2_archived_eligible_order.csv"
    with order_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("archived_ordinal", "case_id"))
        for ordinal, row in enumerate(eligible):
            writer.writerow((ordinal, row["case_id"]))
    rng = np.random.default_rng(20261116)
    ids = np.array([r["case_id"] for r in eligible])
    replay = []
    for replicate in range(1000):
        chosen = set(rng.choice(ids, size=2083, replace=False).tolist())
        values = np.asarray([errors[r["case_id"]] for r in eligible if r["case_id"] in chosen])
        replay.append({"replicate": replicate, "accepted": len(values),
                       "median": float(np.median(values)), "p90": float(np.percentile(values, 90))})
    with args.e2_random_replicates.open(newline="", encoding="utf-8") as stream:
        historical = list(csv.DictReader(stream))
    if len(historical) != len(replay):
        raise RuntimeError("E2 random replicate count mismatch")
    maximum = 0.0
    for old, new in zip(historical, replay):
        if int(old["replicate"]) != new["replicate"] or int(old["accepted"]) != new["accepted"]:
            raise RuntimeError(f"E2 random replicate identifier/count mismatch at {new['replicate']}")
        maximum = max(maximum, abs(float(old["median"])-new["median"]),
                      abs(float(old["p90"])-new["p90"]))
    median_of_medians = float(np.median([r["median"] for r in replay]))
    median_of_p90s = float(np.median([r["p90"] for r in replay]))
    return {"archived_ablation_cases_sha256": digest(args.e2_ablation_cases),
            "archived_random_replicates_sha256": digest(args.e2_random_replicates),
            "rerun_cases_sha256": digest(args.e2_rerun), "order_file_sha256": digest(order_csv),
            "seed": 20261116, "replicates": 1000, "eligible_cases": len(eligible),
            "accepted_per_draw": 2083, "max_absolute_replicate_difference": maximum,
            "historical_random_median_error": median_of_medians,
            "historical_random_p90_error": median_of_p90s,
            "all_historical_replicates_exact": maximum == 0}


def main():
    parser = argparse.ArgumentParser()
    for name in ("e1_archived", "e1_rerun", "e1_superiority", "e2_rerun",
                 "e2_ablation_cases", "e2_random_replicates", "output_dir"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = {"purpose": "Order-preserving replay of frozen results from independently rerun case values",
              "E1": replay_e1(args, args.output_dir),
              "E2_random_ablation": replay_e2(args, args.output_dir)}
    result["pass"] = result["E1"]["all_historical_values_exact"] and result["E1"]["all_decisions_match"] and result["E2_random_ablation"]["all_historical_replicates_exact"]
    target = args.output_dir / "resampling_order_replay.json"
    with target.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"pass": result["pass"], "E1_exact": result["E1"]["all_historical_values_exact"],
                      "E2_random_exact": result["E2_random_ablation"]["all_historical_replicates_exact"],
                      "random_median": result["E2_random_ablation"]["historical_random_median_error"],
                      "random_p90": result["E2_random_ablation"]["historical_random_p90_error"]}, indent=2))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
