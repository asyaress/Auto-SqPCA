"""Numerical PCA operations for G2-R; no observatory input or I/O."""
from __future__ import annotations

import numpy as np

NIGHT = (0, 1, 2, 3, 23)
VARIANTS = ("V0-A", "V1", "V2", "V3")


def center(a: np.ndarray, variant: str) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64)
    if a.ndim != 2 or a.shape[0] != 24 or not np.isfinite(a).all():
        raise ValueError("PCA input must be a finite 24 x N matrix")
    if variant == "V0-A":
        return a.copy()
    if variant == "V1":
        return a - a.mean(axis=0, keepdims=True)
    if variant == "V2":
        return a - a.mean(axis=1, keepdims=True)
    if variant == "V3":
        return a - a[list(NIGHT), :].mean(axis=0, keepdims=True)
    raise ValueError(f"Unknown variant: {variant}")


def decompose(a: np.ndarray, variant: str) -> dict:
    av = center(a, variant)
    u, s, vh = np.linalg.svd(av, full_matrices=False)
    vf = s * s / np.sum(s * s)
    return {"centered": av, "pc": u, "eof": s[:, None] * vh,
            "singular_values": s, "vf": vf}


def mode(result: dict, k: int) -> np.ndarray:
    return np.outer(result["pc"][:, k], result["eof"][k])


def orient(pc: np.ndarray, eof: np.ndarray, reference_pc: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if np.corrcoef(pc, reference_pc)[0, 1] < 0:
        return -pc, -eof
    return pc, eof
