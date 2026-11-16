"""Finalize D2b reports, apply approved G1 table, package small review artifact."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

from d2b_meanfield import ROOT, OUT, MEN, SOURCE, sha, read_csv, verify_frozen, frozen_outputs


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def combined_details(preflight: dict) -> list[dict]:
    """Complete registered _y_all consistency check only; no WDC comparison."""
    rows = []
    for key, info in preflight["meanfield"]["files"].items():
        with (ROOT / info["annual_path"]).open(encoding="utf-8", newline="") as stream:
            annual = list(csv.reader(stream, delimiter="\t"))[1:]
        with (ROOT / info["combined_path"]).open(encoding="utf-8", newline="") as stream:
            combined = list(csv.reader(stream, delimiter="\t"))[1:]
        expected = [r[i] for i in range(1, 12) for r in annual]
        actual = [r[1] for r in combined]
        if len(expected) != len(actual):
            mismatch_count = max(len(expected), len(actual))
            first_mismatch = "LENGTH"
            max_abs = ""
        else:
            mismatches = [(i, a, b) for i, (a, b) in enumerate(zip(expected, actual), 1) if a != b]
            mismatch_count = len(mismatches)
            first_mismatch = mismatches[0][0] if mismatches else ""
            max_abs = max((abs(float(a)-float(b)) for _, a, b in mismatches), default=0.)
        rows.append({"month_component": key, "annual_path": info["annual_path"],
                     "annual_sha256": info["annual_sha256"], "combined_path": info["combined_path"],
                     "combined_sha256": info["combined_sha256"], "annual_rows": len(annual),
                     "combined_rows": len(combined), "mismatch_positions": mismatch_count,
                     "first_mismatch_position_1based": first_mismatch,
                     "max_abs_value_difference_nT": max_abs,
                     "exact_year_major_consistency": mismatch_count == 0})
    write_csv(OUT / "D2b_combined_consistency.csv", rows, list(rows[0]))
    return rows


def revision_months(rows: list[dict]) -> list[dict]:
    by_month: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_month[row["calendar_month_key"]].append(row)
    out = []
    for key in sorted(by_month):
        group = by_month[key]
        revisions = [r for r in group if r.get("predicate_REVISION") == "true"]
        out.append({"year_month": key, "component_day_total": len(group),
                    "valid_comparisons": sum(bool(r.get("d_wdc_minus_mendeley_nT")) for r in group),
                    "revision_component_days": len(revisions),
                    "revision_calendar_days": len({r["date"] for r in revisions}),
                    "iqd_revision_component_days": sum(r["is_gfz_Q1_Q5"] == "True" for r in revisions),
                    "interpolated_hours_on_revision_rows": sum(int(r["interpolated_hours"]) for r in revisions),
                    "affected": bool(revisions),
                    "G3_exclusion_if_rule_applied": bool(revisions),
                    "reason": "at least one XYZ REVISION according to approved D2b threshold" if revisions else ""})
    write_csv(OUT / "D2b_revision_months.csv", out, list(out[0]))
    return out


def g1_decision(summary: dict, preflight: dict, combined: list[dict], months: list[dict]) -> dict:
    n = summary["valid_comparison_rows"]
    target = summary["component_day_target_total"]
    p = summary["predicate_counts_nonexclusive"]
    match_pct = 100*p["MATCH"]/n if n else None
    union_pct = 100*summary["match_union_quant_count"]/n if n else None
    revision_pct = 100*p["REVISION"]/n if n else None
    affected_pct = summary["revision"]["affected_percent"]
    align_fail = summary["status_counts"].get("ALIGNMENT_FAIL", 0)
    ha = summary["H_a"]["status"] == "SUPPORTED"
    # Conditions are evaluated without inventing priority between overlapping G1 rows.
    conditions = {
        "R1_MATCH_ge_99pct": bool(n and match_pct >= 99),
        "R2_MATCH_union_QUANT_ge_99pct_and_Ha": bool(n and union_pct >= 99 and ha),
        "R3_REVISION_gt_1pct_and_affected_le_10pct": bool(n and revision_pct > 1 and affected_pct <= 10),
        "R4_affected_REVISION_gt_10pct": bool(affected_pct > 10),
        "R5_ALIGNMENT_FAIL": bool(align_fail),
        "R6_otherwise": False}
    if not any(conditions.values()):
        conditions["R6_otherwise"] = True
    triggered = [key for key, hit in conditions.items() if hit]
    if triggered == ["R4_affected_REVISION_gt_10pct"]:
        status = "HOLD"
        resolution = "R4 only; no new priority rule required"
    elif len(triggered) > 1:
        status = "UNRESOLVED"
        resolution = "Multiple approved G1 rows triggered; no priority specified"
    elif triggered[0].startswith("R1") or triggered[0].startswith("R2") or triggered[0].startswith("R3") or triggered[0].startswith("R6"):
        status = "CONDITIONAL PASS"
        resolution = "One approved G1 row triggered"
    else:
        status = "HOLD"
        resolution = "One approved G1 HOLD row triggered"
    # Ambiguous class assignment does not change R4 here; preserve evidence.
    ambiguity_affects_g1 = bool(summary["ambiguous_count"] and not conditions["R4_affected_REVISION_gt_10pct"])
    if ambiguity_affects_g1:
        status = "UNRESOLVED"
        resolution = "MATCH/QUANT overlap could change G1; no approved class priority"
    out = {
        "schema": "Auto-SqPCA-S7B-G1-v1", "protocol": "G0-registration-2 APPROVED",
        "status": status, "triggered_rules": triggered, "all_rules": conditions,
        "rule_resolution": resolution,
        "preconditions": {"D1-PCA": "CONFIRMED", "D1-IQD_February_2016": "PROVISIONAL",
                          "D2-TIME_XYZ": "CONFIRMED", "F": "DEFERRED_FOR_XYZ_PCA",
                          "F_reopen_if": ["F used in any analysis", "F mismatch hours correlate with XYZ residuals in G2/G3",
                                          "development QC uses F"],
                          "G0-registration-2": "APPROVED"},
        "numeric_evidence": {
            "calendar_days_nonfeb": summary["calendar_days"],
            "component_day_target_total": target, "valid_comparison_denominator": n,
            "missing_or_alignment_rows": summary["missing_or_alignment_rows"],
            "MATCH_count": p["MATCH"], "MATCH_percent_valid": match_pct,
            "QUANT_count": p["QUANT"], "QUANT_percent_valid": 100*p["QUANT"]/n if n else None,
            "MATCH_union_QUANT_count": summary["match_union_quant_count"],
            "MATCH_union_QUANT_percent_valid": union_pct,
            "SMALL_UNEXPLAINED_count": p["SMALL_UNEXPLAINED"],
            "SMALL_UNEXPLAINED_percent_valid": 100*p["SMALL_UNEXPLAINED"]/n if n else None,
            "REVISION_count": p["REVISION"], "REVISION_percent_valid": revision_pct,
            "ambiguous_count": summary["ambiguous_count"],
            "ALIGNMENT_FAIL_count": align_fail,
            "median_d_nT": summary["median_d_wdc_minus_mendeley_nT"],
            "H_a": summary["H_a"]["status"],
            "affected_year_months": summary["revision"]["affected_year_months"],
            "total_year_months": summary["revision"]["total_year_months"],
            "affected_percent": affected_pct,
            "combined_meanField_inconsistent_files": [r["month_component"] for r in combined if not r["exact_year_major_consistency"]]},
        "affected_year_months": [r["year_month"] for r in months if r["affected"]],
        "G3_consequence": "All 121 non-February year-months are REVISION-affected under the direct absolute threshold; no clean G3 denominator from this rule; do not run G2/G3 while G1 HOLD",
        "G2_can_start_after_review": False,
        "K10": "NOT_EXECUTED: K10 condition is failure of a future non-February G2 pilot; G1 HOLD does not authorize running pilot or K10 now",
        "interpretation_limit": "REVISION is a threshold label, not proof of historical WDC revision; direct medians near +25000/-1800/+36000 nT indicate an unresolved level-reference discrepancy, without offset fitting",
        "R_claims": {"R1": "NOT_ACHIEVED", "R2": "SHAPE_ONLY_PRIOR_S7A; NOT_NEWLY_TESTED",
                     "R3": "NOT_TESTED", "R4": "NOT_TESTED"},
        "source_sha256": sha(SOURCE), "D2b_summary_sha256": sha(OUT / "D2b_summary.json"),
        "D2b_comparison_sha256": sha(OUT / "D2b_meanfield_comparison.csv"),
        "policy_sha256": sha(OUT / "S7B_benchmark_policy.csv"),
        "no_G2_G3_G4_executed": True}
    write_json(OUT / "S7B_G1_decision.json", out)
    return out


def denominator(policy: list[dict]) -> dict:
    counts = Counter()
    raw_seen = sum(r["development_seen"] == "true" for r in policy)
    for row in policy:
        if row["allowed_use"] == "EXCLUDED":
            counts["excluded"] += 1
        elif row["allowed_use"] == "SUSPECT_DIAGNOSTIC":
            counts["suspect_diagnostic"] += 1
        elif row["development_seen"] == "true":
            counts["development_seen"] += 1
        else:
            counts["eligible_prospective"] += 1
    if sum(counts.values()) != len(policy):
        raise RuntimeError("Nonexclusive S7B denominator partition")
    return {"target_total": len(policy), **dict(counts),
            "development_seen_raw_labels": raw_seen,
            "pass_absolute": "NOT_EVALUATED", "fail_absolute": "NOT_EVALUATED",
            "pass_structural": "NOT_EVALUATED", "fail_structural": "NOT_EVALUATED",
            "decision_agreement": "NOT_EVALUATED"}


def report(summary: dict, preflight: dict, combined: list[dict], months: list[dict], g1: dict,
           policy: list[dict], den: dict) -> None:
    p = summary["predicate_counts_nonexclusive"]
    n = summary["valid_comparison_rows"]
    status = summary["status_counts"]
    bad_combined = [r for r in combined if not r["exact_year_major_consistency"]]
    lines = [
        "# D2b — Perbandingan meanField Mendeley dengan rata-rata harian WDC COI",
        "",
        f"**Hasil aturan D2b: {p['REVISION']}/{n} pasangan valid berlabel REVISION; 121/121 bulan tahun terdampak. G1: HOLD menurut baris R4.** Label REVISION di sini hanya keluaran ambang `|d| > 0,5 nT`; tidak membuktikan bahwa data WDC pernah direvisi secara historis.",
        "",
        "## Aturan dan preflight",
        "",
        f"D2b mulai `{summary['started_utc']}` dan selesai `{summary['finished_utc']}`. Cakupan ialah Januari serta Maret–Desember 2007–2017 untuk X/Y/Z; Februari tidak dibandingkan. Semua {preflight['integrity_before']['G0_manifest_files']} file dalam manifest G0, termasuk 42 ZIP Fase 1, serta 54 artefak G0/D1/D2/S7-A cocok SHA-256 sebelum dan sesudah D2b. Hash per input ada di `D2b_preflight.json` dan `D2b_meanfield_comparison.csv`.",
        "",
        "Semua 132 anggota bulanan WDC memiliki timestamp berurutan HH:00, DOY kalender, header IAGA-2002/XYZF, dan CRC ZIP valid. Sentinel `88888.xx`/`99999.xx` diperlakukan sebagai missing. Hanya celah yang terkurung oleh dua jam valid di dalam bulan diinterpolasi linear; tidak ada ekstrapolasi batas bulan atau pengisian satu hari yang seluruh jamnya hilang. Aturan konservatif ini mencatat gap yang melintasi satu hari kosong sebagai unresolved.",
        "",
        "Ketiga puluh tiga DAT tahunan `meanField` memiliki indeks hari 1–30/31 sesuai kalender dan kolom `y.2007`–`y.2017`. Setiap berkas mencetak paling banyak dua desimal, sehingga resolusi cetak per berkas yang didaftarkan sebelum perbandingan adalah **0,01 nT** dan batas MATCH = 0,025 nT. Aturan MATCH dan QUANT memang tumpang tindih secara logis pada 0,02 < |d| ≤ 0,025 nT. Kode mencatat semua predikat tanpa prioritas; **0** pasangan aktual ambigu. Rentang jumlah desimal per file dicatat di preflight JSON.",
        "",
        "Berkas `_y_all` hanya diperiksa terhadap gabungan nilai tahunan, tidak dibandingkan ke WDC. Dari 33 berkas, 29 konsisten persis. Empat berkas X memiliki 30 posisi tidak cocok masing-masing:",
        "",
        "| Bulan/komponen | Posisi tidak cocok | Posisi pertama | Maks. beda nilai (nT) |",
        "|---|---:|---:|---:|",
    ]
    for row in bad_combined:
        lines.append(f"| {row['month_component']} | {row['mismatch_positions']} | {row['first_mismatch_position_1based']} | {float(row['max_abs_value_difference_nT']):.2f} |")
    lines += ["", "Inkonsistensi gabungan ini tidak dipakai untuk menggeser alignment per tahun dan tidak menyentuh keputusan D2b per hari. Penyebabnya tidak diperiksa lebih jauh sesuai K9.",
              "", "## Hasil numerik", "",
              "Selisih `d = mean_daily_WDC − meanField_Mendeley` dihitung langsung tanpa offset fit. Denominator utama D2b ialah pasangan hari–komponen valid, sedangkan target_total juga menampilkan yang tidak dapat dihitung.", "",
              "| Metrik | Jumlah | Persen dari valid |",
              "|---|---:|---:|",
              f"| Target hari kalender non-Februari | {summary['calendar_days']} | — |",
              f"| Target pasangan hari–komponen | {summary['component_day_target_total']} | — |",
              f"| Dapat dihitung | {n} | 100,00% |",
              f"| MATCH | {p['MATCH']} | {100*p['MATCH']/n:.2f}% |",
              f"| QUANT | {p['QUANT']} | {100*p['QUANT']/n:.2f}% |",
              f"| SMALL_UNEXPLAINED | {p['SMALL_UNEXPLAINED']} | {100*p['SMALL_UNEXPLAINED']/n:.2f}% |",
              f"| REVISION (label ambang) | {p['REVISION']} | {100*p['REVISION']/n:.2f}% |",
              f"| ALIGNMENT_FAIL | {status.get('ALIGNMENT_FAIL',0)} | — |",
              f"| ALL_DAY_MISSING | {status.get('ALL_DAY_MISSING',0)} | — |",
              f"| UNRESOLVED_MISSING | {status.get('UNRESOLVED_MISSING',0)} | — |",
              "", "Seluruh 10.953 pasangan valid berlabel REVISION. Sebanyak 138 pasangan adalah hari kosong sepenuhnya, dan 30 pasangan menyisakan gap yang tidak boleh diisi; ketiganya sama antar komponen, yakni 46 dan 10 hari kalender. Sebanyak 585 jam komponen terinterpolasi pada 177 pasangan hari–komponen. Tidak ada `ALIGNMENT_FAIL` pada DAT tahunan.",
              "", "| Komponen | Target hari | Valid | Median d (nT) | H-a |",
              "|:---:|---:|---:|---:|---|",]
    for comp in "XYZ":
        lines.append(f"| {comp} | {summary['calendar_days']} | {n//3} | {summary['median_d_wdc_minus_mendeley_nT'][comp]:+.6f} | {summary['H_a']['status']} |")
    lines += ["", "Median X/Y/Z berada dekat +25.000/−1.800/+36.000 nT, jauh di luar interval tanda kuantisasi H-a (±0,02–0,08 nT). **H-a NOT_SUPPORTED.** Nilai level besar ini konsisten dengan kemungkinan acuan level berbeda, tetapi D2b tidak memasang offset, tidak memulihkan versi WDC penulis, dan tidak menetapkan sebabnya. Karena itu persentase REVISION tidak boleh diterjemahkan sebagai bukti revisi historis luas.",
              "", f"Bulan terdampak didefinisikan oleh ≥1 REVISION pada X/Y/Z: **{summary['revision']['affected_year_months']}/{summary['revision']['total_year_months']} = {summary['revision']['affected_percent']:.2f}%**. Daftar lengkap 121 bulan ada di `D2b_revision_months.csv` dan `D2b_summary.json`. Semua Januari serta Maret–Desember pada setiap tahun 2007–2017 masuk daftar; Februari memang di luar cakupan. Dari pasangan REVISION, {summary['revision']['iqd_revision_component_days']} juga berada pada Q1–Q5 GFZ; status IQD dan jam terinterpolasi per hari ada di CSV utama. Jika pengecualian R4 diterapkan ke G3, seluruh bulan non-Februari akan dikeluarkan sehingga penyebut bersih kosong; G2/G3 tidak dimulai pada G1 HOLD.",
              "", "## Keputusan dan keterbatasan", "",
              "Baris G1 yang terpenuhi hanya **R4: bulan terdampak REVISION >10%**, sehingga status **HOLD**. R1/R2/R3 tidak terpenuhi; R5 tidak diputuskan berdasarkan semantik `meanField` karena D2b tidak boleh melakukan investigasi lebih jauh, sedangkan alignment tahunan lulus. Potensi overlap MATCH/QUANT tidak berpengaruh pada data aktual (0 ambigu). K10 tidak otomatis dijalankan: syaratnya ialah pilot G2 non-Februari gagal, sedangkan pilot belum dijalankan dan G1 HOLD melarang memulainya.",
              "", "R1 numerik persis tidak tercapai; R2 hanya didukung oleh hasil bentuk S7-A yang telah dilihat, tanpa uji baru; R3/R4 belum diuji. D1-IQD Februari 2016 tetap PROVISIONAL; F ditunda hanya untuk PCA XYZ dengan pemicu pembukaan kembali K6. Forensik benchmark ditutup setelah D2b sesuai K9. Residu yang belum terjelaskan dicatat sebagai keterbatasan, tanpa menyalahkan penulis asal atau mengubah 18 kontrol Sq yang gagal absolut.",
              "", "Kode: `d2b_meanfield.py`; uji sintetis: `d2b_test.py` (overlap kelas, celah internal, hari kosong, tepi bulan). Data sintetis tidak digunakan dalam angka penelitian. Seluruh angka laporan diturunkan dari CSV/JSON hasil eksekusi D2b satu kali."]
    (OUT / "D2b_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    g2 = f"""# Kesiapan pilot G2 setelah S7-B

