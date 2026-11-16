"""Exploratory full frozen-rule pipeline under 5–10% holdout masks."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
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

TAG = "EXPLORATORY_POST_HOC"


def quiet_days(year: int, month: int) -> list[int]:
    if year <= 2017:
        return gfz_days(year, month)
    names = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    path = PHASE3 / "raw/gfz/QD_days2018.txt"
    expected = json.loads((PHASE3 / "F3_GFZ2018_source.json").read_text(encoding="utf-8"))["sha256"]
    if sha(path) != expected:
        raise RuntimeError(f"GFZ 2018 SHA-256 mismatch: {path}")
    line = next(x for x in path.read_text(encoding="utf-8").splitlines()
                if re.match(rf"^\s*{names[month-1]}\s+2018\s", x))
    return [int(re.match(r"^\d+", x).group()) for x in line.split()[2:7]]


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


def process_month(item: tuple[dict, list[dict]]) -> list[dict]:
    inv, source_rows = item
    path = ROOT / inv["matrix_cache"]
    if sha(path) != inv["matrix_cache_sha256"]:
        raise RuntimeError(f"U3 monthly source hash mismatch: {path}")
    with np.load(path, allow_pickle=False) as z:
        matrix = z["XYZ_nT"]
    station, year, month = inv["station"], int(inv["year"]), int(inv["month"])
    days = quiet_days(year, month)
    by_comp = defaultdict(list)
    for r in source_rows:
        by_comp[r["component"]].append(r)
    output = []
    for component, cases in by_comp.items():
        complete, keep = gaps.fill_int(matrix[:, :, "XYZ".index(component)])
        if not keep.all() or not np.isfinite(complete).all():
            raise RuntimeError(f"U3 complete matrix invalid: {station} {year}-{month} {component}")
        truth_ref = selection.sq_iqd(complete, days)
        truth_surrogates = random_phase_surrogates(truth_ref)
        truth = selection.choose(pca.decompose_v1(complete), truth_ref, truth_surrogates)
        if truth["curve"] is None:
            raise RuntimeError(f"U3 unmasked truth missing: {station} {year}-{month} {component}")
        for r in cases:
            kind = r["mask_kind"]
            level = float(r["p_nominal"])
            length = int(kind[5:]) if kind.startswith("BLOCK") else None
            rep = int(r["replicate"])
            observed, mask_seed = make_mask(kind, level, length, complete.shape[1], rep,
                                            station, year, month, None)
            if mask_seed != int(r["mask_seed"]):
                raise RuntimeError(f"U3 mask seed mismatch: {station} {year}-{month} {component} {kind} {rep}")
            masked = complete.copy()
            masked[~observed] = np.nan
            observed_fraction = float(observed.mean())
            day_lt6 = bool((observed.sum(axis=0) < 6).any())
            for method in ("M-EM", "M-INT"):
                base = {"audit_label": TAG, "station": station, "year": year, "month": month,
                        "component": component, "mask_kind": kind, "p_nominal": level,
                        "replicate": rep, "mask_seed": mask_seed, "method": method,
                        "observed_fraction": observed_fraction, "day_lt6": day_lt6,
                        "candidate": "", "stability": "", "relative_width": "",
                        "bootstrap_successful": "", "iterations": "", "final_change_nT": "",
                        "accepted": False, "abstain_reasons": "", "error_relative_l2": "",
                        "status": "OK", "error_original": ""}
                if day_lt6:
                    why = ["DAY_LT6"] + (["A3"] if observed_fraction < .90 else [])
                    base["abstain_reasons"] = ";".join(why)
                    base["status"] = "PRECHECK_DAY_LT6"
                    output.append(base)
                    continue
                try:
                    filled, kept, info = gaps.apply(masked, method)
                    base["iterations"] = info["iterations"]
                    base["final_change_nT"] = info["final_change_nT"]
                    if not kept.all() or filled.shape[1] < 3 or not np.isfinite(filled).all():
                        raise RuntimeError("Gap method dropped a day or produced nonfinite/insufficient matrix")
                    reference = selection.sq_iqd(filled, days)
                    surrogates = random_phase_surrogates(reference)
                    chosen = selection.choose(pca.decompose_v1(filled), reference, surrogates)
                    base["candidate"] = chosen["selected"] or ""
                    boot = bootstrap_fast(filled, reference, chosen["selected"], surrogates,
                        seed("E3", station, year, month, component, "bootstrap"))
                    base["stability"] = boot["stability"]
                    base["relative_width"] = boot["relative_width"]
                    base["bootstrap_successful"] = boot["successful"]
                    why = assess({"AUTO_A1": str(chosen["selected"] is None),
                        "AUTO_candidate": chosen["selected"] or "", "stability": boot["stability"],
                        "observed_fraction": observed_fraction, "relative_width": boot["relative_width"],
                        "status": "OK"}, .5, .9, float("inf"))
                    base["abstain_reasons"] = ";".join(why)
                    base["accepted"] = not why
                    if chosen["curve"] is not None and not why:
                        base["error_relative_l2"] = metrics.relative_l2(chosen["curve"], truth["curve"])
                except Exception as e:
                    base["status"] = "ERROR"
                    base["error_original"] = f"{type(e).__name__}: {e}"
                    base["abstain_reasons"] = "ERROR" + (";A3" if observed_fraction < .90 else "")
                output.append(base)
    return output


def q90(a: np.ndarray) -> float:
    return float(np.quantile(a, .9, method="higher"))


def summary(cases: list[dict]) -> list[dict]:
    out = []
    settings = sorted({(r["mask_kind"], float(r["p_nominal"])) for r in cases})
    for kind, level in settings:
        same = [r for r in cases if r["mask_kind"] == kind and float(r["p_nominal"]) == level]
        by_method = {m: [r for r in same if r["method"] == m] for m in ("M-EM", "M-INT")}
        case_ids = lambda r: (r["station"], r["year"], r["month"], r["component"], r["replicate"])
        paired = {m: {case_ids(r): r for r in rr} for m, rr in by_method.items()}
        both = []
        for key in sorted(set(paired["M-EM"]) & set(paired["M-INT"])):
            em, inter = paired["M-EM"][key], paired["M-INT"][key]
            if em["accepted"] and inter["accepted"]:
                both.append((key[:3], float(em["error_relative_l2"]) - float(inter["error_relative_l2"])))
        clusters = defaultdict(list)
        for key, diff in both:
            clusters[key].append(diff)
        values = np.array([diff for _, diff in both], float)
        ci = (float("nan"), float("nan"))
        if clusters:
            arrays = [np.array(clusters[k], float) for k in sorted(clusters)]
            rng = np.random.default_rng(20261115)
            boot = []
            for _ in range(2000):
                ids = rng.integers(0, len(arrays), size=len(arrays))
                boot.append(float(np.median(np.concatenate([arrays[i] for i in ids]))))
            ci = tuple(float(x) for x in np.quantile(boot, [.025, .975]))
        for method, rr in by_method.items():
            accepted = [r for r in rr if r["accepted"]]
            errors = np.array([float(r["error_relative_l2"]) for r in accepted], float)
            reasons = Counter(code for r in rr if not r["accepted"] for code in r["abstain_reasons"].split(";") if code)
            out.append({"audit_label": TAG, "mask_kind": kind, "p_nominal": level, "method": method,
                        "n_cases": len(rr), "n_accepted": len(accepted),
                        "accepted_fraction": len(accepted) / len(rr) if rr else float("nan"),
                        "abstain_reasons_overlapping_json": json.dumps(dict(sorted(reasons.items())), sort_keys=True),
                        "accepted_error_median": float(np.median(errors)) if len(errors) else "",
                        "accepted_error_p90": q90(errors) if len(errors) else "",
                        "n_paired_both_accepted": len(both),
                        "paired_M_EM_minus_M_INT_median": float(np.median(values)) if len(values) else "",
                        "paired_median_ci95_low": ci[0], "paired_median_ci95_high": ci[1]})
    return out


def main() -> None:
    config = json.loads((PHASE3 / "F3_E2_frozen.json").read_text(encoding="utf-8"))
    assert config["theta_s"] == .5 and config["theta_d"] == .9 and config["theta_w"] == "INF"
    c1 = json.loads((PHASE3 / "F3_C1_result.json").read_text(encoding="utf-8"))
    e1_path = PHASE3 / "work/E1_holdout_cases.csv"
    if sha(e1_path) != c1["holdout_cases_sha256"]:
        raise RuntimeError("U3 E1 source SHA-256 mismatch")
    source = [r for r in read_csv(e1_path) if r["split"] == "holdout" and r["method"] == "M-EM" and
              int(r["replicate"]) < 5 and (r["mask_kind"], r["p_nominal"]) in
              {("MCAR", "0.05"), ("MCAR", "0.1"), ("BLOCK6", "0.1"),
               ("BLOCK24", "0.1"), ("BLOCK72", "0.1"), ("DAY", "0.1")}]
    inventory = {(r["station"], int(r["year"]), int(r["month"])): r for r in read_csv(PHASE3 / "F3_data_inventory.csv")}
    grouped = defaultdict(list)
    for r in source:
        grouped[(r["station"], int(r["year"]), int(r["month"]))].append(r)
    out_path = HERE / "U3_full_pipeline_cases.csv"
    fields = ["audit_label", "station", "year", "month", "component", "mask_kind", "p_nominal", "replicate",
              "mask_seed", "method", "observed_fraction", "day_lt6", "candidate", "stability",
              "relative_width", "bootstrap_successful", "iterations", "final_change_nT", "accepted",
              "abstain_reasons", "error_relative_l2", "status", "error_original"]
    if out_path.is_file():
        existing = read_csv(out_path)
        counts = defaultdict(int)
        for r in existing:
            counts[(r["station"], int(r["year"]), int(r["month"]))] += 1
        complete_keys = {key for key, rr in grouped.items() if counts[key] == 2 * len(rr)}
        if any(counts[key] not in (0, 2 * len(rr)) for key, rr in grouped.items()):
            existing = [r for r in existing if (r["station"], int(r["year"]), int(r["month"])) in complete_keys]
            write_csv(out_path, existing, fields)
    else:
        complete_keys = set()
        existing = []
        write_csv(out_path, [], fields)
    n = len(existing)
    pending = {key: rr for key, rr in grouped.items() if key not in complete_keys}
    print(f"U3 resume: {len(complete_keys)}/{len(grouped)} months, {n} method-cases", flush=True)
    with out_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        with ProcessPoolExecutor(max_workers=min(6, os.cpu_count() or 1)) as pool:
            futures = {pool.submit(process_month, (inventory[key], rr)): key for key, rr in pending.items()}
            for index, future in enumerate(as_completed(futures), 1):
                key = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    raise RuntimeError(f"U3 month {key}: {type(e).__name__}: {e}") from e
                w.writerows(result)
                f.flush()
                n += len(result)
                if index % 10 == 0 or index == len(futures):
                    print(f"U3 months {len(complete_keys)+index}/{len(grouped)}, method-cases {n}/{len(source)*2}", flush=True)
    if n != len(source) * 2:
        raise RuntimeError(f"U3 method-case count mismatch: {n}/{len(source)*2}")
    cases = read_csv(out_path)
    for r in cases:
        r["accepted"] = r["accepted"] == "True"
    sums = summary(cases)
    write_csv(HERE / "U3_summary.csv", sums, list(sums[0]))
    print(f"U3 complete: {n} method-cases", flush=True)


if __name__ == "__main__":
    main()
