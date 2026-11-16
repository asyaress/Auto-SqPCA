"""Audit and package Phase 3 Task B without raw or large working matrices."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from f3_preflight import ROOT, OUT, sha, verify_snapshot

EXPECTED_A = {"protocol": "617c96d0cbda26fa3f6333ea1638030a35db1836fd99ba35f2a3bb18ea091327",
              "E1_frozen": "a2a2cd09ccf4c16c87a9033d792de80762d253c2db16455f81cc4329ad26981d",
              "E1_cases": "1acbda1a8825b6b878704395973fea0c37b4fd1324ee470df106f2344d1aceb3",
              "F3A_zip": "ece7681a70c886966f3ad6818288f5277f3cfe7f8203bbb8e29af2cf9be5c1d8"}


def read_csv(path: Path) -> list[dict]:
    return list(csv.DictReader(path.open(encoding="utf-8", newline="")))


def main() -> None:
    frozen_count = verify_snapshot()
    checks = {"protocol_v1": sha(OUT / "F3_protocol_v1.md"),
              "amendment_v1p1": sha(OUT / "F3_amendment_v1.1.md"),
              "E1_frozen": sha(OUT / "F3_E1_frozen.json"),
              "E1_cases": sha(OUT / "work/E1_holdout_cases.csv"),
              "F3A_zip": sha(OUT / "F3A_review.zip")}
    if checks["protocol_v1"] != EXPECTED_A["protocol"] or checks["E1_frozen"] != EXPECTED_A["E1_frozen"] or \
       checks["E1_cases"] != EXPECTED_A["E1_cases"] or checks["F3A_zip"] != EXPECTED_A["F3A_zip"]:
        raise RuntimeError("Frozen Task A hash changed")
    amendment_sha = "8dae6289ef71f1829d37ba6d5726253fd206c679221da7106b1a820421900a8f"
    if checks["amendment_v1p1"] != amendment_sha:
        raise RuntimeError("F3-v1.1 amendment hash mismatch")
    frozen_path = OUT / "F3_E2_frozen.json"
    if sha(frozen_path) != (OUT / "F3_E2_frozen.json.sha256").read_text().split()[0]:
        raise RuntimeError("E2 frozen config hash mismatch")
    e2freeze = json.loads(frozen_path.read_text(encoding="utf-8"))
    for file, field in (("f3b_e2_cases.py", "E2_case_code_sha256"),
                        ("f3b_e2_eval.py", "E2_evaluator_code_sha256"),
                        ("f3b_e2_zero.py", "E2_zero_code_sha256"),
                        ("f3b_e2_develop.py", "E2_development_selection_code_sha256")):
        if sha(OUT / file) != e2freeze[field]:
            raise RuntimeError(f"E2 frozen code changed: {file}")
    if sha(OUT / "F3_ssb_manifest.csv") != e2freeze["SSB_manifest_sha256"] or \
       sha(OUT / "work/E2_development_cases.csv") != e2freeze["E2_development_cases_sha256"]:
        raise RuntimeError("E2 development/SSB manifest changed since freeze")
    e2 = json.loads((OUT / "F3_E2_result.json").read_text(encoding="utf-8"))
    c2 = read_csv(OUT / "F3_E2_C2.csv")
    c3 = json.loads((OUT / "F3_E2_C3.json").read_text(encoding="utf-8"))
    masked = json.loads((OUT / "F3_E2_masked_stratum.json").read_text(encoding="utf-8"))
    alpha0 = json.loads((OUT / "F3_E2_alpha0.json").read_text(encoding="utf-8"))
    e3prov = json.loads((OUT / "F3_E3_provenance.json").read_text(encoding="utf-8"))
    e3val = json.loads((OUT / "F3_E3_summary_validation.json").read_text(encoding="utf-8"))
    claims = json.loads((OUT / "F3_claims.json").read_text(encoding="utf-8"))
    convergence = json.loads((OUT / "F3_E1_convergence.json").read_text(encoding="utf-8"))
    secondary = read_csv(OUT / "F3_E1_secondary_metrics.csv")
    reproduce = json.loads((OUT / "F3_reproduce_check.json").read_text(encoding="utf-8"))
    ssb = json.loads((OUT / "F3_ssb_month_provenance.json").read_text(encoding="utf-8"))
    e3b = json.loads((OUT / "F3_E3b_provenance.json").read_text(encoding="utf-8"))
    e3_cases = read_csv(OUT / "F3_E3_cases.csv")
    if e2["holdout_cases_sha256"] != sha(OUT / "work/E2_holdout_cases.csv") or \
       e3prov["E3_cases_sha256"] != sha(OUT / "F3_E3_cases.csv") or \
       not reproduce["all_pass"] or len(secondary) != 69 or \
       len(e3_cases) != 1068 or ssb["cases"] != 8748 or e3b["station_months"] != 166:
        raise RuntimeError("F3B stage output integrity/count mismatch")
    if claims["C2"]["status"] != ("BERHASIL" if e2["C2_X_success"] else "GAGAL") or \
       claims["C3"]["status"] != ("BERHASIL" if e2["C3_success"] else "GAGAL"):
        raise RuntimeError("F3B claims mismatch results")
    station_lines = ["| Stasiun | Cakupan | Bulan | Diterima/kasus | Median r AUTO–DIFI | Abstain |",
                     "|---|---|---:|---:|---:|---:|"]
    for station in ("COI", "KDU", "GUA", "PLR", "TUN", "HUA", "TTB", "MBO"):
        group = [r for r in e3_cases if r["station"] == station]
        accepted = [r for r in group if r["abstained"] == "False"]
        vals = np.array([float(r["r_AUTO_DIFI"]) for r in accepted], dtype=float)
        vals = vals[np.isfinite(vals)]
        median = float(np.median(vals)) if len(vals) else None
        scope = "utama" if group[0]["scope"] == "E3_primary" else "E3b eksploratoris"
        station_lines.append(f"| {station} | {scope} | {len(group)//3} | {len(accepted)}/{len(group)} | " +
                             (f"{median:.3f}" if median is not None else "NA") + f" | {1-len(accepted)/len(group):.1%} |")
    c2x = next(r for r in c2 if r["component"] == "X")
    boundary = {"GUA 2014-01": 10, "KDU 2014-01": 9}
    report = f"""# Fase 3 Tugas B — E2, E3, dan audit klaim