**Status saat ini: TERTAHAN oleh G1 HOLD.** Dokumen ini merancang pilot saja; tidak ada PCA, SVD, D3, D4, atau klasifikasi dijalankan. Mulai G2 hanya dengan instruksi baru dan setelah keputusan G1 berubah melalui prosedur yang terdokumentasi.

## Target dan pemisahan pengembangan

- Bulan pemilihan varian preprocessing V0–V3: **Juni 2017** dan **Oktober 2017**, X/Y/Z. Gunakan hanya DAT `ORIGINAL_ABSOLUTE` dengan `d3_eligible=true` dari kebijakan S7-B. `DEVELOPMENT_SEEN` dilaporkan dan tidak masuk penyebut evaluasi prospektif; tetap dapat dipakai sebagai data pengembangan dengan label jelas.
- Holdout tetap: **Januari 2009** dan **Maret 2015**. Varian yang dipilih pada dua bulan pengembangan diterapkan sekali pada holdout tanpa pemilihan ulang. Semua Februari dilarang untuk pemilihan V0–V3, termasuk X/Z yang VERIFIED; Februari hanya dievaluasi di G3 berbendera sesuai K4.
- Pemeriksaan sebelum pilot: hash sumber, missing/interpolasi, metadata jam, dan konsistensi input. F tetap `DEFERRED_FOR_XYZ_PCA`, dengan tiga pemicu pembukaan kembali K6.

