"""F3-v1 required T1-T8, before any Phase 3 observatory calculation."""
from __future__ import annotations
import json
import sys
import zipfile
from pathlib import Path
import numpy as np

PHASE3 = Path(__file__).resolve().parents[1]
ROOT = PHASE3.parent
sys.path.insert(0, str(PHASE3))
from auto_sqpca import io, localtime, gaps, pca, candidates, selection, bootstrap, abstain, ssb, metrics

RESULTS = {}


def record(name: str, details: dict, passed: bool):
    RESULTS[name] = {"passed": bool(passed), **details}
    (PHASE3 / "F3_synthetic_tests.json").write_text(json.dumps(RESULTS, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sq_curve(amplitude=30):
    h = np.arange(24)
    return amplitude * (np.sin(2*np.pi*h/24) + 0.2*np.cos(4*np.pi*h/24))


def test_t1_em_rank3_mcar():
    rng = np.random.default_rng(20261114)
    q, _ = np.linalg.qr(rng.normal(size=(24,3)))
    v = rng.normal(size=(3,90))
    original = (q @ v) * 0.1
    mask = rng.random(original.shape) < 0.3
    impaired = original.copy(); impaired[mask] = np.nan
    restored, keep, it, change = gaps.fill_em(impaired)
    error = float(np.max(abs(restored-original[:, keep])))
    passed = error < 1e-6
    record("T1", {"max_error_nT": error, "iterations": it, "final_change_nT": change}, passed)
    assert passed


def test_t2_sign_invariance():
    rng = np.random.default_rng(2)
    a = rng.normal(size=(24,30))
    result = pca.decompose_v1(a)
    flipped = {**result, "pc": result["pc"].copy(), "eof": result["eof"].copy()}
    flipped["pc"][:, 0] *= -1; flipped["eof"][0] *= -1
    c1, c2 = candidates.curves(result), candidates.curves(flipped)
    error = max(float(np.max(abs(c1[k]-c2[k]))) for k in c1)
    passed = error == 0
    record("T2", {"max_candidate_difference_nT": error}, passed)
    assert passed


def test_t3_rank1_bootstrap():
    sq = sq_curve()
    # Identical noiseless rank-one days isolate bootstrap algorithmic spread.
    a = np.repeat(sq[:,None], 40, axis=1)
    ref = sq-sq.mean()
    base = selection.choose(pca.decompose_v1(a), ref)
    boot = bootstrap.summarize(a, ref, base["selected"], seed=20261114)
    passed = base["selected"] == "PC1" and boot["stability"] == 1 and boot["relative_width"] < 1e-8
    record("T3", {"selected": base["selected"], "stability": boot["stability"], "relative_width": boot["relative_width"]}, passed)
    assert passed


def test_t4_ssb_truth_identity():
    rng = np.random.default_rng(4)
    r = rng.normal(size=(24,31)); r -= r.mean(axis=1, keepdims=True)
    sq = sq_curve()
    y, amps = ssb.generate(r, sq, 2, seed=42)
    error = float(np.max(abs((y-r).mean(axis=1)-2*sq)))
    passed = error < 1e-10 and abs(amps.mean()-1)<1e-12
    record("T4", {"max_truth_error_nT": error, "amplitude_mean": float(amps.mean())}, passed)
    assert passed


def test_t5_zero_missing_all_methods():
    rng = np.random.default_rng(5)
    a = sq_curve()[:,None] + rng.normal(0,0.1,size=(24,31))
    errors = {}
    for method in ("M-INT", "M-EXC", "M-EM"):
        out, keep, _ = gaps.apply(a, method)
        errors[method] = float(np.max(abs(out-a))) if keep.all() else float("inf")
    passed = all(v == 0 for v in errors.values())
    record("T5", {"max_errors_nT": errors}, passed)
    assert passed


def test_t6_abstain_synthetic():
    rng = np.random.default_rng(6)
    ref = sq_curve(); ref -= ref.mean()
    outcomes = {}
    for label in ("noise", "strong"):
        count = 0
        for i in range(200):
            if label == "noise":
                u = rng.normal(size=(24,3)); v = rng.normal(size=(3,30))
                a = u@v + rng.normal(0,1,size=(24,30))
            else:
                a = sq_curve()[:,None] * rng.lognormal(0,0.1,size=30)[None,:] + rng.normal(0,1,size=(24,30))
            picked = selection.choose(pca.decompose_v1(a), ref)
            if picked["selected"] is None:
                rejected = True
            else:
                boot = bootstrap.summarize(a, ref, picked["selected"], seed=20261114+i)
                rejected = bool(abstain.reasons(picked["selected"], boot["stability"], 1.0,
                                                boot["relative_width"], 0.7, 0.5, 0.5))
            count += rejected
        outcomes[label] = {"abstained": count, "accepted": 200-count}
    passed = outcomes["noise"]["abstained"] >= 180 and outcomes["strong"]["accepted"] >= 180
    record("T6", {"outcomes": outcomes, "theta_s": 0.7, "theta_w": 0.5, "theta_d": 0.5,
                  "status": "PASS" if passed else "RULE_LIMITATION"}, passed)
    # F3-v1: a T6 failure is recorded, not a stop or an opportunity to retune.


def test_t7_localtime_from_metadata():
    expected = {"COI":(-1,2017), "KDU":(9,2017), "GUA":(10,2017),
                "PLR":(7,2017), "TUN":(7,2017)}
    actual = {}
    for station, (delta, year) in expected.items():
        path = ROOT / "audit_sq_wdc/cache" / f"{station}_{year}_minute_iaga_XYZF.zip"
        with zipfile.ZipFile(path) as z:
            first = next(n for n in z.namelist() if n.lower().endswith(".min"))
            lines = z.read(first).decode("ascii").splitlines()[:35]
            _, longitude = io._header(lines, station, "1-minute")
            actual[station] = {"longitude_east": longitude, "delta": localtime.delta_hours(longitude)}
    passed = all(actual[s]["delta"] == d for s,(d,_) in expected.items())
    record("T7", {"metadata": actual}, passed)
    assert passed


def test_t8_sparsity_prefers_pc1():
    sq = sq_curve()
    a = sq[:,None]*np.linspace(0.9,1.1,31)[None,:]
    picked = selection.choose(pca.decompose_v1(a), sq-sq.mean())
    passed = picked["selected"] == "PC1"
    record("T8", {"selected": picked["selected"]}, passed)
    assert passed
