import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from classification_core import (CANDIDATES, SEED, candidate_curve, classify_curve,
                                 random_phase_surrogates)


def reference():
    h = np.arange(24)
    return 7 * np.sin(2*np.pi*h/24) + 3 * np.cos(4*np.pi*h/24) + 0.8*np.sin(6*np.pi*h/24)


def test_surrogate_preserves_spectrum_and_mean():
    x = reference()
    s = random_phase_surrogates(x)
    assert np.max(abs(abs(np.fft.rfft(s, axis=1)) - abs(np.fft.rfft(x)))) < 1e-10
    assert np.max(abs(s.mean(axis=1) - x.mean())) < 1e-10


def test_seed_reproducibility():
    x = reference()
    assert classify_curve(x, x)["p"] == classify_curve(x, x)["p"]
    assert np.array_equal(random_phase_surrogates(x), random_phase_surrogates(x))


def test_identity_and_white_noise_false_positives():
    x = reference()
    assert classify_curve(x, x)["abs_r"] > 1-1e-12
    assert classify_curve(x, x)["p"] < 0.05
    surrogates = random_phase_surrogates(x)
    rng = np.random.default_rng(419)
    positives = sum(classify_curve(rng.normal(size=24), x, surrogates)["decision"] == "SQ_LIKE" for _ in range(100))
    assert 1 <= positives <= 10, positives


def test_rule_consistency_and_record():
    x = reference()
    surrogates = random_phase_surrogates(x)
    rng = np.random.default_rng(991)
    outside = same = 0
    for _ in range(200):
        original = x + rng.normal(0, 0.3, 24)
        perturbed = original + rng.normal(0, 0.05, 24)
        a = classify_curve(original, x, surrogates)
        b = classify_curve(perturbed, x, surrogates)
        if not a["sensitive_zone"] and not b["sensitive_zone"]:
            outside += 1
            same += a["decision"] == b["decision"]
    fraction = same / outside if outside else None
    result = {"synthetic_cases": 200, "noise_sd_nT": 0.05, "outside_sensitive_zone": outside,
              "same_decision": same, "same_fraction": fraction,
              "threshold": 0.95, "status": "PASS" if fraction is not None and fraction >= 0.95 else "LIMITATION_RULE_INCONSISTENT"}
    out = Path(__file__).resolve().parents[1] / "G4R_rule_consistency.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    assert outside > 0


def test_zero_weight_combination_equals_single_pc():
    h = np.arange(24)
    pcs = np.stack((np.sin(h), np.cos(h), np.sin(2*h)))
    eofs = np.array([[2., 2.], [0., 0.], [1., 1.]])
    combo = candidate_curve(pcs, eofs, (0, 1))
    assert np.allclose(combo, 2*pcs[0])
    x = reference(); s = random_phase_surrogates(x)
    assert classify_curve(combo, x, s)["decision"] == classify_curve(pcs[0], x, s)["decision"]


def test_sign_flip_invariant():
    x = reference()
    rng = np.random.default_rng(72)
    pcs = rng.normal(size=(3,24)); eofs = rng.normal(size=(3,30))
    flipped_pc = pcs.copy(); flipped_eof = eofs.copy()
    flipped_pc[0] *= -1; flipped_eof[0] *= -1
    s = random_phase_surrogates(x)
    for subset in CANDIDATES:
        a = classify_curve(candidate_curve(pcs,eofs,subset),x,s)
        b = classify_curve(candidate_curve(flipped_pc,flipped_eof,subset),x,s)
        assert a["decision"] == b["decision"]


def test_headerless_vf_first_year_adapter(tmp_path):
    from g4r_run import vf_scalar_adapter
    path = tmp_path / "VF.dat"
    path.write_text("y.2007\t0.123\ny.2008\t0.456\n", encoding="utf-8")
    assert vf_scalar_adapter(path, "y.2007") == 0.123
    assert vf_scalar_adapter(path, "y.2008") == 0.456
