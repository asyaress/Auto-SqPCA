"""Final audit report and small review package for G4-R."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import zipfile
from pathlib import Path

import g4r_run as run

HERE = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return run.g2r.sha(path)


def write(name: str, content: str) -> None:
    (HERE / name).write_text(content, encoding="utf-8")


def format_kappa(item: dict) -> str:
    return f"{item['kappa']:.4f}" if item["kappa"] is not None else "tidak terdefinisi†"


def main() -> None:
    frozen_count = run.verify_frozen()
    result = json.loads((HERE / "G4R_result.json").read_text(encoding="utf-8"))
    g3 = json.loads((HERE / "G3R_denominator.json").read_text(encoding="utf-8"))
    rule = json.loads((HERE / "G4R_rule_consistency.json").read_text(encoding="utf-8"))
    sq = json.loads((HERE / "G4R_sq_provenance.json").read_text(encoding="utf-8"))
    preflight = json.loads((HERE / "G4R_preflight.json").read_text(encoding="utf-8"))
    if result["label"] != "D-AGREE" or result["denominator"]["eligible"] != g3["main_eligible"]:
        raise RuntimeError("Agreement and G3-R denominator mismatch")
    if g3["cache_sha256"] != sha(HERE / "G4R_pca_cache.npz") or sq["cache_sha256"] != sha(HERE / "G4R_sq_cache.npz"):
        raise RuntimeError("Derived cache SHA-256 mismatch")
    if "7 passed" not in (HERE / "G4R_unit_tests.log").read_text(encoding="utf-8"):
        raise RuntimeError("Required unit and adapter tests not all passed")
    long = run.csv_read("G4R_classification_long.csv")
    agreement = run.csv_read("G4R_agreement.csv")
    sq_rows = run.csv_read("G4R_sq_iqd_own.csv")
    if len(long) != 10836 or len(agreement) != 2709 or len(sq_rows) != 10368:
        raise RuntimeError(f"Unexpected output rows: class={len(long)}, agreement={len(agreement)}, Sq={len(sq_rows)}")
    if any(r["year"] == "2016" and r["month"] == "2" and "29" not in r["gfz_quiet_days"].split(",") for r in sq_rows):
        raise RuntimeError("Official GFZ Feb 2016 29th not used")
    if run.csv_read("G4R_disagreements_outside_zone.csv"):
        raise RuntimeError("Outside-zone mismatch file unexpectedly nonempty")
    denominator = result["denominator"]
    if denominator["excluded"] + denominator["suspect"] + denominator["unresolved"] + denominator["eligible"] != denominator["target_total"]:
        raise RuntimeError("Exclusive denominator categories do not sum to target_total")
    protocol_sha = sha(HERE / "G4R_protocol_v1.md")
    changes = f"""# G4-R — catatan transisi dan pelaksanaan

- Protokol G4R-v1 diberikan sebagai APPROVED; SHA-256 `{protocol_sha}`. Ini protokol G4-R, bukan amandemen G0–G2-R. Status G1 registration-2/3 tetap HOLD dan label G2-R tetap S-DEVIATE.
- R1/R2 dari bagian 0 protokol dicatat sebagai **HASIL_LOKAL_G2R**: V1 unggul pada pengembangan, sedangkan holdout struktur 3/9 lulus. Tidak dipakai untuk mengubah ambang atau label G2-R.
- R3 dicatat sebagai **ANALISIS_REVIEWER**: batas |r| ≥0,999 dan galat Frobenius ≤1% mengukur hal berbeda dan secara geometri tidak setara. Label S-DEVIATE tidak diubah.
- R4 dicatat sebagai **HIPOTESIS_BELUM_DIUJI**: galat absolut sekitar 0,05 nT mungkin tampak besar relatif pada Sq yang lemah. Tidak diuji sebagai sebab di G4-R.
- Enam uji klasifikasi sintetis lulus sebelum data nyata; uji konsistensi aturan memberi {rule['same_decision']}/{rule['outside_sensitive_zone']} keputusan sama di luar zona. Uji ketujuh memeriksa adaptor VF.
- Kegagalan upaya awal G3-R tercatat verbatim: `RuntimeError: phase2a/raw/mendeley/jcmdrm5f5x-1/Datasets of the solar quiet (Sq) and solar disturbed (SD) variations of the geomagnetic field at a midlatitudinal station in Europe obtained by different methods/PCA modes/X/m01 - January/data files/mode 1/COI_X_VF1_m01.dat lacks y.2007`. DAT VF tidak mempunyai header; baris `y.2007` adalah data pertama. Adaptor G4-R membaca baris pertama itu dan mendelegasikan baris lain ke loader beku. Upaya awal dihentikan tanpa metrik final, adaptor diuji, lalu G3-R dijalankan ulang sekali. File kode dan konfigurasi G2-R tidak diubah.
- Kelayakan seri memakai kebijakan S7-B/S7-C dengan cakupan seri yang dijelaskan protokol G4-R: Y Februari EXCLUDED; Z Februari 2014 dan gabungan serta X empat bulan 2008 dan gabungan SUSPECT_DIAGNOSTIC. Beberapa seri suspect juga mempunyai jam hilang dan berada pada kategori eksklusif UNRESOLVED_MISSING.
- `DEVELOPMENT_SEEN` dilaporkan sebagai bendera yang tumpang tindih. Penyebut D-agreement utama adalah perbandingan retrospektif semua seri eligible; strata yang belum terlihat dilaporkan tersendiri. Tidak ada klaim evaluasi prospektif dari penyebut utama.
- Surrogate IC1 mengacak fase deret **acuan Sq**, mempertahankan amplitudo FFT, DC dan Nyquist. Seed 20261113 dipakai konsisten per acuan/matriks. P-value memakai 1.000 surrogate dan koreksi +1.
- Tidak ada DIFI, DTW, CM5, classifier ML, atau analisis stasiun K11. Kategori X dari tabel asli tidak diklaim direplikasi.
"""
    write("G4R_changes.md", changes)
    kappa_lines = ["| Komponen | PC1 κ | PC2 κ | PC3 κ |", "|:---:|---:|---:|---:|"]
    for c in "XYZ":
        kappa_lines.append("| " + c + " | " + " | ".join(format_kappa(result["kappa"][c][p]) for p in ("PC1", "PC2", "PC3")) + " |")
    sanity_lines = ["| Komponen | P-own ≥0,88 | P-pub ≥0,88 |", "|:---:|---:|---:|"]
    for c in "YZ":
        a, b = result["sanity_CR4"][c]["P-own"], result["sanity_CR4"][c]["P-pub"]
        sanity_lines.append(f"| {c} | {a['ge_0p88']}/{a['n']} ({a['percent']:.2f}%) | {b['ge_0p88']}/{b['n']} ({b['percent']:.2f}%) |")
    report = f"""# G4-R — kesesuaian keputusan pemilihan PC

