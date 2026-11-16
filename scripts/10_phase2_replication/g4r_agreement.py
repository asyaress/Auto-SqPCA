"""Pre-registered G4-R decision agreement and label, no PCA recomputation."""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

import g4r_run as run

HERE = Path(__file__).resolve().parent


def kappa(pairs: list[tuple[str, str]]) -> dict:
    n = len(pairs)
    if n == 0: return {"n": 0, "kappa": None, "reason": "NO_PAIRS"}
    agree = sum(a == b for a, b in pairs)
    p_o = agree / n
    p_a = sum(a == "SQ_LIKE" for a, _ in pairs) / n
    p_b = sum(b == "SQ_LIKE" for _, b in pairs) / n
    p_e = p_a*p_b + (1-p_a)*(1-p_b)
    if p_e == 1:
        return {"n": n, "kappa": None, "observed_agreement": p_o,
                "expected_agreement": p_e, "reason": "CONSTANT_MARGINALS_UNDEFINED"}
    return {"n": n, "kappa": (p_o-p_e)/(1-p_e), "observed_agreement": p_o,
            "expected_agreement": p_e, "reason": "OK"}


def main() -> None:
    run.verify_frozen()
    long = run.csv_read("G4R_classification_long.csv")
    g3 = run.csv_read("G3R_structure_metrics.csv")
    if len(g3) != 432:
        raise RuntimeError(f"G3-R target count {len(g3)}, expected 432")
    grouped = defaultdict(dict)
    for r in long:
        grouped[(r["year"], r["month"], r["component"], r["candidate"])][r["pipeline"]] = r
    if any(set(v) != set(run.PIPELINES) for v in grouped.values()):
        raise RuntimeError("Incomplete four-pipeline candidate rows")
    agreement = []
    for key, v in grouped.items():
        year, month, c, candidate = key
        own, pub, mixa, mixb = (v[p] for p in run.PIPELINES)
        main_agree = own["decision"] == pub["decision"]
        sensitive = any(r["sensitive_zone"] == "True" for r in v.values())
        agreement.append({"year": year, "month": month, "component": c, "candidate": candidate,
                          "scope": own["scope"], "policy_status": own["policy_status"],
                          "development_seen": own["development_seen"], "february": own["february"],
                          "own_decision": own["decision"], "own_r": own["r"], "own_abs_r": own["abs_r"], "own_p": own["p"],
                          "pub_decision": pub["decision"], "pub_r": pub["r"], "pub_abs_r": pub["abs_r"], "pub_p": pub["p"],
                          "mixA_decision": mixa["decision"], "mixA_abs_r": mixa["abs_r"], "mixA_p": mixa["p"],
                          "mixB_decision": mixb["decision"], "mixB_abs_r": mixb["abs_r"], "mixB_p": mixb["p"],
                          "main_agree": main_agree, "sensitive_in_any_pipeline": sensitive,
                          "disagree_in_zone": not main_agree and sensitive,
                          "disagree_outside_zone": not main_agree and not sensitive,
                          "own_mixA_agree": own["decision"] == mixa["decision"],
                          "pub_mixA_agree": pub["decision"] == mixa["decision"],
                          "pub_mixB_agree": pub["decision"] == mixb["decision"]})
    matrix_groups = defaultdict(list)
    for r in agreement: matrix_groups[(r["year"], r["month"], r["component"])].append(r)
    for matrix_rows in matrix_groups.values():
        all7 = len(matrix_rows) == 7 and all(r["main_agree"] for r in matrix_rows)
        for r in matrix_rows: r["matrix_all7_agree"] = all7
    agreement.sort(key=lambda r: (r["year"] == "combined", int(r["year"]) if r["year"] != "combined" else 9999,
                                  int(r["month"]), r["component"], run.CANDIDATE_NAMES.index(r["candidate"])))
    run.csv_write("G4R_agreement.csv", agreement, list(agreement[0]))
    main = [r for r in agreement if r["policy_status"] == "ELIGIBLE"]
    unseen = [r for r in main if r["development_seen"] == "False"]
    suspect = [r for r in agreement if r["policy_status"] == "SUSPECT_DIAGNOSTIC"]
    outside = [r for r in main if r["disagree_outside_zone"]]
    run.csv_write("G4R_disagreements_outside_zone.csv", outside, list(agreement[0]))
    counts = Counter(r["status"] for r in g3)
    if sum(counts.values()) != 432 or len(agreement) != (counts["ELIGIBLE"]+counts["SUSPECT_DIAGNOSTIC"])*7:
        raise RuntimeError("Agreement denominator inconsistent with G3-R")
    kappas = {}
    for c in run.COMP:
        kappas[c] = {}
        for candidate in ("PC1", "PC2", "PC3"):
            pairs = [(r["own_decision"], r["pub_decision"]) for r in main if r["component"] == c and r["candidate"] == candidate]
            kappas[c][candidate] = kappa(pairs)
    sanity = {}
    for c in "YZ":
        sanity[c] = {}
        for p in ("P-own", "P-pub"):
            r = [x for x in long if x["component"] == c and x["pipeline"] == p and x["candidate"] == "PC1" and x["policy_status"] == "ELIGIBLE"]
            n_pass = sum(float(x["abs_r"]) >= 0.88 for x in r)
            sanity[c][p] = {"n": len(r), "ge_0p88": n_pass, "percent": 100*n_pass/len(r) if r else None}
    if any(sanity[c]["P-pub"]["percent"] is not None and sanity[c]["P-pub"]["percent"] < 90 for c in "YZ"):
        raise RuntimeError("P-pub CR4 sanity below 90%; run required unit suite once and document before finalization")
    label = "D-AGREE" if not outside else "D-PARTIAL" if not any(r["component"] in "YZ" and r["candidate"] == "PC1" for r in outside) else "D-DEVIATE"
    result = {"label": label,
              "denominator": {"target_total": 432, "excluded": counts["EXCLUDED"],
                              "suspect": counts["SUSPECT_DIAGNOSTIC"],
                              "development_seen": sum(r["development_seen"] == "True" for r in g3),
                              "unresolved": counts["UNRESOLVED_MISSING"] + counts["UNRESOLVED_ERROR"],
                              "eligible": counts["ELIGIBLE"],
                              "agree": sum(r["main_agree"] for r in main),
                              "disagree_in_zone": sum(r["disagree_in_zone"] for r in main),
                              "disagree_outside_zone": len(outside)},
              "unit_of_agree_disagree": "candidate decisions, 7 per eligible matrix",
              "eligible_matrix_all7_agree": sum(all(r["main_agree"] for r in rr) for key, rr in matrix_groups.items() if rr[0]["policy_status"] == "ELIGIBLE"),
              "eligible_matrix_any_disagree": sum(any(not r["main_agree"] for r in rr) for key, rr in matrix_groups.items() if rr[0]["policy_status"] == "ELIGIBLE"),
              "suspect_diagnostic": {"matrices": counts["SUSPECT_DIAGNOSTIC"],
                                     "candidate_disagreement": sum(not r["main_agree"] for r in suspect)},
              "development_seen_stratum": {"matrices": sum(r["status"] == "ELIGIBLE" and r["development_seen"] == "True" for r in g3),
                                           "candidate_disagreement": sum(not r["main_agree"] for r in main if r["development_seen"] == "True")},
              "unseen_stratum_diagnostic": {"matrices": len(unseen)//7,
                                             "candidate_agree": sum(r["main_agree"] for r in unseen),
                                             "disagree_in_zone": sum(r["disagree_in_zone"] for r in unseen),
                                             "disagree_outside_zone": sum(r["disagree_outside_zone"] for r in unseen)},
              "february_stratum": {"matrices": sum(r["status"] == "ELIGIBLE" and r["february"] == "True" for r in g3),
                                   "candidate_disagreement": sum(not r["main_agree"] for r in main if r["february"] == "True")},
              "combined_stratum": {"matrices": sum(r["status"] == "ELIGIBLE" and r["scope"] == "combined" for r in g3),
                                   "candidate_disagreement": sum(not r["main_agree"] for r in main if r["scope"] == "combined")},
              "diagnostic_comparisons": {"own_vs_mixA_disagreements": sum(not r["own_mixA_agree"] for r in main),
                                         "pub_vs_mixA_disagreements": sum(not r["pub_mixA_agree"] for r in main),
                                         "pub_vs_mixB_disagreements": sum(not r["pub_mixB_agree"] for r in main)},
              "kappa": kappas, "sanity_CR4": sanity,
              "G2R_label_unchanged": "S-DEVIATE", "G1_registration2": "HOLD", "G1_registration3": "HOLD"}
    run.jwrite("G4R_result.json", result)
    run.log(f"G4-R agreement done: {label}; candidates agree={result['denominator']['agree']}, in-zone={result['denominator']['disagree_in_zone']}, outside={len(outside)}")
    run.verify_frozen()


if __name__ == "__main__":
    main()
