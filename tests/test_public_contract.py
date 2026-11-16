"""Targeted tests for the portable distribution; frozen Phase 3 files are untouched."""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from auto_sqpca import bootstrap, gaps, pca, selection

ROOT = Path(__file__).resolve().parents[1]


def historical_gaps():
    path = ROOT / "phase3/auto_sqpca/gaps.py"
    spec = importlib.util.spec_from_file_location("historical_gaps", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_public_import_from_isolated_clone_layout(tmp_path):
    shutil.copytree(ROOT / "auto_sqpca", tmp_path / "auto_sqpca",
                    ignore=shutil.ignore_patterns("__pycache__"))
    proc = subprocess.run([sys.executable, "-c",
        "from auto_sqpca.pca import decompose_v1; "
        "from auto_sqpca.selection import choose; print('portable import OK')"],
        cwd=tmp_path, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "portable import OK"


def test_valid_numerics_match_historical_before_and_after():
    old = historical_gaps()
    rng = np.random.default_rng(719)
    a = rng.normal(size=(24, 30)) + 20_000
    for fraction in (0.0, .05, .20):
        impaired = a.copy()
        impaired[rng.random(a.shape) < fraction] = np.nan
        new = gaps.fill_em(impaired)
        prior = old.fill_em(impaired)
        assert np.array_equal(new[0], prior[0])
        assert np.array_equal(new[1], prior[1])
        assert new[2:] == prior[2:]
        assert np.array_equal(pca.decompose_v1(new[0])["centered"],
                              pca.frozen_decompose(new[0], "V1")["centered"])


def test_infinity_is_missing_and_observations_are_unchanged():
    rng = np.random.default_rng(12)
    a = rng.normal(size=(24, 8))
    a[0, 0] = np.inf
    a[1, 0] = -np.inf
    a[2, 0] = np.nan
    observed = np.isfinite(a)
    filled, keep, it, change = gaps.fill_em(a)
    assert keep.all()
    assert np.isfinite(filled).all()
    assert np.array_equal(filled[observed], a[observed])
    assert 1 <= it <= 500 and np.isfinite(change)


def test_complete_and_day_validity_contract():
    a = np.arange(24 * 3, dtype=float).reshape(24, 3)
    filled, keep, it, change = gaps.fill_em(a)
    assert np.array_equal(filled, a) and keep.all() and (it, change) == (0, 0.0)
    a[:19, 1] = np.nan
    filled, keep, _, _ = gaps.fill_em(a)
    assert keep.tolist() == [True, False, True]
    assert filled.shape == (24, 2)
    with pytest.raises(ValueError, match="24 x N"):
        gaps.fill_em(np.arange(24.0))


def test_constant_reference_and_no_candidate():
    a = np.random.default_rng(11).normal(size=(24, 30))
    with pytest.raises(ValueError, match="nonconstant"):
        selection.choose(pca.decompose_v1(a), np.zeros(24))
    original_curves = selection.curves
    try:
        selection.curves = lambda *args, **kwargs: {name: np.ones(24) for name in selection.NAMES}
        with pytest.raises(ValueError, match="Candidate must be a finite nonconstant"):
            selection.choose(pca.decompose_v1(a), np.arange(24.0))
    finally:
        selection.curves = original_curves
    original = selection.classify_curve
    try:
        selection.classify_curve = lambda *args, **kwargs: {"decision": "NOT_SQ"}
        result = selection.choose(pca.decompose_v1(a), np.arange(24.0))
        assert result["selected"] is None and result["reason"] == "NO_PASS"
    finally:
        selection.classify_curve = original


def test_bootstrap_no_success_and_invalid_count(monkeypatch):
    monkeypatch.setattr(bootstrap, "choose", lambda *args, **kwargs:
                        {"selected": None, "curve": None})
    a = np.random.default_rng(5).normal(size=(24, 8))
    result = bootstrap.summarize(a, np.arange(24.0), None, n_boot=4)
    assert result["successful_bootstraps"] == 0
    assert result["stability"] == 0
    assert np.isnan(result["band_low"]).all()
    assert np.isinf(result["relative_width"])
    with pytest.raises(ValueError, match="positive"):
        bootstrap.summarize(a, np.arange(24.0), None, n_boot=0)


def test_iteration_cap_is_not_convergence():
    rng = np.random.default_rng(0)
    a = rng.normal(size=(24, 30))
    a[5:17, 4:10] = np.nan
    _, _, it, change = gaps.fill_em(a)
    assert it == 500
    assert change > gaps.EM_PRECISION_GUARD_NT
