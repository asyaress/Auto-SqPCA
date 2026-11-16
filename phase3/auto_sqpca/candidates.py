"""Seven weighted Sq candidates specified in F3-v1 S6."""
from __future__ import annotations
import numpy as np

SUBSETS = ((0,), (1,), (2,), (0,1), (0,2), (1,2), (0,1,2))
NAMES = ("PC1", "PC2", "PC3", "PC1+PC2", "PC1+PC3", "PC2+PC3", "PC1+PC2+PC3")


def curves(pca: dict) -> dict[str, np.ndarray]:
    pc, eof = pca["pc"], pca["eof"]
    weight = eof[:3].mean(axis=1)
    return {name: sum(pc[:, k] * weight[k] for k in subset)
            for name, subset in zip(NAMES, SUBSETS)}
