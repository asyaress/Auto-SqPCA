"""Day bootstrap for candidate stability and a 90% hourly band."""
from __future__ import annotations
import numpy as np
from .pca import decompose_v1
from .selection import choose


def summarize(a: np.ndarray, reference: np.ndarray, selected: str | None,
              n_boot: int = 200, seed: int = 20261114) -> dict:
    if n_boot < 1:
        raise ValueError("n_boot must be positive")
    rng = np.random.default_rng(seed)
    curves = []
    labels = []
    for _ in range(n_boot):
        indices = rng.integers(0, a.shape[1], size=a.shape[1])
        result = choose(decompose_v1(a[:, indices]), reference)
        labels.append(result["selected"])
        if result["curve"] is not None: curves.append(result["curve"])
    stability = sum(label == selected for label in labels) / n_boot if selected is not None else 0.0
    if curves:
        arr = np.stack(curves)
        lo, hi = np.percentile(arr, [5,95], axis=0)
        baseline = choose(decompose_v1(a), reference)["curve"]
        amplitude = float(np.ptp(baseline)) if baseline is not None else 0.0
        width = float(np.median(hi-lo) / amplitude) if amplitude > 0 else float("inf")
    else:
        lo = hi = np.full(24, np.nan)
        width = float("inf")
    return {"stability": stability, "band_low": lo, "band_high": hi,
            "relative_width": width, "bootstrap_selected": labels,
            "successful_bootstraps": len(curves)}