## Metrik dan aturan beku

Untuk tiap komponen/bulan/varian, hitung VF₁–VF₃ (selisih absolut ≤0,005), PC nondegenerat (|r| ≥0,999), EOF (RMSE ≤0,1 nT), sudut utama subruang bila pasangan singular hampir degenerat (≤5°), dan galat Frobenius relatif jumlah mode 1–3 (≤1%). Terapkan aturan resolusi cetak G0-registration-1 sebelum perbandingan, tanpa mengubah ambang berdasarkan hasil. Bandingkan `meanField` menurut uji D3 yang telah ditetapkan; jangan gunakan berkas yang `EXCLUDED` sebagai validator. Untuk pasangan hampir degenerat, gunakan kriteria North dari protokol dan nilai subruang/jumlah mode, bukan memaksakan PC individual.

Jika tidak ada V0–V3 yang lolos toleransi struktural pada pilot non-Februari, hentikan replikasi ketat menurut S3/K10 dan lanjutkan hanya sebagai implementasi ulang dengan deviasi terdokumentasi setelah keputusan peneliti. S4: kegagalan PC1 Y/Z nondegenerat (|r| <0,999) ialah tanda kegagalan implementasi. S5: kegagalan Tingkat 1 pada pengolahan penuh; belum dapat diuji. Jangan menjalankan K10 hanya dari G1 HOLD. R4 tetap bersyarat bila DIFI3 asli tidak tersedia; jangan merekonstruksinya.

