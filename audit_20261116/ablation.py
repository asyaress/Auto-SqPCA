"""Post hoc matched-acceptance ablation from frozen E2 case/cached inputs."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO.parents[1]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "phase3"))
from auto_sqpca import candidates, gaps, metrics, pca, selection, ssb  # noqa: E402

def quiet_days(row: dict) -> list[int]:
    path = PROJECT / row["GFZ_IQD_path"]
    assert sha(path) == row["GFZ_IQD_sha256"], path
    month = int(row["month"])
    month_name = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")[month-1]
    line = next(x for x in path.read_text(encoding="utf-8").splitlines()
                if re.match(rf"^\s*{month_name}\s+{row['year']}\s", x))
    return [int(re.match(r"^\d+", x).group()) for x in line.split()[2:7]]


def read(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f: return list(csv.DictReader(f))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def risk(rows: list[dict], selected: set[str]) -> dict:
    x = np.asarray([float(r["AUTO_curve_error"]) for r in rows if r["case_id"] in selected])
    return {"accepted": len(x), "median": float(np.median(x)),
            "p90": float(np.percentile(x, 90))}


def main() -> None:
    cases = [r for r in read(PROJECT / "phase3/work/E2_holdout_cases.csv") if r["mask"] == "NONE"]
    manifest = {r["case_id"]: r for r in read(REPO / "phase3/F3_ssb_manifest.csv")}
    eligible = [r for r in cases if r["status"] == "OK" and r["AUTO_A1"] == "False"
                and float(r["observed_fraction"]) >= .9 and math.isfinite(float(r["AUTO_curve_error"]))]
    full = {r["case_id"] for r in eligible if float(r["stability"]) >= .5}
    assert len(cases) == 2808 and len(eligible) == 2561 and len(full) == 2083
    scores_path = OUT / "ablation_scores.csv"
    scored = {r["case_id"]: r for r in read(scores_path)} if scores_path.exists() else {}
    for r in eligible:
        if r["case_id"] in scored:
            score = scored[r["case_id"]]
            assert abs(float(score["recomputed_error"])-float(r["AUTO_curve_error"])) < 1e-10
            assert 0 <= float(score["abs_r"]) <= 1
    cache_refs = {m["cache_path"]: m["cache_sha256"] for m in (manifest[r["case_id"]] for r in eligible)}
    for path, expected in cache_refs.items(): assert sha(PROJECT / path) == expected, path
    by_month = defaultdict(list)
    for r in eligible:
        if r["case_id"] not in scored:
            m = manifest[r["case_id"]]
            by_month[(m["station"], m["year"], m["month"])].append((r, m))
    for month_index, items in enumerate(by_month.values(), 1):
        first = items[0][1]
        path = PROJECT / first["cache_path"]
        assert sha(path) == first["cache_sha256"], path
        z = np.load(path, allow_pickle=False)
        residual, truth = z["residual_nT"], z["DIFI8_sq_true_nT"]
        days = quiet_days(first)
        for archived, m in items:
            comp = "XYZ".index(m["component"])
            y, _ = ssb.generate(residual[:, :, comp], truth[:, comp], float(m["alpha"]), int(m["amplitude_seed"]))
            filled, keep, _ = gaps.apply(y, "M-EM")
            assert keep.all() and np.isfinite(filled).all()
            ref = selection.sq_iqd(filled, days)
            candidate = candidates.curves(pca.decompose_v1(filled))[archived["AUTO_candidate"]]
            correlation = abs(float(np.corrcoef(candidate, ref)[0, 1]))
            error = metrics.relative_l2(candidate, float(m["alpha"]) * truth[:, comp])
            assert abs(error - float(archived["AUTO_curve_error"])) < 1e-10, (m["case_id"], error)
            scored[m["case_id"]] = {"case_id": m["case_id"], "abs_r": correlation,
                                    "recomputed_error": error}
        if month_index % 10 == 0:
            write(scores_path, list(scored.values()))
            print(f"scored months {month_index}/{len(by_month)}", flush=True)
    assert len(scored) == len(eligible)
    write(scores_path, list(scored.values()))

    count = len(full)
    ranked_corr = sorted(eligible, key=lambda r: (-float(scored[r["case_id"]]["abs_r"]), r["case_id"]))
    corr = {r["case_id"] for r in ranked_corr[:count]}
    rng = np.random.default_rng(20261116)
    eligible_ids = np.asarray([r["case_id"] for r in eligible])
    random_stats = []
    for replicate in range(1000):
        subset = set(rng.choice(eligible_ids, size=count, replace=False).tolist())
        random_stats.append({"replicate": replicate, **risk(eligible, subset)})
    write(OUT / "ablation_random_replicates.csv", random_stats)

    case_out = []
    for r in cases:
        case_out.append({"case_id": r["case_id"], "station": r["station"], "year": r["year"],
            "month": r["month"], "component": r["component"], "alpha": r["alpha"],
            "eligible": r in eligible, "A1_fail": r["AUTO_A1"] == "True",
            "observed_fraction": r["observed_fraction"], "stability": r["stability"],
            "abs_r": scored[r["case_id"]]["abs_r"] if r["case_id"] in scored else "",
            "error": r["AUTO_curve_error"], "full_accept": r["case_id"] in full,
            "no_A2_accept": r in eligible, "correlation_matched_accept": r["case_id"] in corr})
    write(OUT / "ablation_cases.csv", case_out)

    # Paired cluster bootstrap, resampling station-year-month with all its cases.
    clusters = defaultdict(list)
    for r in eligible: clusters[(r["station"], r["year"], r["month"])].append(r)
    cluster_list = [clusters[k] for k in sorted(clusters)]
    ci_rng = np.random.default_rng(20261117)
    differences = []
    for _ in range(2000):
        indices = ci_rng.integers(0, len(cluster_list), size=len(cluster_list))
        boot = [r for i in indices for r in cluster_list[i]]
        a = risk(boot, full); b = risk(boot, corr)
        boot_full_errors = np.asarray([float(r["AUTO_curve_error"]) for r in boot if r["case_id"] in full])
        random_index = ci_rng.choice(len(boot), size=len(boot_full_errors), replace=False)
        random_errors = np.asarray([float(boot[i]["AUTO_curve_error"]) for i in random_index])
        differences.append({"median_full_minus_corr": a["median"]-b["median"],
                            "p90_full_minus_corr": a["p90"]-b["p90"],
                            "median_full_minus_random": float(np.median(boot_full_errors)-np.median(random_errors)),
                            "p90_full_minus_random": float(np.percentile(boot_full_errors,90)-np.percentile(random_errors,90))})
    write(OUT / "ablation_cluster_bootstrap.csv", differences)
    curve = []
    for size in sorted(set([round(len(eligible)*p) for p in np.linspace(.1, 1, 19)] + [count])):
        for name, ranking in (("stability", sorted(eligible, key=lambda r: (-float(r["stability"]), r["case_id"]))),
                              ("correlation", ranked_corr)):
            chosen = {r["case_id"] for r in ranking[:size]}
            curve.append({"ranking": name, "accepted": size, "coverage_all": size/len(cases),
                          **{k:v for k,v in risk(eligible, chosen).items() if k != "accepted"}})
        random_risks = []
        for _ in range(100):
            chosen = set(rng.choice(eligible_ids, size=size, replace=False).tolist())
            random_risks.append(risk(eligible, chosen))
        curve.append({"ranking": "random_mean_100", "accepted": size, "coverage_all": size/len(cases),
                      "median": float(np.mean([x["median"] for x in random_risks])),
                      "p90": float(np.mean([x["p90"] for x in random_risks]))})
    write(OUT / "ablation_risk_coverage.csv", curve)
    summary = {"label": "POST_HOC", "source_sha256": {
            "cases": sha(PROJECT / "phase3/work/E2_holdout_cases.csv"),
            "manifest": sha(REPO / "phase3/F3_ssb_manifest.csv")},
        "n_all_unmasked": len(cases), "n_upstream_eligible": len(eligible),
        "n_A1_fail": sum(r["AUTO_A1"] == "True" for r in cases),
        "frozen_full": risk(eligible, full), "no_A2_native": risk(eligible, set(eligible_ids)),
        "correlation_matched": risk(eligible, corr),
        "random_matched": {"replicates": len(random_stats),
            "median_error_median": float(np.median([r["median"] for r in random_stats])),
            "median_error_interval95": np.percentile([r["median"] for r in random_stats], [2.5, 97.5]).tolist(),
            "p90_error_median": float(np.median([r["p90"] for r in random_stats])),
            "p90_error_interval95": np.percentile([r["p90"] for r in random_stats], [2.5, 97.5]).tolist()},
        "cluster_bootstrap_full_minus_corr": {metric: np.percentile([r[metric] for r in differences], [2.5,97.5]).tolist()
            for metric in differences[0]},
        "correlation_cutoff_descriptive": float(scored[ranked_corr[count-1]["case_id"]]["abs_r"])}
    (OUT / "ablation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__": main()
