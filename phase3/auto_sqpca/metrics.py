"""F3-v1 E1 error metrics and safe missing-fraction bounds."""
from __future__ import annotations
import numpy as np


def relative_l2(estimate: np.ndarray, truth: np.ndarray) -> float:
    denominator = float(np.linalg.norm(truth))
    if denominator == 0: return float("nan")
    return float(np.linalg.norm(estimate-truth) / denominator)


def vector_angle_deg(a: np.ndarray, b: np.ndarray) -> float:
    d = np.linalg.norm(a) * np.linalg.norm(b)
    if d == 0: return float("nan")
    return float(np.degrees(np.arccos(np.clip(abs(np.dot(a,b))/d, 0, 1))))


def safe_fraction(records: list[dict], epsilon: float) -> float | None:
    by_p = {}
    for r in records:
        if r["error"] is None or not np.isfinite(r["error"]): continue
        by_p.setdefault(float(r["p"]), []).append(float(r["error"]))
    safe = [p for p, values in by_p.items()
            if np.median(values) <= epsilon and np.percentile(values, 90) <= 2*epsilon]
    return max(safe) if safe else None
