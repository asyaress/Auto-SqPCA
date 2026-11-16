"""G4-R fixed decision rule; pure functions, no observatory data."""
from __future__ import annotations

import itertools

import numpy as np

SEED = 20261113
N_SURROGATES = 1000
ALPHA = 0.05
R_THRESHOLD = 0.45
CANDIDATES = ((0,), (1,), (2,), (0, 1), (0, 2), (1, 2), (0, 1, 2))


def random_phase_surrogates(reference: np.ndarray, n: int = N_SURROGATES, seed: int = SEED) -> np.ndarray:
    reference = np.asarray(reference, dtype=np.float64)
    if reference.shape != (24,) or not np.isfinite(reference).all():
        raise ValueError("Reference must be a finite 24-hour curve")
    spectrum = np.fft.rfft(reference)
    randomized = np.broadcast_to(spectrum, (n, len(spectrum))).copy()
    rng = np.random.default_rng(seed)
    randomized[:, 1:-1] *= np.exp(1j * rng.uniform(0, 2 * np.pi, size=(n, len(spectrum)-2)))
    return np.fft.irfft(randomized, n=24, axis=1)


def abs_correlations(curves: np.ndarray, reference: np.ndarray) -> np.ndarray:
    curves = np.asarray(curves, dtype=np.float64)
    reference = np.asarray(reference, dtype=np.float64)
    if curves.ndim == 1:
        curves = curves[None, :]
    a = curves - curves.mean(axis=1, keepdims=True)
    b = reference - reference.mean()
    denom = np.linalg.norm(a, axis=1) * np.linalg.norm(b)
    out = np.full(len(curves), np.nan)
    valid = denom > 0
    out[valid] = np.abs(a[valid] @ b / denom[valid])
    return out


def classify_curve(curve: np.ndarray, reference: np.ndarray, surrogates: np.ndarray | None = None) -> dict:
    if surrogates is None:
        surrogates = random_phase_surrogates(reference)
    r = float(np.corrcoef(curve, reference)[0, 1])
    abs_r = abs(r)
    if not np.isfinite(abs_r):
        raise ValueError("Correlation undefined for constant candidate/reference")
    p = (1 + int(np.sum(abs_correlations(surrogates, curve) >= abs_r))) / (len(surrogates) + 1)
    return {"r": r, "abs_r": abs_r, "p": p,
            "decision": "SQ_LIKE" if abs_r >= R_THRESHOLD and p < ALPHA else "NOT_SQ",
            "sensitive_zone": abs(abs_r - R_THRESHOLD) <= 0.02 or abs(p - ALPHA) <= 0.01}


def candidate_curve(pcs: np.ndarray, eofs: np.ndarray, subset: tuple[int, ...]) -> np.ndarray:
    """PCs are 3 x 24; EOFs are 3 x days; single PC is unweighted."""
    if len(subset) == 1:
        return pcs[subset[0]].copy()
    weights = eofs.mean(axis=1)
    return sum(weights[k] * pcs[k] for k in subset)