**C1 BERHASIL; C2 GAGAL; C3 GAGAL; C4 DESKRIPTIF; C5 PARSIAL.** Judul yang didukung: *{claims['allowed_title']}*.

## Dasar dan integritas

Protokol F3-v1 SHA-256 `{checks['protocol_v1']}` dan amandemen F3-v1.1 SHA-256 `{checks['amendment_v1p1']}`. E1 tetap beku: konfigurasi `{checks['E1_frozen']}`, CSV holdout `{checks['E1_cases']}`. ZIP review Tugas A tetap `{checks['F3A_zip']}`. Preflight menemukan {frozen_count} keluaran Fase 1–2 cocok hash, 42 ZIP menit dan 3.702 entri G0 tervalidasi. Verifikasi cache reproduksi F3A lulus {len(reproduce['stages'])} tahap; ini **belum** membuktikan satu perintah membangun ulang seluruh Fase 3 dari data mentah (C5 parsial).

## Pelaporan tambahan E1

`F3_E1_secondary_metrics.csv` memuat kandidat tetap, sudut PC1, dan kesepakatan kandidat untuk {len(secondary)} kombinasi metode–topeng–p, dengan penyebut berhingga dicatat. M-EM mencapai 500 iterasi pada {convergence['M_EM_reached_500_iterations']:,}/{convergence['M_EM_cases']:,} kasus ({convergence['capped_fraction_of_M_EM']:.1%}); di antaranya {convergence['capped_below_1e-4_fraction']:.1%} memiliki perubahan akhir <10⁻⁴ nT dan {convergence['capped_below_1e-6_fraction']:.1%} <10⁻⁶ nT. Ini temuan deskriptif, tidak mengubah C1 atau p*. Review amandemen menerima guard M-EM 10⁻⁸ nT dan koreksi GFZ 2018 dengan pengungkapan; topeng DAY setara menurut konstruksi.

## SSB dan E2

