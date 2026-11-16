"""F3-v1 missing data methods on 24 x N matrices."""
from __future__ import annotations
import numpy as np

# F3-v1 specifies 1e-4 nT, while its mandatory T1 requires reconstruction
# below 1e-6 nT. The deterministic precision guard below is a documented
# implementation deviation: it retains the 500-iteration cap and uses a
# stronger final change threshold to make T1 verifiable on rank-3 data.
EM_PRECISION_GUARD_NT = 1e-8


def _interpolate_1d(x: np.ndarray) -> np.ndarray:
    good = np.flatnonzero(np.isfinite(x))
    if not len(good): return x.copy()
    return np.interp(np.arange(len(x)), good, x[good])


def fill_int(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(a, dtype=float)
    keep = np.isfinite(a).any(axis=0)
    out = a[:, keep].copy()
    if not out.size: return out, keep
    flat = out.T.reshape(-1)
    good = np.flatnonzero(np.isfinite(flat))
    if len(good):
        between = np.arange(good[0], good[-1]+1)
        flat[between] = np.interp(between, good, flat[good])
    out = flat.reshape(-1, 24).T
    # Edge gaps use the closest observed value in the same day.
    for j in range(out.shape[1]):
        out[:, j] = _interpolate_1d(out[:, j])
    return out, keep


def fill_exc(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(a, dtype=float)
    keep = np.isfinite(a).sum(axis=0) >= 22
    out = a[:, keep].copy()
    for j in range(out.shape[1]): out[:, j] = _interpolate_1d(out[:, j])
    return out, keep


def fill_em(a: np.ndarray) -> tuple[np.ndarray, np.ndarray, int, float]:
    a = np.asarray(a, dtype=float)
    if a.ndim != 2 or a.shape[0] != 24:
        raise ValueError("M-EM input must be a 24 x N matrix")
    keep = np.isfinite(a).sum(axis=0) >= 6
    out = a[:, keep].copy()
    if not out.size: return out, keep, 0, 0.0
    missing = ~np.isfinite(out)
    if not missing.any(): return out, keep, 0, 0.0
    # Infinity is missing by contract.  Convert it before nanmean, which
    # otherwise includes +inf/-inf and can pass a nonfinite matrix to SVD.
    out[missing] = np.nan
    means = np.nanmean(out, axis=0)
    out[missing] = np.broadcast_to(means, out.shape)[missing]
    change = float("inf")
    for iteration in range(1, 501):
        day_mean = out.mean(axis=0, keepdims=True)
        centered = out - day_mean
        u, s, vh = np.linalg.svd(centered, full_matrices=False)
        reconstructed = (u[:, :3] * s[:3]) @ vh[:3] + day_mean
        change = float(np.max(np.abs(reconstructed[missing] - out[missing])))
        out[missing] = reconstructed[missing]
        if change < 1e-4 and change < EM_PRECISION_GUARD_NT: break
    return out, keep, iteration, change


def apply(a: np.ndarray, method: str) -> tuple[np.ndarray, np.ndarray, dict]:
    if method == "M-INT":
        out, keep = fill_int(a); return out, keep, {"iterations": 0, "final_change_nT": 0.0}
    if method == "M-EXC":
        out, keep = fill_exc(a); return out, keep, {"iterations": 0, "final_change_nT": 0.0}
    if method == "M-EM":
        out, keep, it, change = fill_em(a)
        return out, keep, {"iterations": it, "final_change_nT": change}
    raise ValueError(f"Unknown gap method: {method}")
