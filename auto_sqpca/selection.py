"""Local-IQD reference and F3-v1 candidate selection."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

G4R = Path(__file__).resolve().parents[2] / "phase2a/G4R"
sys.path.insert(0, str(G4R))
from classification_core import classify_curve, random_phase_surrogates
from .candidates import NAMES, SUBSETS, curves

NIGHT = (23, 0, 1, 2, 3)


def sq_iqd(a: np.ndarray, quiet_days: list[int]) -> np.ndarray:
    """a is 24 x N in local-calendar days; 1-based GFZ day list."""
    indices = np.array(quiet_days) - 1
    if len(indices) != 5 or min(indices) < 0 or max(indices) >= a.shape[1]:
        raise ValueError("Five GFZ quiet days must lie in local month")
    days = a[:, indices]
    if not np.isfinite(days).all():
        raise ValueError("IQD reference contains missing hours")
    daily = days - days[list(NIGHT), :].mean(axis=0, keepdims=True)
    result = daily.mean(axis=1)
    return result - result.mean()


def choose(pca: dict, reference: np.ndarray, surrogates: np.ndarray | None = None) -> dict:
    if surrogates is None: surrogates = random_phase_surrogates(reference)
    candidates = curves(pca)
    scored = {name: classify_curve(curve, reference, surrogates)
              for name, curve in candidates.items()}
    passing = [name for name in NAMES if scored[name]["decision"] == "SQ_LIKE"]
    if not passing:
        return {"selected": None, "scores": scored, "curve": None, "reason": "NO_PASS"}
    maximum = max(scored[name]["abs_r"] for name in passing)
    near = [name for name in passing if scored[name]["abs_r"] >= maximum - 0.02]
    chosen = min(near, key=lambda name: (len(SUBSETS[NAMES.index(name)]), -scored[name]["abs_r"], NAMES.index(name)))
    return {"selected": chosen, "scores": scored, "curve": candidates[chosen], "reason": "PASS"}
