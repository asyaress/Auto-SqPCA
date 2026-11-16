import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pca_core import NIGHT, VARIANTS, center, decompose, mode, orient


def synthetic():
    rng = np.random.default_rng(8247)
    q, _ = np.linalg.qr(rng.normal(size=(24, 24)))
    v, _ = np.linalg.qr(rng.normal(size=(30, 24)))
    s = np.linspace(24.0, 1.0, 24)
    a = (q * s) @ v.T
    return a, q, v, s


def test_known_svd():
    a, q, v, s = synthetic()
    result = decompose(a, "V0-A")
    assert np.max(abs(result["singular_values"] - s)) < 1e-10
    assert np.max(abs(abs(np.sum(result["pc"] * q, axis=0)) - 1)) < 1e-10
    assert np.max(abs(abs(np.sum(result["eof"] * (s[:, None] * v.T), axis=1)) - s * s)) < 1e-10
    assert np.max(abs(result["vf"] - s * s / np.sum(s * s))) < 1e-10


def test_vf_sum():
    assert abs(decompose(synthetic()[0], "V0-A")["vf"].sum() - 1) < 1e-10


def test_all_modes_reconstruct():
    a = synthetic()[0]
    for variant in VARIANTS:
        result = decompose(a, variant)
        assert np.max(abs(sum(mode(result, k) for k in range(24)) - result["centered"])) < 1e-10


def test_sign_invariance():
    result = decompose(synthetic()[0], "V0-A")
    p, e = result["pc"][:, 0], result["eof"][0]
    flipped_p, flipped_e = orient(p, e, -p)
    assert np.max(abs(np.outer(p, e) - np.outer(flipped_p, flipped_e))) < 1e-10


def test_centering_invariants():
    a = synthetic()[0]
    assert np.max(abs(center(a, "V1").mean(axis=0))) < 1e-10
    assert np.max(abs(center(a, "V2").mean(axis=1))) < 1e-10
    assert np.max(abs(center(a, "V3")[list(NIGHT), :].mean(axis=0))) < 1e-10


def test_constant_offset_invariance():
    a = synthetic()[0]
    for variant in VARIANTS[1:]:
        assert np.max(abs(center(a + 1234.0, variant) - center(a, variant))) < 1e-10
