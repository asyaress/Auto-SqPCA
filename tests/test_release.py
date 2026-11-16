from __future__ import annotations

import hashlib
import csv
import gzip
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
from auto_sqpca import candidates, gaps, pca, selection
from phase2a.G2R.pca_core import center


def test_frozen_hashes():
    lines = (ROOT / "phase3/F3B_checksums.sha256").read_text(encoding="utf-8").splitlines()
    names = {line.split(None, 1)[1].strip() for line in lines if "  auto_sqpca/" in line}
    assert names == {"auto_sqpca/" + p.name for p in (ROOT / "phase3/auto_sqpca").glob("*.py")}
    for line in lines:
        if "  auto_sqpca/" not in line:
            continue
        expected, name = line.split(None, 1)
        assert hashlib.sha256((ROOT / "phase3" / name).read_bytes()).hexdigest() == expected
    assert hashlib.sha256((ROOT / "phase3/auto_sqpca/gaps.py").read_bytes()).hexdigest() == "a97ddb8595176a9a518238761fd79d6089a933be6bc8cbe732597289338eeaa4"
    assert (ROOT / "auto_sqpca/_frozen/pca_core.py").read_bytes() == (ROOT / "phase2a/G2R/pca_core.py").read_bytes()
    assert (ROOT / "auto_sqpca/_frozen/classification_core.py").read_bytes() == (ROOT / "phase2a/G4R/classification_core.py").read_bytes()


def test_em_observed_daily_means_rank3():
    rng = np.random.default_rng(20261114)
    q, _ = np.linalg.qr(rng.normal(size=(24, 3)))
    original = (q @ rng.normal(size=(3, 90))) * .1
    missing = rng.random(original.shape) < .3
    impaired = original.copy()
    impaired[missing] = np.nan
    restored, keep, _, _ = gaps.fill_em(impaired)
    assert keep.all()
    assert np.array_equal(restored[~missing], original[~missing])
    assert np.max(np.abs(restored.mean(axis=0) - original.mean(axis=0))) < 1e-6
    assert np.max(np.abs(restored - original)) < 1e-6


def test_daily_mean_centering():
    rng = np.random.default_rng(3)
    a = rng.normal(size=(24, 31)) + 20_000
    assert np.max(np.abs(center(a, "V1").mean(axis=0))) < 1e-10


def test_candidate_sign_invariance():
    a = np.random.default_rng(2).normal(size=(24, 30))
    result = pca.decompose_v1(a)
    flipped = {**result, "pc": result["pc"].copy(), "eof": result["eof"].copy()}
    flipped["pc"][:, 0] *= -1
    flipped["eof"][0] *= -1
    for name in candidates.NAMES:
        assert np.array_equal(candidates.curves(result)[name], candidates.curves(flipped)[name])


def test_selection_seed_determinism():
    h = np.arange(24)
    sq = 30 * (np.sin(2 * np.pi * h / 24) + .2 * np.cos(4 * np.pi * h / 24))
    a = sq[:, None] * np.linspace(.9, 1.1, 31)[None, :]
    result = pca.decompose_v1(a)
    one = selection.choose(result, sq - sq.mean())
    two = selection.choose(result, sq - sq.mean())
    assert one["selected"] == two["selected"] == "PC1"
    assert np.array_equal(one["curve"], two["curve"])
    assert one["scores"] == two["scores"]


def test_original_script_copies_are_identical():
    # No original analysis script was changed for portable paths. Verify exact
    # provenance copies, rather than claiming unperformed 3-case equivalence.
    for rel in ("phase3/f3b_figures.py", "phase3/f3_e1.py", "phase2a/G2R/g2r.py", "phase2a/G4R/g4r_run.py"):
        assert (ROOT / rel).read_bytes() == (ROOT / "provenance/original_scripts" / rel).read_bytes()


def test_frozen_configs_and_results_checksums():
    for name in ("phase3/F3_E1_frozen.json", "phase3/F3_E2_frozen.json", "phase2a/G2R/G2R_frozen_config.json"):
        expected = (ROOT / f"{name}.sha256").read_text(encoding="utf-8").split()[0]
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    for subtree in ("phase2", "phase3", "post_hoc"):
        for line in (ROOT / "results" / subtree / "checksums.sha256").read_text(encoding="utf-8").splitlines():
            expected, name = line.split(None, 1)
            assert hashlib.sha256((ROOT / name.strip()).read_bytes()).hexdigest() == expected


def test_holdout_gzip_and_download_manifest():
    gz = ROOT / "results/phase3/F3_E1_holdout_cases.csv.gz"
    assert hashlib.sha256(gz.read_bytes()).hexdigest() == "4f559d2f51f60b8641a6bafb1a34febb84e21399db4f48bf48eddb9a1f9a4499"
    h = hashlib.sha256()
    with gzip.open(gz, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    assert h.hexdigest() == "1acbda1a8825b6b878704395973fea0c37b4fd1324ee470df106f2344d1aceb3"
    with (ROOT / "scripts/00_download/download_manifest.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 79
    assert all(r["url"].startswith("https://") and len(r["sha256"]) == 64 for r in rows)
    assert len({r["relative_path"] for r in rows}) == len(rows)


def test_archived_synthetic_audit_is_consistent():
    archived = json.loads((ROOT / "provenance/audit_tests/results_2026-11-15.json").read_text(encoding="utf-8"))
    rerun = json.loads((ROOT / "results/post_hoc/audit_tests_rerun.json").read_text(encoding="utf-8"))
    assert rerun["B_observed_unchanged"] is True
    assert abs(rerun["A_baseline_noop_max_abs_diff_nT"] - archived["A_baseline_noop_max_abs_diff_nT"]) < 1e-13
    assert abs(rerun["B_rank3_max_err_nT"] - archived["B_rank3_max_err_nT"]) < 1e-9
    assert rerun["B_iter"] == archived["B_iterations"]
    assert rerun["D_null_selfref_A1_pass_rate"] == archived["D_null_selfref_A1_pass_rate"]
    assert rerun["D_null_independent_ref_pass_rate"] == archived["D_null_independent_ref_pass_rate"]
    assert round(rerun["D_null_selfref_accept_after_A2_rate"], 3) == archived["D_null_selfref_accept_after_A2_rate"]
    assert rerun["E_selected_negative_r"] == archived["E_selected_negative_r"]


def test_release_manifest():
    with (ROOT / "docs/release_manifest.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) > 400
    # This is the immutable 2dadbbd manifest.  Root package files are now an
    # audited portable distribution; the phase3 copies remain frozen above.
    changed = {"auto_sqpca/pca.py", "auto_sqpca/selection.py", "auto_sqpca/gaps.py",
               "auto_sqpca/bootstrap.py", "auto_sqpca/cli.py", "demo/synthetic_month.py",
                   "README.md", "docs/deviation_log.md", "docs/release_environment.md", "docs/manuscript_map.md", "CITATION.cff", ".zenodo.json",
                   ".gitignore", "tests/test_release.py"}
    for row in rows:
        path = ROOT / row["path"]
        assert path.is_file()
        if row["path"] in changed:
            continue
        assert path.stat().st_size == int(row["bytes"])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]

