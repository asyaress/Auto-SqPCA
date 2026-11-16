"""Reuse the frozen G2-R V1 numerical implementation."""
from __future__ import annotations
from ._frozen.pca_core import decompose as frozen_decompose


def decompose_v1(a):
    return frozen_decompose(a, "V1")