## Denominator wajib pada laporan G2/G3/G4

Pada tingkat **DAT** untuk manifest awal, partisi saling eksklusif menggunakan urutan EXCLUDED → SUSPECT_DIAGNOSTIC → DEVELOPMENT_SEEN yang tersisa → ELIGIBLE_PROSPECTIVE. Label DEVELOPMENT_SEEN mentah dapat tumpang tindih, maka dilaporkan terpisah dan tidak dikurangkan dua kali. Untuk evaluasi deret G2/G3/G4, hitung ulang pada target deret sebenarnya beserta alasan setiap pengecualian. Contoh inventaris DAT saat ini (bukan hasil G2):

| target_total | excluded | suspect_diagnostic | development_seen | eligible_prospective | pass_absolute | fail_absolute | pass_structural | fail_structural | decision_agreement |
|---:|---:|---:|---:|---:|---|---|---|---|---|
| {den['target_total']} | {den['excluded']} | {den['suspect_diagnostic']} | {den['development_seen']} | {den['eligible_prospective']} | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |

Jumlah label `development_seen=true` mentah ialah {den['development_seen_raw_labels']} DAT; {den['development_seen_raw_labels']-den['development_seen']} di antaranya sudah masuk excluded/suspect. Setiap laporan kelak wajib menampilkan `target_total` bersama `eligible_prospective`, `pass_absolute/fail_absolute`, `pass_structural/fail_structural`, dan `decision_agreement` untuk G4. Enam Y Februari tetap tercatat sebagai excluded; 36 DAT IQD melaporkan hasil absolut beku dan metrik bentuk deskriptif, tanpa ambang bentuk baru. Keputusan G4 membandingkan klasifikasi dengan IQD kita dan Mendeley menurut K2, bila tahap itu kelak diizinkan.

