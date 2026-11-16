"""Apply preregistered F3-v1/v1.1 claim and title rules to completed results."""
from __future__ import annotations

import csv
import json

from f3_preflight import OUT, sha, verify_snapshot


def main() -> None:
    verify_snapshot()
    c1 = json.loads((OUT / "F3_C1_result.json").read_text(encoding="utf-8"))
    e2 = json.loads((OUT / "F3_E2_result.json").read_text(encoding="utf-8"))
    frozen = json.loads((OUT / "F3_E2_frozen.json").read_text(encoding="utf-8"))
    reproduce = json.loads((OUT / "F3_reproduce_check.json").read_text(encoding="utf-8"))
    if not reproduce["all_pass"] or c1["selected_method"] != frozen["E1_method"]:
        raise RuntimeError("F3 claims input integrity mismatch")
    c1_ok, c2_ok, c3_ok = bool(c1["C1_success"]), bool(e2["C2_X_success"]), bool(e2["C3_success"])
    if c1_ok and c3_ok:
        title = "Auto-SqPCA: A Quality-Aware and Uncertainty-Guided Workflow for Extracting Solar Quiet Geomagnetic Variations at Low and Equatorial Latitudes"
    elif c1_ok:
        title = "Auto-SqPCA: A Quality-Aware Workflow for Extracting Solar Quiet Geomagnetic Variations at Low and Equatorial Latitudes"
    elif c3_ok:
        title = "Auto-SqPCA: An Uncertainty-Guided Workflow for Extracting Solar Quiet Geomagnetic Variations at Low and Equatorial Latitudes"
    else:
        title = "Automated PCA-based Sq extraction at low and equatorial latitudes: validation using selected Indonesian and INTERMAGNET observatories"
    claims = {
        "C1": {"status": "BERHASIL" if c1_ok else "GAGAL", "method": c1["selected_method"],
               "qualifications": ["GFZ 2018 input corrected after preliminary C1 was seen; preliminary and corrected C1 both succeeded",
                                  "DAY mask is equivalent by construction under all three gap methods"]},
        "C2": {"status": "BERHASIL" if c2_ok else "GAGAL", "rule": "X paired median ASAL minus AUTO-NA lower 95% cluster bootstrap CI >0",
               "PC_combinations_contribution_allowed": c2_ok},
        "C3": {"status": "BERHASIL" if c3_ok else "GAGAL", "rule": "median error reduction lower 95% CI >0 and unmasked holdout coverage >=0.80",
               "unmasked_holdout_coverage": e2["unmasked_coverage"], "masked_abstain_fraction": e2["masked_abstain_fraction"]},
        "C4": {"status": "DESCRIPTIVE", "stations_primary": ["COI", "KDU", "GUA", "PLR", "TUN"],
               "stations_exploratory": ["HUA", "TTB", "MBO"], "reference": "DIFI8 independent of IQD selection"},
        "C5": {"status": "PARTIAL", "cached_F3A_hash_verification": True,
               "limitation": "F3A cached hash verification passed; one-command full Phase 3 rerun from raw data is not demonstrated"},
        "allowed_title": title,
        "allowed_claim_sentences": [
            "Auto-SqPCA dengan M-EM menunjukkan ketahanan lebih baik daripada interpolasi linear untuk MCAR dan blok 24 jam pada holdout E1." if c1_ok else "Batas operasi data hilang diukur tanpa klaim keunggulan metode.",
            "Kombinasi PC diperlakukan sebagai opsi, karena C2 tidak menunjukkan peningkatan nyata pada komponen X." if not c2_ok else "Kombinasi PC menurunkan galat komponen X secara nyata pada SSB holdout.",
            "Abstain menurunkan median galat pada kasus diterima, tetapi coverage 74,18% berada di bawah syarat 80%; klaim uncertainty-guided tidak didukung." if not c3_ok else "Abstain menurunkan galat dengan coverage memenuhi syarat pada strata utama.",
            "Hasil transfer E3 bersifat deskriptif dan berlaku hanya untuk stasiun yang diuji; E3b eksploratoris.",
            "Topeng DAY setara menurut konstruksi bagi metode celah yang dibandingkan."],
        "prohibited_claims": ["uncertainty-guided" if not c3_ok else "", "PC combination as validated contribution" if not c2_ok else "",
                              "berlaku untuk Indonesia"],
        "source_sha256": {"F3_protocol_v1.md": sha(OUT / "F3_protocol_v1.md"),
                          "F3_amendment_v1.1.md": sha(OUT / "F3_amendment_v1.1.md"),
                          "F3_E1_frozen.json": sha(OUT / "F3_E1_frozen.json"),
                          "F3_E2_frozen.json": sha(OUT / "F3_E2_frozen.json"),
                          "F3_E2_result.json": sha(OUT / "F3_E2_result.json"),
                          "F3_E3_cases.csv": sha(OUT / "F3_E3_cases.csv")}}
    claims["prohibited_claims"] = [x for x in claims["prohibited_claims"] if x]
    (OUT / "F3_claims.json").write_text(json.dumps(claims, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    parameters = [
        ("gap_method", frozen["E1_method"], frozen["E1_frozen_sha256"]),
        ("theta_s", frozen["theta_s"], sha(OUT / "F3_E2_frozen.json")),
        ("theta_w", frozen["theta_w"], sha(OUT / "F3_E2_frozen.json")),
        ("theta_d", frozen["theta_d"], sha(OUT / "F3_E2_frozen.json")),
        ("SSB_seed", frozen["seed"], sha(OUT / "F3_ssb_manifest.csv")),
        ("bootstrap_B", frozen["bootstrap_B"], sha(OUT / "F3_E2_frozen.json")),
        ("DIFI_model", "DIFI8", sha(OUT / "F3_ssb_month_provenance.json")),
        ("dipole_epoch", 2015, sha(OUT / "F3_E3_provenance.json")),
    ]
    with (OUT / "F3B_parameters.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(("parameter", "value", "source_sha256"))
        writer.writerows(parameters)
    print(f"Claims: C1={claims['C1']['status']} C2={claims['C2']['status']} C3={claims['C3']['status']} C5={claims['C5']['status']}")
    verify_snapshot()


if __name__ == "__main__":
    main()
