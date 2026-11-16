"""New post hoc paired null bank; historical phase3 code is imported unchanged."""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "phase3"))
from auto_sqpca import pca, selection  # noqa: E402
from classification_core import random_phase_surrogates  # noqa: E402

OUT = Path(__file__).resolve().parent
SEED = 20261118
N = 100
B = 200
RHO = .9
SD = 5.0


def ar_days(rng: np.random.Generator, n: int) -> np.ndarray:
    innovations = rng.normal(size=(24, n))
    out = np.empty((24, n))
    out[0] = innovations[0]
    scale = math.sqrt(1 - RHO**2)
    for hour in range(1, 24):
        out[hour] = RHO * out[hour - 1] + scale * innovations[hour]
    return SD * out


def wilson(k: int, n: int) -> tuple[float, float]:
    z = 1.959963984540054
    p = k / n
    mid = (p + z*z/(2*n)) / (1 + z*z/n)
    radius = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return mid-radius, mid+radius


def main() -> None:
    rng = np.random.default_rng(SEED)
    rows = []
    for reference_type in ("self", "independent"):
        for case in range(N):
            matrix = 20000.0 + ar_days(rng, 30)
            if reference_type == "self":
                days = sorted(rng.choice(np.arange(1, 31), 5, replace=False).tolist())
                reference = selection.sq_iqd(matrix, days)
            else:
                days = []
                reference = ar_days(rng, 5).mean(axis=1)
                reference -= reference.mean()
            surrogates = random_phase_surrogates(reference)
            chosen = selection.choose(pca.decompose_v1(matrix), reference, surrogates)
            selected = chosen["selected"]
            boot_seed = SEED + (0 if reference_type == "self" else 100000) + case
            boot_rng = np.random.default_rng(boot_seed)
            matching = 0
            for _ in range(B):
                index = boot_rng.integers(0, 30, size=30)
                resampled = selection.choose(pca.decompose_v1(matrix[:, index]), reference, surrogates)
                matching += resampled["selected"] == selected
            stability = matching / B
            rows.append({"reference_type": reference_type, "case": case,
                         "gfz_day_indices": ";".join(map(str, days)),
                         "bootstrap_seed": boot_seed, "selected": selected or "",
                         "A1_pass": selected is not None, "stability": stability,
                         "A1_A2_accept": selected is not None and stability >= .5})
        print(reference_type, "complete", flush=True)
    with (OUT / "paired_null_cases.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    summary = {}
    for reference_type in ("self", "independent"):
        part = [r for r in rows if r["reference_type"] == reference_type]
        candidate = sum(r["A1_pass"] for r in part)
        full = sum(r["A1_A2_accept"] for r in part)
        summary[reference_type] = {"n": N, "candidate_pass": candidate,
                                   "candidate_ci95_wilson": wilson(candidate, N),
                                   "full_accept": full,
                                   "full_ci95_wilson": wilson(full, N),
                                   "paired_pass_to_reject": candidate-full,
                                   "paired_reject_to_pass": 0}
    (OUT / "paired_null_summary.json").write_text(json.dumps({"label": "POST_HOC", "seed": SEED,
        "n_per_stratum": N, "rho": RHO, "sd_nT": SD, "n_days": 30,
        "n_bootstrap": B, "surrogates": 1000, "summary": summary}, indent=2), encoding="utf-8")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
