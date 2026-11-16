"""Render post hoc matched-ablation risk curves from the audited CSV."""
import csv
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
with (ROOT / "ablation_risk_coverage.csv").open(newline="", encoding="utf-8") as f:
    data = list(csv.DictReader(f))

fig, axes = plt.subplots(1, 2, figsize=(10, 3.7), sharex=True)
styles = {"stability": ("#1466a3", "solid", "Stability ranking"),
          "correlation": ("#ba5c2e", "dashed", "Correlation ranking"),
          "random_mean_100": ("#666666", "dotted", "Random rejection mean")}
for axis, metric, label in zip(axes, ("median", "p90"), ("Median", "90th percentile")):
    for name, (color, line, display) in styles.items():
        part = sorted((r for r in data if r["ranking"] == name), key=lambda r: float(r["coverage_all"]))
        axis.plot([float(r["coverage_all"]) for r in part], [float(r[metric]) for r in part],
                  color=color, linestyle=line, linewidth=1.8, label=display)
    axis.axvline(2083/2808, color="#1466a3", alpha=.35, linewidth=1)
    axis.axvline(.8, color="black", alpha=.45, linewidth=1, linestyle="-.")
    axis.set_title(label + " relative L2 error")
    axis.set_xlabel("Accepted fraction of all 2,808 cases")
    axis.grid(alpha=.2)
    axis.set_xlim(.08, .95)
axes[0].set_ylabel("Error among accepted cases")
axes[0].legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(ROOT / "ablation_risk_coverage.png", dpi=300)
plt.close(fig)
