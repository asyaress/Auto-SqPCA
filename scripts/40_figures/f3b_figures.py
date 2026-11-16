"""Publication-ready F3B risk, latitude, and example-curve figures."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent


def risk_coverage() -> None:
    rows = list(csv.DictReader((OUT / "F3_E2_risk_coverage.csv").open(encoding="utf-8", newline="")))
    result = json.loads((OUT / "F3_E2_result.json").read_text(encoding="utf-8"))
    c3 = json.loads((OUT / "F3_E2_C3.json").read_text(encoding="utf-8"))
    x = [float(r["AUTO_coverage"]) for r in rows if r["AUTO_accepted_median_error"]]
    y = [float(r["AUTO_accepted_median_error"]) for r in rows if r["AUTO_accepted_median_error"]]
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    ax.plot(x, y, "o-", label="AUTO (θ_s bervariasi)", color="#2878a7")
    ax.scatter([1], [c3["AUTO_NA_all_median_error"]], marker="s", s=90, label="AUTO-NA", color="#b45f06")
    ax.scatter([c3["coverage"]], [c3["AUTO_accepted_median_error"]], marker="*", s=190,
               label=f"θ beku: s={result['theta_s']}, w=∞", color="#b22222", zorder=5)
    ax.axvline(.8, linestyle="--", color="black", linewidth=.9, label="Coverage 0,80")
    ax.set(xlabel="Coverage pada strata tanpa topeng", ylabel="Median galat relatif L2 kasus diterima",
           title="E2: risiko–coverage pada holdout")
    ax.set_xlim(0, 1.04); ax.grid(alpha=.25); ax.legend(fontsize=9)
    fig.tight_layout(); fig.savefig(OUT / "F3B_figure3_risk_coverage.png", dpi=220); plt.close(fig)


def latitude() -> None:
    rows = list(csv.DictReader((OUT / "F3_E3_cases.csv").open(encoding="utf-8", newline="")))
    groups = defaultdict(list)
    for r in rows: groups[(r["scope"], r["station"])].append(r)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    for (scope, station), group in sorted(groups.items()):
        accepted = [r for r in group if r["abstained"] == "False"]
        lat = float(np.median([float(r["dipole_geomag_lat_deg"]) for r in group]))
        rvals = [float(r["r_AUTO_DIFI"]) for r in accepted if np.isfinite(float(r["r_AUTO_DIFI"]))]
        color = "#2878a7" if scope == "E3_primary" else "#9b59b6"
        symbol = "o" if scope == "E3_primary" else "D"
        axes[0].scatter(lat, np.median(rvals) if rvals else np.nan, c=color, marker=symbol, s=75)
        axes[1].scatter(lat, 1 - len(accepted)/len(group), c=color, marker=symbol, s=75)
        offsets = ({"TUN": (-27, -15), "HUA": (7, 4), "GUA": (7, -12), "TTB": (7, 6), "COI": (7, -11)},
                   {"GUA": (7, 6), "TTB": (7, -12), "HUA": (7, 4), "COI": (7, -10)})
        for panel, (ax, val) in enumerate(((axes[0], np.median(rvals) if rvals else np.nan),
                                            (axes[1], 1-len(accepted)/len(group)))):
            ax.annotate(station, (lat, val), xytext=offsets[panel].get(station, (4, 4)),
                        textcoords="offset points", fontsize=8)
    axes[0].set(ylabel="Median r(AUTO, DIFI-8), kasus diterima", xlabel="Lintang geomagnet dipol (°)")
    axes[1].set(ylabel="Fraksi abstain", xlabel="Lintang geomagnet dipol (°)", ylim=(-.03, 1.03))
    for ax in axes: ax.grid(alpha=.25)
    fig.suptitle("E3: transfer lintas stasiun (ungu = E3b eksploratoris)")
    fig.tight_layout(); fig.savefig(OUT / "F3B_figure4_E3_latitude.png", dpi=220); plt.close(fig)


def examples() -> None:
    records = json.loads((OUT / "F3_E3_examples.json").read_text(encoding="utf-8"))
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharex=True)
    for ax, station in zip(axes.flat, ("COI", "KDU", "PLR", "TUN")):
        r = records[station]
        if r["status"] != "OK":
            ax.text(.5, .5, r["status"], ha="center", va="center", transform=ax.transAxes)
            ax.set_title(station)
            continue
        hours = np.arange(24)
        ax.fill_between(hours, r["band_low"], r["band_high"], color="#2878a7", alpha=.22, label="Pita bootstrap 90%")
        ax.plot(hours, r["AUTO"], color="#2878a7", label="AUTO")
        ax.plot(hours, r["ASAL"], color="#b45f06", linestyle="--", label="ASAL")
        ax.plot(hours, r["DIFI8"], color="black", linestyle=":", label="DIFI-8")
        ax.set_title(f"{station} {r['year']}-{r['month']:02d} X ({r['candidate']})")
        ax.set(ylabel="Variasi harian (nT)", xlabel="Jam LT (HH:30)")
        ax.grid(alpha=.25)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, bbox_to_anchor=(.5, 1.01), fontsize=9)
    fig.tight_layout(rect=(0,0,1,.95)); fig.savefig(OUT / "F3B_figure5_examples.png", dpi=220); plt.close(fig)


if __name__ == "__main__":
    risk_coverage(); latitude(); examples()
    print("F3B figures 3–5 saved")