**Label D-agreement: {result['label']}.** P-own dan P-pub memberi keputusan sama pada {denominator['agree']}/{denominator['eligible']*7} kandidat dari {denominator['eligible']} matriks eligible. Enam ketidaksepakatan berada di zona sensitif; **nol** di luar zona. Sebanyak {result['eligible_matrix_all7_agree']}/{denominator['eligible']} matriks sepakat pada ketujuh kandidat. Ini kesesuaian keputusan aturan yang didaftarkan dalam G4R-v1, bukan replikasi tabel klasifikasi X berbasis DIFI3 + DTW. Label struktur G2-R **S-DEVIATE** dan G1 registration-2/3 **HOLD** tetap.

## Integritas dan aturan

Protokol SHA-256 `{protocol_sha}`. Preflight memverifikasi {preflight['G0_manifest_rows']:,} entri manifest G0, {preflight['G0_S7C_prior_hashes_checked']} hash historis G0–S7-C, konfigurasi V1 G2-R SHA-256 `{preflight['G2R_config_sha256']}`, kode PCA beku, dan paket G2-R. {frozen_count} hash artefak beku cocok hingga akhir G4-R. Tidak ada sumber atau artefak lama ditimpa.

Aturan: |r| Pearson ≥0,45 dan p<0,05; 1.000 surrogate acak-fase acuan dengan seed 20261113, DC/Nyquist tetap, p=(1+jumlah surrogate ≥|r| observasi)/1.001. Zona sensitif ialah |r| dalam ±0,02 dari 0,45 atau p dalam ±0,01 dari 0,05 pada salah satu pipeline. Kombinasi PC memakai bobot rata-rata EOF dari masing-masing pipeline. Enam uji aturan lulus sebelum data nyata; uji konsistensi sintetis {rule['same_decision']}/{rule['outside_sensitive_zone']} di luar zona ({rule['same_fraction']:.1%}).

## G3-R deskriptif

V1 beku dijalankan pada {g3['target_total']} target: {g3['annual_target']} tahunan dan {g3['combined_target']} gabungan. Status eksklusif: {denominator['eligible']} eligible, {denominator['suspect']} suspect yang dapat dihitung, {denominator['excluded']} excluded, {denominator['unresolved']} unresolved missing. Pada {denominator['eligible']} eligible, {g3['main_frob_pass']} memenuhi galat Frobenius ≤1% dan {g3['main_all_metrics_pass']} memenuhi seluruh metrik struktur G2-R. Angka ini **deskriptif tanpa label struktur baru**. Detail setiap matriks ada di `G3R_structure_metrics.csv`; target yang tidak dapat dihitung tidak diganti.

## Acuan Sq IQD dan keputusan

Semua {sq['references_available']} acuan Sq_IQD sendiri tersedia. Untuk setiap IQD, rata-rata jam malam indeks 0,1,2,3,23 UTC dikurangkan dari 24 nilai per jam, lalu lima hari Q1–Q5 GFZ dirata-ratakan. Acuan gabungan merata-ratakan 11 kurva tahunan (55 IQD). Februari 2016 memakai Q1–Q5 **22,28,27,21,29**; status D1-IQD tetap **PROVISIONAL**. Offset antara acuan sendiri dan Mendeley tidak mengubah |r|.