## Dampak G1 saat ini

D2b memberi {g1['numeric_evidence']['affected_year_months']}/{g1['numeric_evidence']['total_year_months']} bulan terdampak REVISION menurut ambang langsung. Tidak ada bulan non-Februari yang bersih untuk denominator utama G3 sesuai R4. Pilot G2 menunggu review dan instruksi baru; tidak ada klaim R3/R4.
"""
    (OUT / "S7B_G2_readiness.md").write_text(g2, encoding="utf-8")

    brief = f"""# S7-B — Ringkasan eksekusi dan keputusan G1

**Amandemen G0-registration-2: APPROVED** menurut keputusan peneliti utama bertanggal 13 November 2026. Dokumen sumber SHA-256 `{sha(SOURCE)}` ditemukan di `D:\\Downloads`, bukan di working directory; isi lengkap dikonversi tanpa kehilangan paragraf atau sel tabel menjadi `S7B_decisions_approved.md`. Protokol G0-registration-1 tetap beku.

## Kebijakan benchmark

Seluruh 684 DAT memiliki satu kebijakan: 624 ORIGINAL_ABSOLUTE, 36 ABSOLUTE_REPORTED_ONLY, 18 SUSPECT_DIAGNOSTIC, 6 EXCLUDED. Rekonsiliasi S7-A: 624 VERIFIED, 54 SUSPECT, 6 UNUSABLE. Label DEVELOPMENT_SEEN pada 403 DAT; hitungan partisi denominator setelah prioritas kategori ialah {den['excluded']} excluded, {den['suspect_diagnostic']} suspect_diagnostic, {den['development_seen']} development_seen, {den['eligible_prospective']} eligible_prospective. Tidak ada DAT mentah yang dihapus atau ditimpa.

