"""Small synthetic-only demonstration of the frozen selection and bootstrap.

This is an illustration, not a re-analysis of observatory data.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
# The frozen package resolves the G2-R/G4-R cores from its Phase 3 position.
sys.path.insert(0, str(ROOT / "phase3"))
from auto_sqpca import abstain, bootstrap, pca, selection


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "demo/output")
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    h = np.arange(24, dtype=float)
    sq = 30 * (np.sin(2 * np.pi * h / 24) + .2 * np.cos(4 * np.pi * h / 24))
    a = sq[:, None] * np.linspace(.9, 1.1, 31)[None, :]
    reference = sq - sq.mean()
    choice = selection.choose(pca.decompose_v1(a), reference)
    boot = bootstrap.summarize(a, reference, choice["selected"], n_boot=200, seed=20261114)
    why = abstain.reasons(choice["selected"], boot["stability"], 1.0,
                          boot["relative_width"], .5, .9, float("inf"))
    payload = {"kind": "synthetic demonstration", "selected": choice["selected"],
               "stability": boot["stability"], "relative_width": boot["relative_width"],
               "abstained": bool(why), "abstain_reasons": why, "bootstrap_B": 200,
               "seed": 20261114, "hours": 24}
    (args.output / "demo_result.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    curve = choice["curve"]
    with (args.output / "demo_curve.csv").open("w", encoding="utf-8", newline="") as f:
        f.write("local_hour,selected_curve,band_low,band_high\n")
        for i in range(24):
            f.write(f"{i},{curve[i]:.12g},{boot['band_low'][i]:.12g},{boot['band_high'][i]:.12g}\n")
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.fill_between(h, boot["band_low"], boot["band_high"], color="#8dc7ea", alpha=.5, label="90% day-bootstrap band")
    ax.plot(h, curve, color="#1769a0", label=choice["selected"])
    ax.set(xlabel="Local hour", ylabel="Variation (synthetic nT)", xlim=(0, 23))
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.output / "demo_curve.png", dpi=180)
    plt.close(fig)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

