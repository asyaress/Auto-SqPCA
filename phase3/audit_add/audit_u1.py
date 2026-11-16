"""Exploratory cap-500 versus cap-5000 sensitivity; frozen inputs are read-only."""
from __future__ import annotations

import csv
import hashlib
import json
import math
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

from auto_sqpca import gaps, metrics, pca, selection
from classification_core import random_phase_surrogates
from f3_e1 import gfz_days, make_mask
from f3b_e2_cases import bootstrap_fast, seed
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


def write_csv(path: Path, data: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(data)


def fill_em_cap(a: np.ndarray, cap: int, checkpoint_at: int | None = None):
    """Same arithmetic and stop condition as gaps.fill_em, with variable cap.

    Optional checkpoint captures iteration 500 without changing the algorithm.
    """
    a = np.asarray(a, dtype=float)
    keep = np.isfinite(a).sum(axis=0) >= 6
    out = a[:, keep].copy()
    if not out.size:
        return out, keep, 0, 0.0, None
    missing = ~np.isfinite(out)
    if not missing.any():
        return out, keep, 0, 0.0, None
    means = np.nanmean(out, axis=0)
    out[missing] = np.broadcast_to(means, out.shape)[missing]
    change = float("inf")
    checkpoint = None
    for iteration in range(1, cap + 1):
        day_mean = out.mean(axis=0, keepdims=True)
        centered = out - day_mean
        u, s, vh = np.linalg.svd(centered, full_matrices=False)
        reconstructed = (u[:, :3] * s[:3]) @ vh[:3] + day_mean
        change = float(np.max(np.abs(reconstructed[missing] - out[missing])))
        out[missing] = reconstructed[missing]
        if iteration == checkpoint_at:
            checkpoint = (out.copy(), iteration, change)
        if change < 1e-4 and change < gaps.EM_PRECISION_GUARD_NT:
            break
    return out, keep, iteration, change, checkpoint


def case_key(r: dict) -> tuple:
    return (r["station"], int(r["year"]), int(r["month"]), r["component"],
            r["mask_kind"], int(r["replicate"]))


def pilot_gate(cases: list[dict], inventory: dict) -> None:
    capped = [r for r in cases if int(r["em_iterations"]) == 500]
    uncapped = [r for r in cases if int(r["em_iterations"]) < 500]
    pilot = capped[:10] + uncapped[:10]
    if len(pilot) != 20:
        raise RuntimeError("U1 pilot lacks 10 capped and 10 uncapped cases")
    evidence = []
    for r in pilot:
        inv = inventory[(r["station"], int(r["year"]), int(r["month"]))]
        cache = ROOT / inv["matrix_cache"]
        if sha(cache) != inv["matrix_cache_sha256"]:
            raise RuntimeError(f"U1 pilot monthly source hash mismatch: {cache}")
        with np.load(cache, allow_pickle=False) as z:
            matrix = z["XYZ_nT"][:, :, "XYZ".index(r["component"])]
        complete, keep = gaps.fill_int(matrix)
        if not keep.all():
            raise RuntimeError(f"U1 pilot truth matrix dropped days: {case_key(r)}")
        observed, mask_seed = make_mask(r["mask_kind"], .1,
            int(r["mask_kind"][5:]) if r["mask_kind"].startswith("BLOCK") else None,
            complete.shape[1], int(r["replicate"]), r["station"], int(r["year"]), int(r["month"]), None)
        if mask_seed != int(r["mask_seed"]):
            raise RuntimeError(f"U1 pilot seed mismatch: {case_key(r)}")
        masked = complete.copy()
        masked[~observed] = np.nan
        a, k, i, c = gaps.fill_em(masked)
        b, kk, ii, cc, _ = fill_em_cap(masked, 500)
        if not (np.array_equal(a, b, equal_nan=True) and np.array_equal(k, kk) and i == ii and
                np.float64(c).tobytes() == np.float64(cc).tobytes()):
            raise RuntimeError(f"U1 fill_em_cap not bit-identical: {case_key(r)}")
        evidence.append({"case_key": list(case_key(r)), "iterations": i, "final_change_nT": c,
                         "filled_sha256": hashlib.sha256(a.tobytes()).hexdigest(),
                         "keep_sha256": hashlib.sha256(k.tobytes()).hexdigest()})
    (HERE / "U1_wrapper_verification.json").write_text(json.dumps({
        "audit_label": "EXPLORATORY_POST_HOC", "n_cases": 20,
        "n_capped": 10, "n_uncapped": 10, "bit_identical": True,
        "frozen_gaps_py_sha256": sha(PHASE3 / "auto_sqpca/gaps.py"),
        "cases": evidence}, indent=2) + "\n", encoding="utf-8")
    print("U1 20-case bit-identity gate matched", flush=True)


def finite_or_inf(s: str) -> float:
    try:
        return float(s)
    except (TypeError, ValueError):
        return float("inf")


def process_month(items: tuple[dict, list[dict]]) -> list[dict]:
    inv, source_rows = items
    path = ROOT / inv["matrix_cache"]
    if sha(path) != inv["matrix_cache_sha256"]:
        raise RuntimeError(f"U1 matrix source hash mismatch: {path}")
    with np.load(path, allow_pickle=False) as z:
        matrix = z["XYZ_nT"]
    station, year, month = inv["station"], int(inv["year"]), int(inv["month"])
    source_rows.sort(key=case_key)
    by_comp = defaultdict(list)
    for r in source_rows:
        by_comp[r["component"]].append(r)
    out = []
    for component, rr in by_comp.items():
        complete, keep = gaps.fill_int(matrix[:, :, "XYZ".index(component)])
        if not keep.all() or not np.isfinite(complete).all():
            raise RuntimeError(f"U1 complete matrix invalid: {station} {year}-{month} {component}")
        days = gfz_days(year, month) if year <= 2017 else _gfz_2018_days(month)
        reference = selection.sq_iqd(complete, days)
        surrogates = random_phase_surrogates(reference)
        truth = selection.choose(pca.decompose_v1(complete), reference, surrogates)
        if truth["curve"] is None:
            raise RuntimeError(f"U1 truth missing: {station} {year}-{month} {component}")
        for r in rr:
            old_candidate = r["selected_candidate"] or None
            old_error = finite_or_inf(r["error_relative_l2"])
            old_change = float(r["em_final_change_nT"])
            old_iter = int(r["em_iterations"])
            new_candidate, new_error, new_iter, new_change = old_candidate, old_error, old_iter, old_change
            curve_diff = 0.0 if old_candidate is not None else float("nan")
            status = "IDENTICAL_STOP_BEFORE_CAP"
            if old_iter >= 500:
                length = int(r["mask_kind"][5:]) if r["mask_kind"].startswith("BLOCK") else None
                observed, mask_seed = make_mask(r["mask_kind"], .1, length, complete.shape[1],
                    int(r["replicate"]), station, year, month, None)
                if mask_seed != int(r["mask_seed"]):
                    raise RuntimeError(f"U1 mask seed mismatch: {case_key(r)}")
                masked = complete.copy()
                masked[~observed] = np.nan
                filled, keep, new_iter, new_change, checkpoint = fill_em_cap(masked, 5000, 500)
                if checkpoint is None:
                    raise RuntimeError(f"U1 expected iteration 500 checkpoint: {case_key(r)}")
                frozen_filled, _, check_change = checkpoint
                if np.float64(check_change).tobytes() != np.float64(old_change).tobytes():
                    raise RuntimeError(f"U1 E1 frozen final-change mismatch: {case_key(r)}")
                before = selection.choose(pca.decompose_v1(frozen_filled), reference, surrogates)
                if before["selected"] != old_candidate:
                    raise RuntimeError(f"U1 frozen candidate mismatch: {case_key(r)}")
                if before["curve"] is not None and abs(metrics.relative_l2(before["curve"], truth["curve"]) - old_error) > 1e-11:
                    raise RuntimeError(f"U1 frozen error mismatch: {case_key(r)}")
                after = selection.choose(pca.decompose_v1(filled), reference, surrogates)
                new_candidate = after["selected"]
                new_error = metrics.relative_l2(after["curve"], truth["curve"]) if after["curve"] is not None else float("inf")
                curve_diff = metrics.relative_l2(after["curve"], before["curve"]) if after["curve"] is not None and before["curve"] is not None else float("nan")
                status = "RECOMPUTED_CAPPED"
            out.append({"audit_label": "EXPLORATORY_POST_HOC", "station": station, "year": year,
                        "month": month, "component": component, "mask_kind": r["mask_kind"],
                        "p_nominal": .1, "replicate": r["replicate"], "mask_seed": r["mask_seed"],
                        "cap500_iterations": old_iter, "cap500_final_change_nT": old_change,
                        "cap500_candidate": old_candidate or "", "cap500_error_relative_l2": old_error,
                        "cap5000_iterations": new_iter, "cap5000_final_change_nT": new_change,
                        "cap5000_candidate": new_candidate or "", "cap5000_error_relative_l2": new_error,
                        "candidate_same": old_candidate == new_candidate,
                        "relative_l2_curve_difference": curve_diff,
                        "status": status})
    return out


def u1_holdout(cases: list[dict], inventory: dict) -> None:
    grouped = defaultdict(list)
    for r in cases:
        grouped[(r["station"], int(r["year"]), int(r["month"]))].append(r)
    fields = ["audit_label", "station", "year", "month", "component", "mask_kind", "p_nominal",
              "replicate", "mask_seed", "cap500_iterations", "cap500_final_change_nT", "cap500_candidate",
              "cap500_error_relative_l2", "cap5000_iterations", "cap5000_final_change_nT",
              "cap5000_candidate", "cap5000_error_relative_l2", "candidate_same",
              "relative_l2_curve_difference", "status"]
    out_path = HERE / "U1_cap_sensitivity_cases.csv"
    if out_path.is_file():
        existing = read_csv(out_path)
        counts = defaultdict(int)
        for r in existing:
            counts[(r["station"], int(r["year"]), int(r["month"]))] += 1
        complete_keys = {key for key, rr in grouped.items() if counts[key] == len(rr)}
        if any(counts[key] not in (0, len(rr)) for key, rr in grouped.items()):
            existing = [r for r in existing if (r["station"], int(r["year"]), int(r["month"])) in complete_keys]
            write_csv(out_path, existing, fields)
    else:
        complete_keys = set()
        write_csv(out_path, [], fields)
    pending = {key: rr for key, rr in grouped.items() if key not in complete_keys}
    print(f"U1 resume: {len(complete_keys)}/{len(grouped)} months complete", flush=True)
    with out_path.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        with ProcessPoolExecutor(max_workers=min(6, os.cpu_count() or 1)) as pool:
            futures = {pool.submit(process_month, (inventory[key], rr)): key for key, rr in pending.items()}
            for n, f in enumerate(as_completed(futures), 1):
                key = futures[f]
                try:
                    result = f.result()
                except Exception as e:
                    raise RuntimeError(f"U1 month {key}: {type(e).__name__}: {e}") from e
                writer.writerows(result)
                stream.flush()
                if n % 10 == 0 or n == len(futures):
                    print(f"U1 months {len(complete_keys)+n}/{len(grouped)}, new cases {n}", flush=True)
    out = read_csv(out_path)
    if len(out) != len(cases):
        raise RuntimeError("U1 case count mismatch")
    out.sort(key=lambda r: (r["station"], int(r["year"]), int(r["month"]), r["component"], r["mask_kind"], int(r["replicate"])))
    write_csv(out_path, out, fields)
    summary = []
    for kind in ("MCAR", "BLOCK6", "BLOCK24", "BLOCK72"):
        subset = [r for r in out if r["mask_kind"] == kind]
        diffs = np.array([r["relative_l2_curve_difference"] for r in subset], float)
        diffs = diffs[np.isfinite(diffs)]
        e500 = np.array([r["cap500_error_relative_l2"] for r in subset], float)
        e5000 = np.array([r["cap5000_error_relative_l2"] for r in subset], float)
        summary.append({"audit_label": "EXPLORATORY_POST_HOC", "mask_kind": kind, "n_cases": len(subset),
                        "n_paired_curves": len(diffs), "fraction_at_cap500": float(np.mean([int(r["cap500_iterations"]) >= 500 for r in subset])),
                        "fraction_converged_before_cap5000": float(np.mean([int(r["cap5000_iterations"]) < 5000 for r in subset])),
                        "fraction_candidate_same": float(np.mean([r["candidate_same"] == "True" for r in subset])),
                        "curve_diff_median": float(np.median(diffs)) if len(diffs) else "",
                        "curve_diff_p90": float(np.quantile(diffs, .9, method="higher")) if len(diffs) else "",
                        "curve_diff_max": float(diffs.max()) if len(diffs) else "",
                        "cap500_error_median": float(np.median(e500)),
                        "cap500_error_p90": float(np.quantile(e500, .9, method="higher")),
                        "cap5000_error_median": float(np.median(e5000)),
                        "cap5000_error_p90": float(np.quantile(e5000, .9, method="higher"))})
    write_csv(HERE / "U1_summary.csv", summary, list(summary[0]))


def u1_e3() -> None:
    records = [r for r in read_csv(PHASE3 / "F3_E3_cases.csv") if r["status"] == "OK" and int(r["M_EM_iterations"]) >= 500]
    inv = {(r["station"], int(r["year"]), int(r["month"])): r for name in ("F3_data_inventory.csv", "F3_E3b_inventory.csv")
           for r in read_csv(PHASE3 / name)}
    config = json.loads((PHASE3 / "F3_E2_frozen.json").read_text(encoding="utf-8"))
    output = []
    for n, r in enumerate(records, 1):
        key = (r["station"], int(r["year"]), int(r["month"]))
        source = inv[key]
        path = ROOT / source["matrix_cache"]
        if sha(path) != source["matrix_cache_sha256"]:
            raise RuntimeError(f"U1 E3 source hash mismatch: {path}")
        with np.load(path, allow_pickle=False) as z:
            matrix = z["XYZ_nT"][:, :, "XYZ".index(r["component"])]
        filled, keep, iterations, change, checkpoint = fill_em_cap(matrix, 5000, 500)
        if checkpoint is None or not keep.all() or not np.isfinite(filled).all():
            raise RuntimeError(f"U1 E3 cap5000 matrix invalid: {key} {r['component']}")
        days = gfz_days(int(r["year"]), int(r["month"])) if int(r["year"]) <= 2017 else \
               _gfz_2018_days(int(r["month"]))
        old_filled, _, old_change = checkpoint
        if np.float64(old_change).tobytes() != np.float64(float(r["M_EM_final_change_nT"])).tobytes():
            raise RuntimeError(f"U1 E3 frozen iteration-500 change mismatch: {key} {r['component']}")
        old_ref = selection.sq_iqd(old_filled, days)
        old_surrogates = random_phase_surrogates(old_ref)
        old_chosen = selection.choose(pca.decompose_v1(old_filled), old_ref, old_surrogates)
        if (old_chosen["selected"] or "") != r["AUTO_candidate"]:
            raise RuntimeError(f"U1 E3 frozen candidate mismatch: {key} {r['component']}")
        ref = selection.sq_iqd(filled, days)
        surrogates = random_phase_surrogates(ref)
        chosen = selection.choose(pca.decompose_v1(filled), ref, surrogates)
        boot = bootstrap_fast(filled, ref, chosen["selected"], surrogates,
            seed("E3", r["station"], int(r["year"]), int(r["month"]), r["component"], "bootstrap"))
        why = assess({"AUTO_A1": str(chosen["selected"] is None), "AUTO_candidate": chosen["selected"] or "",
            "stability": boot["stability"], "observed_fraction": r["valid_observed_fraction"],
            "relative_width": boot["relative_width"], "status": "OK"},
            float(config["theta_s"]), float(config["theta_d"]), float("inf"))
        old_path = ROOT / r["curve_cache_path"]
        if sha(old_path) != r["curve_cache_sha256"]:
            raise RuntimeError(f"U1 E3 curve hash mismatch: {old_path}")
        with np.load(old_path, allow_pickle=False) as z:
            old_curve, difi = z["AUTO"], z["DIFI8"]
        if old_chosen["curve"] is None:
            if np.isfinite(old_curve).any():
                raise RuntimeError(f"U1 E3 frozen curve should be missing: {key} {r['component']}")
        elif not np.array_equal(old_chosen["curve"], old_curve, equal_nan=True):
            raise RuntimeError(f"U1 E3 frozen curve mismatch: {key} {r['component']}")
        new_curve = chosen["curve"]
        curve_diff = metrics.relative_l2(new_curve, old_curve) if new_curve is not None and np.isfinite(old_curve).all() else float("nan")
        old_accepted = r["abstained"] == "False"
        new_accepted = not why
        new_r = float(np.corrcoef(new_curve, difi)[0, 1]) if new_accepted and new_curve is not None else float("nan")
        old_r = float(r["r_AUTO_DIFI"]) if old_accepted else float("nan")
        output.append({"audit_label": "EXPLORATORY_POST_HOC", "station": r["station"], "year": r["year"],
                       "month": r["month"], "component": r["component"], "scope": r["scope"],
                       "cap500_iterations": r["M_EM_iterations"], "cap500_final_change_nT": r["M_EM_final_change_nT"],
                       "cap5000_iterations": iterations, "cap5000_final_change_nT": change,
                       "cap500_candidate": r["AUTO_candidate"], "cap5000_candidate": chosen["selected"] or "",
                       "candidate_changed": (r["AUTO_candidate"] or None) != chosen["selected"],
                       "cap500_abstained": r["abstained"], "cap5000_abstained": bool(why),
                       "abstain_changed": old_accepted != new_accepted,
                       "cap5000_reasons": ";".join(why), "relative_l2_curve_difference": curve_diff,
                       "cap500_r_AUTO_DIFI": old_r, "cap5000_r_AUTO_DIFI": new_r,
                       "delta_r_AUTO_DIFI": new_r - old_r if old_accepted and new_accepted else float("nan")})
        if n % 10 == 0 or n == len(records):
            print(f"U1 E3 cases {n}/{len(records)}", flush=True)
    write_csv(HERE / "U1_E3_capped.csv", output, list(output[0]) if output else ["audit_label"])


def _gfz_2018_days(month: int) -> list[int]:
    import re
    names = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    path = PHASE3 / "raw/gfz/QD_days2018.txt"
    expected = json.loads((PHASE3 / "F3_GFZ2018_source.json").read_text(encoding="utf-8"))["sha256"]
    if sha(path) != expected:
        raise RuntimeError(f"GFZ 2018 SHA-256 mismatch: {path}")
    line = next(x for x in path.read_text(encoding="utf-8").splitlines() if re.match(rf"^\s*{names[month-1]}\s+2018\s", x))
    return [int(re.match(r"^\d+", x).group()) for x in line.split()[2:7]]


def main() -> None:
    c1 = json.loads((PHASE3 / "F3_C1_result.json").read_text(encoding="utf-8"))
    source = PHASE3 / "work/E1_holdout_cases.csv"
    if sha(source) != c1["holdout_cases_sha256"]:
        raise RuntimeError("U1 E1 holdout CSV hash mismatch")
    inv = {(r["station"], int(r["year"]), int(r["month"])): r for r in read_csv(PHASE3 / "F3_data_inventory.csv")}
    cases = [r for r in read_csv(source) if r["split"] == "holdout" and r["method"] == "M-EM" and
             int(r["replicate"]) < 5 and (r["mask_kind"], r["p_nominal"]) in
             {("MCAR", "0.1"), ("BLOCK6", "0.1"), ("BLOCK24", "0.1"), ("BLOCK72", "0.1")}]
    pilot_gate(cases, inv)
    u1_holdout(cases, inv)
    u1_e3()


if __name__ == "__main__":
    main()