Penyebut target: {denominator['target_total']}; excluded {denominator['excluded']}; suspect dihitung terpisah {denominator['suspect']}; unresolved {denominator['unresolved']}; eligible {denominator['eligible']}. Bendera DEVELOPMENT_SEEN ada pada {denominator['development_seen']} target dan tumpang tindih kategori status; {result['development_seen_stratum']['matrices']} di antaranya eligible. Strata eligible yang belum terlihat berisi {result['unseen_stratum_diagnostic']['matrices']} matriks dengan {result['unseen_stratum_diagnostic']['candidate_agree']} keputusan kandidat sama dan {result['unseen_stratum_diagnostic']['disagree_in_zone']} selisih dalam zona; ini pemeriksaan diagnostik, bukan klaim prospektif baru. Kasus suspect dan Februari dilaporkan terpisah dalam `G4R_result.json`.

{chr(10).join(kappa_lines)}

† κ tidak terdefinisi bila kedua marginal keputusan konstan (P_o=P_e=1), meskipun kesepakatan observasi 100%; tidak diberi nilai 1 secara artifisial. Rincian n dan P_o/P_e ada di `G4R_result.json`.

Sanity CR4 pada penyebut eligible:

{chr(10).join(sanity_lines)}

Keduanya melewati batas berhenti 90%; angka lokal bukan 100% yang dilaporkan artikel. `G4R_agreement.csv` memuat keputusan, r, p, dan zona untuk seluruh kandidat empat pipeline. Perbandingan diagnostik mempunyai {result['diagnostic_comparisons']['own_vs_mixA_disagreements']} selisih P-own/P-mixA, {result['diagnostic_comparisons']['pub_vs_mixA_disagreements']} P-pub/P-mixA, dan {result['diagnostic_comparisons']['pub_vs_mixB_disagreements']} P-pub/P-mixB pada penyebut eligible. Daftar ketidaksepakatan utama di luar zona kosong (`G4R_disagreements_outside_zone.csv`).

## Batas klaim

Penyebut utama bersifat retrospektif dan memuat seri DEVELOPMENT_SEEN yang ditandai; hasil tidak diklaim prospektif. Enam ketidaksepakatan terletak di dekat ambang, dan hasil p bergantung pada pilihan 1.000 surrogate/seed yang dibekukan di protokol. Y Februari tetap excluded; beberapa matriks dengan jam batas bulan kosong tidak dihitung; keluaran X tidak menyamai kategori DIFI3 + DTW artikel. Hipotesis review bahwa Sq lemah menjelaskan galat relatif tidak diuji. Langkah berikutnya adalah Fase 3 menurut protokol terpisah.
"""
    write("G4R_report.md", report)
    validation = {"schema": "Auto-SqPCA-G4R-v1", "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "protocol_sha256": protocol_sha, "G2R_config_sha256": preflight["G2R_config_sha256"],
                  "G0_manifest_rows_verified": preflight["G0_manifest_rows"],
                  "frozen_files_verified_unchanged": frozen_count,
                  "unit_tests_passed": 7, "rule_consistency": rule,
                  "G3R_denominator": g3, "G4R_label": result["label"],
                  "G4R_denominator": denominator, "G1_registration2": "HOLD", "G1_registration3": "HOLD",
                  "G2R_label": "S-DEVIATE", "pca_cache_sha256": g3["cache_sha256"],
                  "sq_cache_sha256": sq["cache_sha256"]}
    run.jwrite("G4R_validation.json", validation)
    run.log(f"Finalized G4-R report: {result['label']}, {denominator['eligible']} eligible, {denominator['disagree_outside_zone']} outside-zone disagreements")
    excluded_names = {"G4R_review.zip", "G4R_review.zip.sha256", "G4R_checksums.sha256",
                      "G4R_pca_cache.npz", "G4R_sq_cache.npz"}
    included = sorted(p for p in HERE.rglob("*") if p.is_file() and p.name not in excluded_names and
                      not any(x in {"__pycache__", ".pytest_cache"} for x in p.relative_to(HERE).parts))
    write("G4R_checksums.sha256", "".join(f"{sha(p)}  {p.relative_to(HERE).as_posix()}\n" for p in included))
    zip_path = HERE / "G4R_review.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for p in included + [HERE / "G4R_checksums.sha256"]:
            info = zipfile.ZipInfo(p.relative_to(HERE).as_posix(), date_time=(2026, 11, 13, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(zip_path) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("G4R_review.zip CRC failed")
        if any(name.endswith(".npz") or "raw/" in name for name in archive.namelist()):
            raise RuntimeError("Review package contains derived cache or raw data")
    write("G4R_review.zip.sha256", f"{sha(zip_path)}  G4R_review.zip\n")
    print(f"G4R_review.zip {zip_path.stat().st_size} bytes sha256={sha(zip_path)}")


if __name__ == "__main__":
    main()
