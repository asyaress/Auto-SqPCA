"""Re-aggregate archived case tables without rerunning the scientific pipeline."""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO.parents[1]
OUT = Path(__file__).resolve().parent


def rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def metrics(values: list[float]) -> dict:
    x = np.asarray(values, dtype=float)
    return {"n": len(x), "median": float(np.median(x)) if len(x) else None,
            "p90": float(np.percentile(x, 90)) if len(x) else None}


def write(path: Path, items: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(items[0])); writer.writeheader(); writer.writerows(items)


def main() -> None:
    sources = {
        "E1_truth": PROJECT / "phase3/work/E1_holdout_truth_status.csv",
        "E2_manifest": REPO / "phase3/F3_ssb_manifest.csv",
        "E2_holdout": PROJECT / "phase3/work/E2_holdout_cases.csv",
        "E2_development": PROJECT / "phase3/work/E2_development_cases.csv",
        "E3": REPO / "phase3/F3_E3_cases.csv",
        "U3": REPO / "phase3/audit_add/U3_full_pipeline_cases.csv",
        "U3_summary": REPO / "phase3/audit_add/U3_summary.csv",
        "U5": REPO / "phase3/audit_add/U5_band_coverage.csv",
    }
    data = {name: rows(path) for name, path in sources.items()}
    hashes = {name: {"project_relative_path": path.relative_to(PROJECT).as_posix(), "sha256": digest(path), "rows": len(data[name])}
              for name, path in sources.items()}
    e1_case_archive = REPO / "results/phase3/F3_E1_holdout_cases.csv.gz"
    e1_case_status = Counter()
    e1_case_count = 0
    with gzip.open(e1_case_archive, "rt", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            e1_case_count += 1
            e1_case_status[r["status"]] += 1
            assert r["station"] and r["year"] and r["month"] and r["component"]
            assert r["mask_kind"] and r["replicate"] and r["mask_seed"] and r["method"]
            assert r["p_nominal"] and r["p_actual"]
    assert e1_case_count == 555660
    hashes["E1_full_cases_gzip"] = {"project_relative_path": e1_case_archive.relative_to(PROJECT).as_posix(), "sha256": digest(e1_case_archive),
                                   "rows": e1_case_count}
    truth, manifest, holdout, development, e3 = (data[k] for k in
        ("E1_truth", "E2_manifest", "E2_holdout", "E2_development", "E3"))
    counts = Counter(r["status"] for r in truth)
    months = {(r["station"], r["year"], r["month"]) for r in truth}
    assert len(truth) == 447 and len(months) == 149 and counts == {"OK": 420, "UNRESOLVED_TRUTH": 27}, counts
    assert len(manifest) == 8748 and len(holdout) == 5616 and len(development) == 3132
    combined = {r["case_id"]: r for r in development + holdout}
    assert set(combined) == {r["case_id"] for r in manifest}
    assert len(e3) == 1068
    unmasked = [r for r in holdout if r["mask"] == "NONE"]
    assert len(unmasked) == 2808
    eligible = [r for r in unmasked if r["status"] == "OK" and r["AUTO_A1"] == "False"
                and float(r["observed_fraction"]) >= .9 and math.isfinite(float(r["AUTO_curve_error"]))]
    accepted = [r for r in eligible if float(r["stability"]) >= .5
                and float(r["relative_width"]) <= math.inf]
    assert len(accepted) == 2083, len(accepted)
    e3_accepted = [r for r in e3 if r["abstained"] == "False"]
    assert len(e3_accepted) == 830, len(e3_accepted)
    u3_counts = Counter((r["mask_kind"], r["p_nominal"], r["method"]) for r in data["U3"])
    # Every U3 summary row describes the same 420 truth slots at five replicates.
    for summary in data["U3_summary"]:
        key = summary["mask_kind"], summary["p_nominal"], summary["method"]
        assert u3_counts[key] == 2100, (key, u3_counts[key])
        assert int(summary["n_cases"]) == 2100
    u5_by_alpha: dict[str, list[dict]] = defaultdict(list)
    for r in data["U5"]:
        if r["record_type"] == "CASE": u5_by_alpha[r["alpha"]].append(r)
    u5_stats = {}
    u5_rng = np.random.default_rng(20261120)
    for alpha, part in sorted(u5_by_alpha.items()):
        by_month = defaultdict(list)
        for r in part: by_month[(r["station"], r["year"], r["month"])].append(r)
        groups = [by_month[k] for k in sorted(by_month)]
        draws = []
        for _ in range(2000):
            sampled = [r for i in u5_rng.integers(0, len(groups), size=len(groups)) for r in groups[i]]
            draws.append(sum(r["at_least_22_hours"] == "True" for r in sampled)/len(sampled))
        k = sum(r["at_least_22_hours"] == "True" for r in part)
        u5_stats[alpha] = {"cases": len(part), "at_least_22": k, "fraction": k/len(part),
                           "cluster_ci95": np.percentile(draws, [2.5, 97.5]).tolist(),
                           "clusters": len(groups)}
    manifest_rows = []
    for r in truth:
        manifest_rows.append({"stage": "E1", "case_id": "_".join((r["station"], r["year"], r["month"], r["component"])),
            "split": r["split"], "station": r["station"], "year": r["year"], "month": r["month"],
            "component": r["component"], "mask": "", "replicate": "", "seed": "",
            "included": r["status"] == "OK", "reason": r["error"], "decision": r["status"]})
    for r in manifest:
        case = combined[r["case_id"]]
        why = []
        if case["status"] != "OK": why.append("ERROR")
        if case["AUTO_A1"] == "True": why.append("A1")
        if float(case["stability"]) < .5: why.append("A2")
        if float(case["observed_fraction"]) < .9: why.append("A3")
        if float(case["relative_width"]) > math.inf: why.append("A4")
        manifest_rows.append({"stage": "E2", "case_id": r["case_id"], "split": r["split"],
            "station": r["station"], "year": r["year"], "month": r["month"],
            "component": r["component"], "mask": r["mask"], "replicate": r["replicate"],
            "seed": r["amplitude_seed"] + ";" + r["mask_seed"] + ";" + case["bootstrap_seed"],
            "included": not why, "reason": ";".join(why),
            "decision": "ACCEPT" if not why else "ABSTAIN"})
    for r in e3:
        manifest_rows.append({"stage": "E3", "case_id": "_".join((r["station"], r["year"], r["month"], r["component"])),
            "split": r["scope"], "station": r["station"], "year": r["year"], "month": r["month"],
            "component": r["component"], "mask": "OBSERVED", "replicate": "", "seed": "",
            "included": r["abstained"] == "False", "reason": r["abstain_reasons"] or r["error_original"],
            "decision": "ACCEPT" if r["abstained"] == "False" else "ABSTAIN"})
    write(OUT / "case_manifest.csv", manifest_rows)
    u3_mcar10 = next(r for r in data["U3_summary"] if r["mask_kind"] == "MCAR" and
        float(r["p_nominal"]) == .1 and r["method"] == "M-EM")
    result = {"verification_level": "ARCHIVED_CASE_REAGGREGATION", "source_files": hashes,
        "E1": {"station_months": len(months), "component_slots": len(truth), "truth_status": counts,
               "full_mask_method_cases": e1_case_count, "full_case_status_counts": dict(e1_case_status),
               "full_case_index": "results/phase3/F3_E1_holdout_cases.csv.gz (mask, replicate, seed, realized fraction, decision)",
               "unresolved_reason_counts": dict(Counter(r["error"] for r in truth if r["status"] != "OK"))},
        "E2": {"manifest_cases": len(manifest), "development": len(development), "holdout": len(holdout),
               "holdout_unmasked": len(unmasked), "upstream_eligible": len(eligible),
               "frozen_accepted": len(accepted), "coverage": len(accepted)/len(unmasked),
               "accepted_error": metrics([float(r["AUTO_curve_error"]) for r in accepted]),
               "A1_fail": sum(r["AUTO_A1"] == "True" for r in unmasked),
               "A2_fail": sum(float(r["stability"]) < .5 for r in unmasked)},
        "E3": {"cases": len(e3), "accepted": len(e3_accepted),
               "by_scope": {scope: {"cases": sum(r["scope"] == scope for r in e3),
                                    "accepted": sum(r["scope"] == scope and r["abstained"] == "False" for r in e3)}
                            for scope in sorted({r["scope"] for r in e3})},
               "status_counts": dict(Counter(r["status"] for r in e3))},
        "U3": {"settings": len(u3_counts), "cases_per_setting": 2100,
               "MCAR_10_M_EM_accepted_error_median": float(u3_mcar10["accepted_error_median"]),
               "MCAR_10_M_EM_round_3": f'{float(u3_mcar10["accepted_error_median"]):.3f}'},
        "U5": u5_stats}
    (OUT / "reconciliation.json").write_text(json.dumps(result, indent=2, default=dict), encoding="utf-8")
    print(json.dumps({k: v for k,v in result.items() if k != "source_files"}, indent=2, default=dict))


if __name__ == "__main__": main()