SSB memakai {ssb['source_months']} bulan QC≥95% dan {ssb['cases']:,} kasus, `pyDIFI` {ssb['pydifi_version']} dengan `model_name=DIFI8` eksplisit; default pustaka ialah xDIFI2 sehingga tidak dipakai. Kurva DIFI-8 dirata-ratakan atas hari pada jam LT HH:30, lalu dipusatkan. Residu berasal dari observasi yang diisi M-EM dan dipusatkan V1. Hash koefisien DIFI dan F10.7 ada di `F3_ssb_month_provenance.json`. Sebanyak 19 sampel UTC (GUA 2014-01: 10; KDU 2014-01: 9) jatuh pada 31 Desember 2013 karena pergeseran LT; `pyDIFI` memberi peringatan bahwa waktu ini di luar rentang rekomendasi DIFI-8, tetapi menghasilkan nilai. Titik batas itu dipertahankan dan dampaknya belum diuji terpisah.

Pengembangan E2: 58 bulan, 3.132 kasus; tidak ada titik grid dengan coverage strata tanpa topeng ≥80%. Sesuai A-4, dipilih coverage terbesar: **θ_s={e2freeze['theta_s']}, θ_w={e2freeze['theta_w']}, θ_d={e2freeze['theta_d']}**, coverage pengembangan {e2freeze['development_unmasked_coverage']:.2%}. Konfigurasi dibekukan SHA-256 `{sha(frozen_path)}` sebelum holdout. Holdout: 104 bulan, 5.616 kasus; strata utama 2.808 tanpa topeng dan strata bertopeng 2.808 MCAR 20%.

**C2:** untuk X, median selisih berpasangan galat ASAL − AUTO-NA = {float(c2x['median_paired_ASAL_minus_AUTO_NA']):.5f}, CI 95% [{float(c2x['CI95_lower']):.5f}, {float(c2x['CI95_upper']):.5f}]; batas bawah tidak >0. Y/Z ada di `F3_E2_C2.csv`. **C3:** median galat semua AUTO-NA {c3['AUTO_NA_all_median_error']:.5f} versus AUTO diterima {c3['AUTO_accepted_median_error']:.5f}; selisih {c3['median_error_difference']:.5f}, CI 95% [{c3['CI95_lower']:.5f}, {c3['CI95_upper']:.5f}]. Coverage utama {c3['coverage']:.2%} <80%, sehingga C3 gagal walau selisih positif. Seluruh {masked['cases']:,} kasus bertopeng abstain; A3 berlaku pada semuanya (alasan bisa tumpang tindih). Uji α=0: {alpha0['abstained']}/{alpha0['cases']} tidak diterima ({alpha0['abstain_fraction']:.1%}); 31 kasus menghasilkan korelasi kandidat tidak terdefinisi dan dicatat sebagai `ERROR`, tidak disamakan dengan keputusan abstain A1 murni. Residu R masih mengandung variasi Sq nyata menurut konstruksi SSB.

## E3 transfer nyata

E3 utama memakai {e3val['primary_station_months']} bulan di COI, KDU, GUA, PLR, TUN; E3b eksploratoris memakai {e3val['exploratory_station_months']} bulan di HUA, TTB, MBO yang memenuhi syarat manifest Fase 1. E3b menurunkan jam dari ZIP menit beku dengan 60 menit XYZ valid per jam dan aturan A. Pipeline M-EM/V1/S7–S10 serta θ beku dipakai tanpa penyetelan stasiun. DIFI-8 adalah acuan evaluasi utama; korelasi IQD ditandai tidak independen. Lintang geomagnet dihitung dari dipol terpusat IGRF-13 epoch 2015 (`ppigrf` {e3prov['ppigrf_version']}, koefisien dan rumus di `F3_E3_provenance.json`). Audit sesudah perhitungan menemukan lintang geodetik metadata perlu dikonversi ke arah radial geosentris sebelum rumus dipol; hanya kolom lintang geomagnet dikoreksi (maksimum {e3prov['latitude_correction_max_abs_deg']:.5f}°), dengan CSV awal dan hash disimpan di `phase3/work/E3_cases_before_geocentric_lat_fix.csv`. Semua metrik kurva, keputusan abstain, dan hasil E2 tetap identik. Dari {len(e3_cases):,} kasus komponen, {e3val['status_counts'].get('NO_MATRIX_OR_DROPPED_DAY',0)} tidak mempertahankan semua hari setelah M-EM; indeks IQD tidak digeser dan kasus itu abstain.