## D2b dan G1

D2b satu kali membandingkan 3.707 hari kalender non-Februari ×3 komponen = 11.121 target; 10.953 valid. MATCH 0 (0,00%), QUANT 0 (0,00%), SMALL_UNEXPLAINED 0 (0,00%), REVISION 10.953 (100,00% valid), ALIGNMENT_FAIL 0, dan 168 missing/unresolved. Median d X={summary['median_d_wdc_minus_mendeley_nT']['X']:+.6f}, Y={summary['median_d_wdc_minus_mendeley_nT']['Y']:+.6f}, Z={summary['median_d_wdc_minus_mendeley_nT']['Z']:+.6f} nT; H-a NOT_SUPPORTED. Semua 121/121 bulan non-Februari terdampak dan tercantum di `D2b_revision_months.csv`. Empat berkas meanField gabungan X (bulan 04, 06, 09, 11) tidak konsisten persis dengan blok tahunan, tetapi berkas gabungan tidak dipakai untuk perbandingan harian.

**Keputusan G1: HOLD (aturan R4).** G2 belum boleh dimulai, termasuk setelah review, kecuali G1 dinilai ulang secara terdokumentasi dengan instruksi baru. R4 tabel G1 menggunakan istilah REVISION sebagai label ambang; data ini tidak menetapkan revisi historis WDC. Median yang sangat besar menunjukkan level acuan yang belum terjelaskan, sehingga klaim data identik atau R1 tidak dibuat. D1-IQD Februari 2016 tetap PROVISIONAL, F `DEFERRED_FOR_XYZ_PCA`, R3/R4 belum diuji, dan 18 kontrol Sq FAIL absolut tetap FAIL. K10 tidak dijalankan otomatis karena pilot G2 belum berlangsung. Forensik benchmark ditutup menurut K9.

