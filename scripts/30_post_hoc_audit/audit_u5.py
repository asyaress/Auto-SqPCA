"""Exploratory pointwise bootstrap-band coverage on frozen E2 holdout cases."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np

HERE = Path(__file__).resolve().parent
PHASE3 = HERE.parent
ROOT = PHASE3.parent
sys.path.insert(0, str(PHASE3))

from auto_sqpca import gaps, pca, selection, ssb
from classification_core import random_phase_surrogates
from f3b_e2_cases import quiet_days
from f3b_e2_eval import assess


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def bootstrap_band(a: np.ndarray, reference: np.ndarray, selected: str | None,
                   surrogates: np.ndarray, case_seed: int) -> dict:
    """Identical bootstrap loop and RNG to f3b_e2_cases.bootstrap_fast; keep band."""
    rng = np.random.default_rng(case_seed)
    labels, curves = [], []
    for _ in range(200):
        indices = rng.integers(0, a.shape[1], size=a.shape[1])
        result = selection.choose(pca.decompose_v1(a[:, indices]), reference, surrogates)
        labels.append(result["selected"])
        if result["curve"] is not None:
            curves.append(result["curve"])
    stability = sum(label == selected for label in labels) / 200
    if not curves:
        raise RuntimeError("Bootstrap produced no curves")
    lo, hi = np.percentile(np.stack(curves), [5, 95], axis=0)
    return {"stability": stability, "successful": len(curves), "band_low": lo,
            "band_high": hi, "median_width_nT": float(np.median(hi-lo))}


def process_month(items: list[tuple[dict, dict]]) -> list[dict]:
    first = items[0][0]
    cache = ROOT / first["cache_path"]
    if sha(cache) != first["cache_sha256"]:
        raise RuntimeError(f"U5 source cache SHA-256 mismatch: {cache}")
    with np.load(cache, allow_pickle=False) as z:
        residual, true_matrix = z["residual_nT"], z["DIFI8_sq_true_nT"]
    days = quiet_days(first)
    output = []
    for manifest, recorded in items:
        comp = "XYZ".index(manifest["component"])
        true = true_matrix[:, comp]
        alpha = float(manifest["alpha"])
        y, _ = ssb.generate(residual[:, :, comp], true, alpha, int(manifest["amplitude_seed"]))
        filled, keep, _ = gaps.apply(y, "M-EM")
        if not keep.all() or filled.shape != y.shape or not np.isfinite(filled).all():
            raise RuntimeError(f"U5 invalid reconstructed matrix: {manifest['case_id']}")
        reference = selection.sq_iqd(filled, days)
        surrogates = random_phase_surrogates(reference)
        chosen = selection.choose(pca.decompose_v1(filled), reference, surrogates)
        band = bootstrap_band(filled, reference, chosen["selected"], surrogates,
                              int(recorded["bootstrap_seed"]))
        if chosen["selected"] != (recorded["AUTO_candidate"] or None) or \
           band["stability"] != float(recorded["stability"]) or \
           band["successful"] != int(recorded["bootstrap_successful"]):
            raise RuntimeError(f"U5 candidate/stability/bootstrap verification mismatch: {manifest['case_id']}")
        target = alpha * true
        inside = (target >= band["band_low"]) & (target <= band["band_high"])
        output.append({"audit_label": "EXPLORATORY_POST_HOC", "record_type": "CASE",
                       "case_id": manifest["case_id"], "station": manifest["station"],
                       "year": manifest["year"], "month": manifest["month"],
                       "component": manifest["component"], "alpha": alpha,
                       "hours_covered": int(inside.sum()), "fraction_hours_covered": float(inside.mean()),
                       "at_least_22_hours": bool(inside.sum() >= 22),
                       "median_band_width_nT": band["median_width_nT"],
                       "candidate_verified": True, "stability_verified": True})
    return output


def main() -> None:
    config = json.loads((PHASE3 / "F3_E2_frozen.json").read_text(encoding="utf-8"))
    assert config["theta_s"] == .5 and config["theta_d"] == .9 and config["theta_w"] == "INF"
    manifest_path = PHASE3 / "F3_ssb_manifest.csv"
    assert sha(manifest_path) == config["SSB_manifest_sha256"]
    cases_path = PHASE3 / "work/E2_holdout_cases.csv"
    e2 = json.loads((PHASE3 / "F3_E2_result.json").read_text(encoding="utf-8"))
    assert sha(cases_path) == e2["holdout_cases_sha256"]
    manifest = {r["case_id"]: r for r in read_csv(manifest_path) if r["split"] == "holdout"}
    cases = read_csv(cases_path)
    accepted = [r for r in cases if r["split"] == "holdout" and r["mask"] == "NONE" and
                not assess(r, config["theta_s"], config["theta_d"], float("inf"))]
    grouped = defaultdict(list)
    for r in accepted:
        m = manifest[r["case_id"]]
        grouped[(r["station"], r["year"], r["month"])].append((m, r))
    # Independent 20-case gate before any full-run output is written.
    pilot = []
    pilot_keys = sorted(grouped)[:20]
    for key in pilot_keys:
        pilot.extend(process_month([grouped[key][0]]))
    if len(pilot) != 20 or not all(r["candidate_verified"] and r["stability_verified"] for r in pilot):
        raise RuntimeError("U5 20-case verification incomplete")
    print("U5 20-case candidate/stability gate matched", flush=True)
    all_rows = []
    with ProcessPoolExecutor(max_workers=min(6, os.cpu_count() or 1)) as pool:
        futures = {pool.submit(process_month, group): key for key, group in grouped.items()}
        for n, f in enumerate(as_completed(futures), 1):
            key = futures[f]
            try:
                all_rows.extend(f.result())
            except Exception as e:
                raise RuntimeError(f"U5 month {key}: {type(e).__name__}: {e}") from e
            if n % 10 == 0 or n == len(futures):
                print(f"U5 months {n}/{len(futures)}, cases {len(all_rows)}/{len(accepted)}", flush=True)
    if len(all_rows) != len(accepted):
        raise RuntimeError("U5 accepted case count mismatch")
    summary = []
    for comp in "XYZ":
        for alpha in (.5, 1.0, 2.0):
            subset = [r for r in all_rows if r["component"] == comp and r["alpha"] == alpha]
            summary.append({"audit_label": "EXPLORATORY_POST_HOC", "record_type": "SUMMARY",
                            "case_id": "", "station": "ALL", "year": "", "month": "",
                            "component": comp, "alpha": alpha, "n_cases": len(subset),
                            "mean_fraction_hours_covered": float(np.mean([r["fraction_hours_covered"] for r in subset])) if subset else "",
                            "fraction_cases_at_least_22_hours": float(np.mean([r["at_least_22_hours"] for r in subset])) if subset else "",
                            "median_band_width_nT": float(np.median([r["median_band_width_nT"] for r in subset])) if subset else ""})
    fields = ["audit_label", "record_type", "case_id", "station", "year", "month", "component", "alpha",
              "hours_covered", "fraction_hours_covered", "at_least_22_hours", "median_band_width_nT",
              "candidate_verified", "stability_verified", "n_cases", "mean_fraction_hours_covered",
              "fraction_cases_at_least_22_hours"]
    with (HERE / "U5_band_coverage.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(sorted(all_rows, key=lambda r: r["case_id"]))
        w.writerows(summary)
    (HERE / "U5_verification.json").write_text(json.dumps({"audit_label": "EXPLORATORY_POST_HOC",
        "pilot_cases": 20, "pilot_matched": True, "accepted_cases": len(accepted),
        "source_cases_sha256": sha(cases_path), "source_manifest_sha256": sha(manifest_path),
        "note": "Pointwise bands conditional on filled matrix and IQD reference; not nominal confidence intervals."}, indent=2) + "\n", encoding="utf-8")
    print(f"U5 complete: {len(all_rows)} cases", flush=True)


if __name__ == "__main__":
    main()