{chr(10).join(station_lines)}

Rincian per komponen, alasan A1–A4, rasio amplitudo, perbandingan berpasangan terhadap ASAL, lebar pita bootstrap, dan korelasi IQD ada di `F3_E3_cases.csv` serta `F3_E3_station_summary.csv`. Gambar 3 menunjukkan risk–coverage, Gambar 4 transfer menurut lintang dipol, dan Gambar 5 kurva contoh dengan pita 90% untuk COI/KDU/PLR/TUN. Temuan ini deskriptif untuk stasiun yang diuji; tidak mendukung klaim umum “berlaku untuk Indonesia”.

## Klaim dan batas

C1 mendukung kata **Quality-Aware**. C2 gagal, sehingga kombinasi PC dilaporkan sebagai opsi. C3 gagal, sehingga **Uncertainty-Guided** tidak boleh dipakai pada judul atau klaim. C5 parsial karena pembungkus Tugas A menjalankan verifikasi hash cache, bukan pembangunan ulang penuh satu perintah. Paket review hanya memuat laporan, kode, tabel, gambar, log, dan metadata kecil; matriks kerja, ZIP WDC/Mendeley, serta data mentah tidak disertakan. Hasil E1 dan Fase 1–2 tidak diubah.
"""
    (OUT / "F3B_report.md").write_text(report, encoding="utf-8")
    validation = {"schema": "Auto-SqPCA-F3B-v1.1", "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "protocol_amendment_sha256": checks, "phase1_phase2_frozen_outputs_verified": frozen_count,
                  "E2_frozen_sha256": sha(frozen_path), "E2_development_cases": 3132,
                  "E2_holdout_cases": 5616, "E2_holdout_sha256": e2["holdout_cases_sha256"],
                  "theta": {k: e2[k] for k in ("theta_s", "theta_w", "theta_d")},
                  "C2_X_success": e2["C2_X_success"], "C3_success": e2["C3_success"],
                  "unmasked_holdout_coverage": e2["unmasked_coverage"],
                  "masked_abstain_fraction": e2["masked_abstain_fraction"],
                  "E3_station_months": e3prov["station_months"], "E3_component_cases": len(e3_cases),
                  "E3_status_counts": e3val["status_counts"], "claims": {k: claims[k]["status"] for k in ("C1","C2","C3","C4","C5")},
                  "allowed_title": claims["allowed_title"],
                  "DIFI8_UTC_2013_boundary_hours": boundary,
                  "E3_dipole_latitude_correction_max_abs_deg": e3prov["latitude_correction_max_abs_deg"],
                  "E3_original_cases_sha256_before_latitude_fix": e3prov["original_E3_cases_sha256_before_geocentric_lat_fix"],
                  "C5_limit": claims["C5"]["limitation"]}
    (OUT / "F3B_validation.json").write_text(json.dumps(validation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (OUT / "F3B_execution.log").open("a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now(dt.timezone.utc).isoformat()} F3B finalization C2={e2['C2_X_success']} C3={e2['C3_success']} E3_cases={len(e3_cases)} E3b_months={e3val['exploratory_station_months']}\n")
    excluded = {"F3A_review.zip", "F3B_review.zip", "F3B_review.zip.sha256", "F3B_checksums.sha256"}
    files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name not in excluded and
                   not any(x in ("raw", "work", "__pycache__", ".pytest_cache", "_deps") for x in p.relative_to(OUT).parts))
    checksums = OUT / "F3B_checksums.sha256"
    checksums.write_text("".join(f"{sha(p)}  {p.relative_to(OUT).as_posix()}\n" for p in files), encoding="ascii")
    archive = OUT / "F3B_review.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files + [checksums]:
            info = zipfile.ZipInfo(p.relative_to(OUT).as_posix(), date_time=(2026,11,15,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None or any(n.startswith(("raw/", "work/")) for n in z.namelist()):
            raise RuntimeError("F3B review ZIP CRC or raw/work exclusion failed")
    (OUT / "F3B_review.zip.sha256").write_text(f"{sha(archive)}  F3B_review.zip\n", encoding="ascii")
    print(f"F3B_review.zip {archive.stat().st_size} bytes SHA-256 {sha(archive)}")


if __name__ == "__main__":
    main()