## Audit dan artefak

Semua 3.702 entri manifest G0, termasuk sumber mentah dan 42 ZIP Fase 1, serta 54 berkas beku G0/D1/D2/S7-A cocok SHA-256 sebelum dan sesudah D2b. Parser memeriksa 132 bulan WDC dan 33 pasangan DAT tahunan/gabungan. Uji sintetis aturan klasifikasi dan missing lulus sebelum satu eksekusi utama. Python, NumPy, timestamp, hash input/output, hasil per hari, dan batas interpretasi tersedia di JSON, CSV, skrip, serta log. Tidak ada PCA/SVD, D3/D4, DTW, DIFI, classifier, atau G2–G4.
"""
    (OUT / "S7B_report.md").write_text(brief, encoding="utf-8")


def main() -> None:
    summary = json.loads((OUT / "D2b_summary.json").read_text(encoding="utf-8"))
    preflight = json.loads((OUT / "D2b_preflight.json").read_text(encoding="utf-8"))
    policy = read_csv(OUT / "S7B_benchmark_policy.csv")
    comparison = read_csv(OUT / "D2b_meanfield_comparison.csv")
    if len(policy) != 684 or len(comparison) != 11121:
        raise RuntimeError("S7B output CSV row counts invalid")
    combined = combined_details(preflight)
    months = revision_months(comparison)
    if len(months) != 121 or sum(r["affected"] for r in months) != 121:
        raise RuntimeError("D2b affected-month reconciliation failed")
    g1 = g1_decision(summary, preflight, combined, months)
    den = denominator(policy)
    report(summary, preflight, combined, months, g1, policy, den)
    # Run frozen integrity after every S7-B report write; only S7-B is mutable.
    manifest = read_csv(ROOT / "phase2a/G0/input_manifest.csv")
    final_integrity = verify_frozen(manifest, preflight["frozen_outputs_sha256"], "AFTER_S7B_REPORTS")
    audit = {"schema": "Auto-SqPCA-S7B-validation-v1", "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
             "completed_local_Asia_Makassar": dt.datetime.now(dt.timezone.utc).astimezone(ZoneInfo("Asia/Makassar")).isoformat(),
             "approved_decision_source_sha256": sha(SOURCE),
             "amendment_status": "APPROVED", "policy_rows": len(policy),
             "policy_allowed_use_counts": dict(Counter(r["allowed_use"] for r in policy)),
             "policy_original_status_counts": dict(Counter(r["status_original_S7"] for r in policy)),
             "denominator_DAT_partition": den,
             "comparison_rows": len(comparison), "combined_check_rows": len(combined),
             "revision_month_rows": len(months), "G1_status": g1["status"],
             "final_frozen_integrity": final_integrity,
             "python": summary["environment"]}
    write_json(OUT / "S7B_validation.json", audit)
    with (OUT / "S7B_execution.log").open("a", encoding="utf-8") as stream:
        stream.write(f"INFO S7-B finalized_utc={audit['completed_utc']}; 684 DAT policy, 11121 D2b rows, G1={g1['status']}; no G2\n")
    files = ["S7B_decisions_approved.md", "S7B_protocol_amendment.md", "S7B_changes.md",
             "S7B_benchmark_policy.csv", "S7B_preparation.json", "D2b_preflight.json",
             "D2b_meanfield_comparison.csv", "D2b_combined_consistency.csv", "D2b_revision_months.csv",
             "D2b_summary.json", "D2b_report.md", "d2b_meanfield.py", "d2b_test.py",
             "s7b_prepare.py", "s7b_finalize.py", "S7B_G1_decision.json", "S7B_G2_readiness.md",
             "S7B_report.md", "S7B_execution.log", "S7B_validation.json"]
    checksums = "".join(f"{sha(OUT / name)}  {name}\n" for name in files)
    (OUT / "S7B_checksums.sha256").write_text(checksums, encoding="utf-8")
    files.append("S7B_checksums.sha256")
    archive_path = OUT / "S7B_review.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 13, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, (OUT / name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED,
                             compresslevel=9)
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None or sorted(archive.namelist()) != sorted(files):
            raise RuntimeError("S7B ZIP CRC/member list failed")
        for name in files:
            if archive.read(name) != (OUT / name).read_bytes():
                raise RuntimeError(f"S7B ZIP member differs: {name}")
    (OUT / "S7B_review.sha256").write_text(f"{sha(archive_path)}  S7B_review.zip\n", encoding="utf-8")
    print(f"S7B APPROVED; D2b {summary['valid_comparison_rows']} valid; G1 {g1['status']}; ZIP {archive_path.stat().st_size} bytes SHA-256 {sha(archive_path)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        with (OUT / "S7B_execution.log").open("a", encoding="utf-8") as stream:
            stream.write(f"ERROR {type(error).__name__}: {error}\n")
        raise
