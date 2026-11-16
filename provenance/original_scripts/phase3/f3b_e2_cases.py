"""F3-v1.1 E2 case evaluation; frozen E1 gap and selection code are imported."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from auto_sqpca import abstain, candidates, gaps, pca, selection, ssb, metrics
from classification_core import random_phase_surrogates
from f3_preflight import ROOT, OUT, sha, verify_snapshot

MANIFEST = OUT / "F3_ssb_manifest.csv"
WORK = OUT / "work"
FIELDS = ("case_id", "split", "station", "year", "month", "component", "alpha", "mask", "replicate",
          "status", "error_original", "ASAL_error", "AUTO_NA_error", "AUTO_curve_error",
          "ASAL_candidate", "AUTO_NA_candidate", "AUTO_candidate", "AUTO_A1",
          "stability", "relative_width", "observed_fraction", "M_EM_iterations", "M_EM_final_change_nT",
          "bootstrap_successful", "bootstrap_seed", "SQ_true_amplitude_nT")
THETA_D = .90
BOOTSTRAPS = 200


def log(message: str) -> None:
    line = f"{dt.datetime.now(dt.timezone.utc).isoformat()} {message}"
    print(line, flush=True)
    with (OUT / "F3B_execution.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def seed(*parts: object) -> int:
    return int(hashlib.sha256("|".join(map(str, (20261114, "E2", *parts))).encode()).hexdigest()[:8], 16)


def quiet_days(row: dict) -> list[int]:
    path = ROOT / row["GFZ_IQD_path"]
    if sha(path) != row["GFZ_IQD_sha256"]:
        raise RuntimeError(f"GFZ IQD file SHA-256 mismatch: {path}")
    names = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    year, month = int(row["year"]), int(row["month"])
    line = next((x for x in path.read_text(encoding="utf-8").splitlines()
                 if re.match(rf"^\s*{names[month-1]}\s+{year}\s", x)), None)
    if line is None:
        raise RuntimeError(f"GFZ quiet days missing {year}-{month:02d}")
    days = [int(re.match(r"^\d+", x).group()) for x in line.split()[2:7]]
    if len(days) != 5 or len(set(days)) != 5:
        raise RuntimeError(f"GFZ quiet days invalid {year}-{month:02d}: {days}")
    return days


def bootstrap_fast(a: np.ndarray, reference: np.ndarray, selected: str | None,
                   surrogates: np.ndarray, case_seed: int) -> dict:
    rng = np.random.default_rng(case_seed)
    labels = []
    curves = []
    for _ in range(BOOTSTRAPS):
        indices = rng.integers(0, a.shape[1], size=a.shape[1])
        result = selection.choose(pca.decompose_v1(a[:, indices]), reference, surrogates)
        labels.append(result["selected"])
        if result["curve"] is not None:
            curves.append(result["curve"])
    stability = sum(label == selected for label in labels) / BOOTSTRAPS
    if curves:
        lo, hi = np.percentile(np.stack(curves), [5, 95], axis=0)
        baseline = selection.choose(pca.decompose_v1(a), reference, surrogates)["curve"]
        amp = float(np.ptp(baseline)) if baseline is not None else 0.0
        width = float(np.median(hi - lo) / amp) if amp > 0 else float("inf")
    else:
        width = float("inf")
    return {"stability": stability, "relative_width": width, "successful": len(curves)}


def process_month(month_rows: list[dict]) -> list[dict]:
    first = month_rows[0]
    cache = ROOT / first["cache_path"]
    if sha(cache) != first["cache_sha256"]:
        raise RuntimeError(f"SSB month cache SHA-256 mismatch: {cache}")
    z = np.load(cache, allow_pickle=False)
    residual, truth = z["residual_nT"], z["DIFI8_sq_true_nT"]
    days = quiet_days(first)
    output = []
    for row in month_rows:
        comp = "XYZ".index(row["component"])
        true = truth[:, comp]
        alpha = float(row["alpha"])
        base = {k: row[k] for k in ("case_id", "split", "station", "year", "month", "component", "alpha", "mask", "replicate")}
        base.update(status="OK", error_original="", ASAL_error=float("inf"), AUTO_NA_error=float("inf"),
                    AUTO_curve_error=float("inf"), ASAL_candidate="", AUTO_NA_candidate="", AUTO_candidate="",
                    AUTO_A1=False, stability=float("nan"), relative_width=float("inf"), observed_fraction=0.0,
                    M_EM_iterations=0, M_EM_final_change_nT=0.0, bootstrap_successful=0,
                    bootstrap_seed=seed(row["case_id"], "bootstrap"), SQ_true_amplitude_nT=float(np.ptp(true)))
        try:
            y, amplitudes = ssb.generate(residual[:, :, comp], true, alpha, int(row["amplitude_seed"]))
            if np.max(np.abs((y - residual[:, :, comp]).mean(axis=1) - alpha * true)) >= 1e-10:
                raise RuntimeError("SSB T4 mean identity failed")
            if row["mask"] == "MCAR20":
                observed = np.random.default_rng(int(row["mask_seed"])).random(y.shape) >= .2
                y = y.copy(); y[~observed] = np.nan
            elif row["mask"] == "NONE":
                observed = np.ones(y.shape, dtype=bool)
            else:
                raise ValueError(f"Unknown SSB mask {row['mask']}")
            base["observed_fraction"] = float(observed.mean())
            filled, keep, info = gaps.apply(y, "M-EM")
            base["M_EM_iterations"] = info["iterations"]
            base["M_EM_final_change_nT"] = info["final_change_nT"]
            if not keep.all() or not np.isfinite(filled).all() or filled.shape[1] < 3:
                raise RuntimeError("SSB E2 M-EM produced dropped day/nonfinite/insufficient matrix")
            reference = selection.sq_iqd(filled, days)
            surrogates = random_phase_surrogates(reference)
            result = pca.decompose_v1(filled)
            curves = candidates.curves(result)
            correlation = {name: abs(float(np.corrcoef(curve, reference)[0, 1])) for name, curve in curves.items()}
            if any(not np.isfinite(x) for x in correlation.values()):
                raise RuntimeError("SSB candidate correlation undefined")
            asal_name = max(candidates.NAMES[:3], key=lambda name: correlation[name])
            chosen = selection.choose(result, reference, surrogates)
            auto_na_name = chosen["selected"] or max(candidates.NAMES, key=lambda name: correlation[name])
            base["ASAL_candidate"] = asal_name
            base["AUTO_NA_candidate"] = auto_na_name
            base["AUTO_candidate"] = chosen["selected"] or ""
            base["AUTO_A1"] = chosen["selected"] is None
            target = alpha * true
            base["ASAL_error"] = metrics.relative_l2(curves[asal_name], target)
            base["AUTO_NA_error"] = metrics.relative_l2(curves[auto_na_name], target)
            if chosen["curve"] is not None:
                base["AUTO_curve_error"] = metrics.relative_l2(chosen["curve"], target)
            boot = bootstrap_fast(filled, reference, chosen["selected"], surrogates, base["bootstrap_seed"])
            base["stability"] = boot["stability"]
            base["relative_width"] = boot["relative_width"]
            base["bootstrap_successful"] = boot["successful"]
        except Exception as e:
            base["status"] = "ERROR"
            base["error_original"] = f"{type(e).__name__}: {e}"
        output.append(base)
    return output


def run(split: str) -> None:
    verify_snapshot()
    frozen = json.loads((OUT / "F3_E1_frozen.json").read_text(encoding="utf-8"))
    if frozen["method"] != "M-EM" or sha(OUT / "F3_E1_frozen.json") != (OUT / "F3_E1_frozen.json.sha256").read_text().split()[0]:
        raise RuntimeError("E1 frozen method/hash mismatch")
    provenance = json.loads((OUT / "F3_ssb_month_provenance.json").read_text(encoding="utf-8"))
    if sha(MANIFEST) != provenance["manifest_sha256"]:
        raise RuntimeError("SSB manifest hash mismatch")
    if split == "holdout":
        config_path = OUT / "F3_E2_frozen.json"
        if not config_path.is_file() or sha(config_path) != (OUT / "F3_E2_frozen.json.sha256").read_text().split()[0]:
            raise RuntimeError("E2 frozen config must exist before holdout")
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if sha(OUT / "f3b_e2_cases.py") != config["E2_case_code_sha256"] or \
           sha(MANIFEST) != config["SSB_manifest_sha256"]:
            raise RuntimeError("E2 case code or manifest changed after freeze")
    all_rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8", newline="")))
    chosen = [r for r in all_rows if r["split"] == split]
    by_month = {}
    for row in chosen:
        by_month.setdefault((row["station"], row["year"], row["month"]), []).append(row)
    path = WORK / f"E2_{split}_cases.csv"
    if path.exists():
        raise RuntimeError(f"E2 {split} already exists; refusing recomputation: {path}")
    workers = int(os.environ.get("F3_WORKERS", "8"))
    log(f"E2 {split}: {len(by_month)} source months, {len(chosen)} cases, {workers} workers")
    n = 0
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(process_month, rows): key for key, rows in by_month.items()}
            for index, future in enumerate(as_completed(futures), 1):
                key = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    raise RuntimeError(f"E2 {split} worker {key}: {type(e).__name__}: {e}") from e
                writer.writerows(result)
                f.flush()
                n += len(result)
                if index % 5 == 0 or index == len(by_month):
                    log(f"E2 {split}: completed {index}/{len(by_month)} months, {n}/{len(chosen)} cases")
    if n != len(chosen):
        raise RuntimeError(f"E2 {split} case count mismatch: {n}/{len(chosen)}")
    log(f"E2 {split} complete: SHA-256={sha(path)}")
    verify_snapshot()


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("development", "holdout"):
        raise SystemExit("Usage: f3b_e2_cases.py development|holdout")
    run(sys.argv[1])
