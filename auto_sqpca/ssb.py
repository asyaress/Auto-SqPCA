"""Semi-synthetic benchmark generator for F3-v1 E2 (T4 only in Task A)."""
from __future__ import annotations
import numpy as np


def generate(residual: np.ndarray, sq_true: np.ndarray, alpha: float,
             seed: int = 20261114, sigma: float = 0.3) -> tuple[np.ndarray, np.ndarray]:
    residual = np.asarray(residual, dtype=float)
    sq_true = np.asarray(sq_true, dtype=float)
    if residual.shape[0] != 24 or sq_true.shape != (24,):
        raise ValueError("Residual must be 24 x N and truth 24 values")
    rng = np.random.default_rng(seed)
    amplitudes = rng.lognormal(0, sigma, size=residual.shape[1])
    amplitudes /= amplitudes.mean()
    y = residual + alpha * sq_true[:, None] * amplitudes[None, :]
    return y, amplitudes
