"""Reuse the frozen G2-R V1 numerical implementation."""
from __future__ import annotations
import sys
from pathlib import Path

G2R = Path(__file__).resolve().parents[2] / "phase2a/G2R"
sys.path.insert(0, str(G2R))
from pca_core import decompose as frozen_decompose


def decompose_v1(a):
    return frozen_decompose(a, "V1")
