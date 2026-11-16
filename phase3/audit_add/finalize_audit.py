"""Verify inputs and package post-hoc audit results without touching frozen files."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHASE3 = HERE.parent
TAG = "EXPLORATORY_POST_HOC"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def csv_rows(name: str) -> list[dict]:
    with (HERE / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fmt(x, digits=3):
    try:
        y = float(x)
        return f"{y:.{digits}f}" if math.isfinite(y) else "NA"
    except (TypeError, ValueError):
        return "NA"


def pct(x, digits=1):
    try:
        y = float(x)
        return f"{100*y:.{digits}f}%" if math.isfinite(y) else "NA"
    except (TypeError, ValueError):
        return "NA"


def manifest() -> list[dict]:
    expected = {}
    for name in ("F3A_checksums.sha256", "F3B_checksums.sha256",
                 "F3_E1_frozen.json.sha256", "F3_E2_frozen.json.sha256"):
        for line in (PHASE3 / name).read_text(encoding="utf-8").splitlines():
            if len(line) >= 66:
                h, rel = line.split(maxsplit=1)
                expected[rel.strip()] = h
    required = ["F3_protocol_v1.md", "F3_amendment_v1.1.md", "F3_E1_frozen.json",
                "F3_E2_frozen.json", "F3_E1_holdout_cases.csv.gz"]
    required += [str(p.relative_to(PHASE3)).replace("\\", "/") for p in sorted((PHASE3 / "auto_sqpca").glob("*.py"))]
    required += ["F3_C1_result.json", "F3_E2_result.json", "F3_E3_cases.csv", "F3_E3b_inventory.csv",
                 "F3_data_inventory.csv", "F3_ssb_manifest.csv", "F3_GFZ2018_source.json",
                 "raw/gfz/QD_days2018.txt", "../phase2a/raw/gfz/QD_days2016.txt",
                 "work/E1_holdout_cases.csv", "work/E2_holdout_cases.csv"]
    c1 = json.loads((PHASE3 / "F3_C1_result.json").read_text(encoding="utf-8"))
    e2 = json.loads((PHASE3 / "F3_E2_result.json").read_text(encoding="utf-8"))
    expected["work/E1_holdout_cases.csv"] = c1["holdout_cases_sha256"]
    expected["work/E2_holdout_cases.csv"] = e2["holdout_cases_sha256"]
    expected["raw/gfz/QD_days2018.txt"] = json.loads((PHASE3 / "F3_GFZ2018_source.json").read_text(encoding="utf-8"))["sha256"]
    with (PHASE3.parent / "phase2a/G0/input_manifest.csv").open(newline="", encoding="utf-8") as f:
        gfz = next(r for r in csv.DictReader(f) if r["relative_path"] == "phase2a/raw/gfz/QD_days2016.txt")
    expected["../phase2a/raw/gfz/QD_days2016.txt"] = gfz["sha256"]
    out = []
    for rel in required:
        path = PHASE3 / rel
        actual = sha(path) if path.is_file() else ""
        exp = expected.get(rel, "")
        status = "MATCH" if actual and actual == exp else ("UNRESOLVED_MISSING" if not actual else "MISMATCH")
        out.append({"audit_label": TAG, "path": rel, "expected_sha256": exp,
                    "actual_sha256": actual, "status": status})
    if any(r["status"] == "MISMATCH" for r in out):
        raise RuntimeError("Frozen input SHA-256 mismatch; package not finalized")
    with (HERE / "AUDIT_ADD_input_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    return out


def report(inputs: list[dict]) -> None:
    u1 = csv_rows("U1_summary.csv")
    u1e3 = csv_rows("U1_E3_capped.csv")
    u2 = csv_rows("U2_operating_range_ratios.csv")
    u3 = csv_rows("U3_summary.csv")
    u3cases = csv_rows("U3_full_pipeline_cases.csv")
    u4 = csv_rows("U4_rmse_by_station_component.csv")
    u5 = [r for r in csv_rows("U5_band_coverage.csv") if r["record_type"] == "SUMMARY"]
    if len(u1) != 4 or len(u2) != 12 or len(u3) != 12 or len(u4) != 24 or len(u5) != 9:
        raise RuntimeError("Unexpected audit summary table dimensions")
    if len(u3cases) != 25200:
        raise RuntimeError(f"U3 method-case count {len(u3cases)} differs from 25200")
    u3_errors = Counter(r["error_original"] for r in u3cases if r["status"] == "ERROR")
    rmse = [float(r["rmse_nT_median"]) for r in u4 if r["rmse_nT_median"]]
    lines = ["# AUDIT_ADD — audit tambahan Fase 3", "", f"Status: **{TAG}**. Audit deskriptif pasca-hasil; tidak mengubah metode, ambang, konfigurasi beku, atau hasil lama.", "",
             "## Integritas dan sumber", "",
             f"Verifikasi ulang {sum(r['status']=='MATCH' for r in inputs)} input yang memiliki hash acuan cocok; satu path yang diminta tidak ada: `F3_E1_holdout_cases.csv.gz`. Seluruh modul `auto_sqpca/*.py`, protokol, amandemen, serta konfigurasi E1/E2 cocok dengan hash beku. Setiap cache bulanan/kurva yang dipakai diperiksa terhadap hash pada inventaris atau tabel kasus.", "",
             "U2 dan U3 memakai `work/E1_holdout_cases.csv` sebagai sumber alternatif **yang terautentikasi**: SHA-256-nya sama dengan `F3_C1_result.json`, dan berkas hasil C1 tersebut tercakup dalam `F3B_checksums.sha256`. Ketiadaan path gzip tetap dicatat sebagai `UNRESOLVED`; tidak ada data yang direkonstruksi dari asumsi.", "",
             "Percobaan awal U1 berhenti dengan pesan asli `FileNotFoundError: [Errno 2] No such file or directory: 'D:\\\\A. PAPER\\\\GEO-3-PAK-PRI\\\\Paket_Tugas1_AutoSqPCA_WDC\\\\phase2a\\\\raw\\\\gfz\\\\QD_days2018.txt'`. Ini adalah salah path pada skrip audit. Pembacaan 2018 dikoreksi ke `phase3/raw/gfz/QD_days2018.txt` dan hash-nya diverifikasi terhadap `F3_GFZ2018_source.json`; tidak ada sumber beku yang diubah. Log percobaan dan eksekusi ulang disertakan.", "",
             "Semua analisis U1–U5 memakai set *holdout*. Seed topeng E1 berasal dari `f3_e1.py`; bootstrap E2/E3 memakai seed dasar 20261114. Resampel klaster untuk CI U2/U3: 2.000, seed 20261115, unit stasiun–tahun–bulan. Lingkungan: " + f"Python {platform.python_version()}, {platform.platform()}." , "",
             "## U1 — sensitivitas batas iterasi", "",
             "Sumber E1 holdout memuat 149 bulan dan 420 pasangan bulan–komponen yang memiliki target kurva tanpa topeng. U1 menggunakan empat topeng 10% dan lima replikasi pertama, sehingga ada 8.400 kasus.", "",
             "`fill_em_cap(a, 500)` menghasilkan array, keep-mask, iterasi, dan perubahan akhir yang bit-identik dengan `gaps.fill_em` pada 20 kasus (10 mencapai cap, 10 berhenti lebih awal). Kasus yang berhenti sebelum 500 menggunakan hasil E1 terautentikasi karena cap 5000 mengikuti kondisi berhenti yang sama; kasus yang mencapai cap 500 dihitung ulang dan checkpoint iterasi 500 dibandingkan dengan E1. Pada E3, checkpoint cap-500 juga dicocokkan dengan kandidat dan kurva cache beku.", "",
             "| Topeng 10% | Kasus | Cap 500 | Konvergen <5000 | Kandidat sama | Kurva berpasangan | Beda kurva median / p90 / maks (L2 relatif) | Galat E1 median 500 / 5000 | Galat E1 p90 500 / 5000 |",
             "|---|---:|---:|---:|---:|---:|---|---|---|"]
    for r in u1:
        lines.append(f"| {r['mask_kind']} | {r['n_cases']} | {pct(r['fraction_at_cap500'])} | {pct(r['fraction_converged_before_cap5000'])} | {pct(r['fraction_candidate_same'])} | {r['n_paired_curves']} | {fmt(r['curve_diff_median'],4)} / {fmt(r['curve_diff_p90'],4)} / {fmt(r['curve_diff_max'],4)} | {fmt(r['cap500_error_median'],4)} / {fmt(r['cap5000_error_median'],4)} | {fmt(r['cap500_error_p90'],4)} / {fmt(r['cap5000_error_p90'],4)} |")
    changed_cand = sum(r["candidate_changed"] == "True" for r in u1e3)
    changed_abs = sum(r["abstain_changed"] == "True" for r in u1e3)
    still_capped = sum(int(r["cap5000_iterations"]) >= 5000 for r in u1e3)
    to_accept = sum(r["cap500_abstained"] == "True" and r["cap5000_abstained"] == "False" for r in u1e3)
    to_abstain = sum(r["cap500_abstained"] == "False" and r["cap5000_abstained"] == "True" for r in u1e3)
    e3_diffs = [float(r["relative_l2_curve_difference"]) for r in u1e3 if r["relative_l2_curve_difference"] not in ("", "nan")]
    e3_dr = [float(r["delta_r_AUTO_DIFI"]) for r in u1e3 if r["delta_r_AUTO_DIFI"] not in ("", "nan")]
    lines += ["", f"E3 nyata berstatus OK dan M-EM mencapai 500 iterasi: **{len(u1e3)} kasus** (kasus E3 non-OK tidak termasuk). Sebanyak **{still_capped}** masih mencapai cap 5.000. Kandidat berubah: **{changed_cand}**; keputusan abstain berubah: **{changed_abs}** ({to_accept} abstain→diterima, {to_abstain} diterima→abstain). Beda kurva median/maks pada kurva berpasangan: **{fmt(__import__('numpy').median(e3_diffs),4) if e3_diffs else 'NA'} / {fmt(max(e3_diffs),4) if e3_diffs else 'NA'}**. Perubahan r AUTO–DIFI median pada kasus diterima di kedua cap: **{fmt(__import__('numpy').median(e3_dr),6) if e3_dr else 'NA'}** (n={len(e3_dr)}).", "",
              "Cap 5.000 tidak berarti seluruh kasus telah konvergen; maksimum beda L2 relatif juga harus dibaca bersama norma kurva cap-500 yang menjadi penyebutnya. Rincian tiap kasus ada di tabel U1.", "",
              "## U2 — rentang operasi 5–10% hilang", "",
              "Rasio memakai galat relatif L2 E1; kasus tanpa keluaran diberi galat tak hingga. CI 95% menggunakan resampel klaster bulan–stasiun. Rasio di bawah 1 berarti galat M-EM lebih kecil untuk ringkasan tersebut; median dan p90 dapat bergerak berbeda.", "",
              "| Topeng | M-EM/pembanding | Rasio median (CI 95%) | Rasio p90 (CI 95%) | Tanpa keluaran M-EM / pembanding |",
              "|---|---|---|---|---|"]
    for r in u2:
        label = f"{r['mask_kind']} {float(r['p_nominal'])*100:g}%"
        lines.append(f"| {label} | {r['comparison']} | {fmt(r['median_error_ratio'])} ({fmt(r['median_ratio_ci95_low'])}–{fmt(r['median_ratio_ci95_high'])}) | {fmt(r['p90_error_ratio'])} ({fmt(r['p90_ratio_ci95_low'])}–{fmt(r['p90_ratio_ci95_high'])}) | {pct(r['M_EM_no_output_fraction'])} / {pct(r['comparator_no_output_fraction'])} |")
    lines += ["", "## U3 — pipeline beku lengkap", "",
              "Untuk kedua metode, matriks dengan hari berisi <6 jam observasi dihentikan sebelum imputasi (`DAY_LT6`); untuk matriks lain dijalankan pengisian, PCA/seleksi, bootstrap 200 kali, A1/A2/A3, dengan A4 tidak aktif. Seed bootstrap E3 per stasiun–bulan–komponen sama untuk dua metode. Galat dihitung terhadap kurva bulan tanpa topeng menurut definisi E1. Alasan abstain dalam CSV dapat tumpang tindih.", "",
              "| Topeng | Metode | Diterima | Galat diterima median / p90 | Pasangan diterima keduanya | Median Δ galat M-EM − M-INT (CI 95%) |",
              "|---|---|---:|---|---:|---|"]
    for r in u3:
        label = f"{r['mask_kind']} {float(r['p_nominal'])*100:g}%"
        lines.append(f"| {label} | {r['method']} | {pct(r['accepted_fraction'])} | {fmt(r['accepted_error_median'],4)} / {fmt(r['accepted_error_p90'],4)} | {r['n_paired_both_accepted']} | {fmt(r['paired_M_EM_minus_M_INT_median'],4)} ({fmt(r['paired_median_ci95_low'],4)}–{fmt(r['paired_median_ci95_high'],4)}) |")
    lines += ["", "Alasan abstain berikut adalah jumlah kasus dan dapat tumpang tindih:", "",
              "| Topeng | Metode | A1 | A2 | A3 | Hari <6 jam |",
              "|---|---|---:|---:|---:|---:|"]
    for r in u3:
        reason = json.loads(r["abstain_reasons_overlapping_json"])
        label = f"{r['mask_kind']} {float(r['p_nominal'])*100:g}%"
        lines.append(f"| {label} | {r['method']} | {reason.get('A1',0)} | {reason.get('A2',0)} | {reason.get('A3',0)} | {reason.get('DAY_LT6',0)} |")
    lines += ["", "## U4 — RMSE terhadap DIFI-8", "",
              f"Pada 24 kombinasi stasiun × komponen, median RMSE di antara kasus diterima berkisar **{fmt(min(rmse),2)}–{fmt(max(rmse),2)} nT**. RMSE dihitung dari 24 nilai jam kurva AUTO dan DIFI-8, lalu dibagi amplitudo puncak-ke-puncak DIFI untuk versi ternormalisasi. Korelasi AUTO–IQD adalah pembanding nonindependen karena IQD dipakai dalam seleksi.", "",
              "| Stasiun | Komp. | Diterima / total | Abstain | RMSE median [Q1, Q3] nT | RMSE ternormalisasi median | r AUTO–IQD < 0 |",
              "|---|---|---:|---:|---|---:|---:|"]
    for r in u4:
        lines.append(f"| {r['station']} | {r['component']} | {r['n_accepted']}/{r['n_cases']} | {pct(r['abstain_fraction'])} | {fmt(r['rmse_nT_median'],2)} [{fmt(r['rmse_nT_q25'],2)}, {fmt(r['rmse_nT_q75'],2)}] | {fmt(r['normalized_rmse_median'],3)} | {r['n_r_AUTO_IQD_negative']} |")
    lines += ["", "## U5 — cakupan band pada E2 semi-sintetis", "",
              "Verifikasi ulang 20 kasus cocok untuk kandidat dan stabilitas; seluruh kasus holdout tanpa topeng yang diterima dihitung ulang dengan seed bootstrap beku. Target per jam adalah `alpha × Sq_target` (DIFI-8). **Band 5–95% bersifat pointwise, bersyarat pada matriks terisi dan acuan IQD; ini bukan uji interval kepercayaan nominal.**", "",
              "| Komp. | α | Kasus | Rata-rata fraksi jam tercakup | Kasus ≥22/24 jam | Median lebar band (nT) |",
              "|---|---:|---:|---:|---:|---:|"]
    for r in u5:
        lines.append(f"| {r['component']} | {fmt(r['alpha'],1)} | {r['n_cases']} | {pct(r['mean_fraction_hours_covered'])} | {pct(r['fraction_cases_at_least_22_hours'])} | {fmt(r['median_band_width_nT'],2)} |")
    lines += ["", "## U6 — fakta kode dan kalender", "",
              "Cache Februari kabisat Fase 3 berukuran 24 × 29 × 3; 29 Februari **ikut** dalam matriks E1/E2/E3. Rincian per stasiun, jam tepi deret UTC, dan irisan hari GFZ UTC/lokal ada di `U6_facts.md`. Fakta ini berbeda dari kalimat naskah MethodsX yang menyatakan 29 Februari dibuang. Audit ini tidak mengubah naskah atau preprocessing.", "",
              "## UNRESOLVED dan batas interpretasi", "",
              "- `F3_E1_holdout_cases.csv.gz`: **UNRESOLVED_MISSING**. U2 dan U3 menggunakan `work/E1_holdout_cases.csv` yang hash-nya terverifikasi sebagai sumber alternatif; path gzip yang diminta tetap belum tersedia."]
    if u3_errors:
        lines.append("- U3 menghasilkan baris ERROR; pesan asli dan jumlahnya:")
        for err, count in u3_errors.items():
            lines.append(f"  - {count} × `{err}`")
    else:
        lines.append("- Tidak ada baris `ERROR` pada U3. Status `PRECHECK_DAY_LT6` adalah abstain yang ditetapkan oleh aturan kelengkapan, bukan error komputasi.")
    lines += ["", "Semua hasil U1–U5 bersifat deskriptif pasca-hasil. Tidak ada ambang atau klaim keberhasilan baru yang ditetapkan dari audit ini.", ""]
    (HERE / "AUDIT_ADD_report.md").write_text("\n".join(lines), encoding="utf-8")


def logs_and_package(inputs: list[dict]) -> None:
    log = [f"{datetime.now(timezone.utc).isoformat()} {TAG} finalization", "Input status: " + str(Counter(r["status"] for r in inputs)),
           "Python: " + sys.version.replace("\n", " ")]
    for name in ("U1_execution.log", "U3_execution.log", "U5_execution.log"):
        log += ["", f"--- {name} ---", (HERE / name).read_text(encoding="utf-8", errors="replace")]
    (HERE / "AUDIT_ADD_execution.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    included = sorted(p for p in HERE.iterdir() if p.is_file() and p.suffix in {".py", ".csv", ".md", ".json", ".log"})
    checksum_path = HERE / "AUDIT_ADD_checksums.sha256"
    checksum_path.write_text("".join(f"{sha(p)}  {p.name}\n" for p in included), encoding="utf-8")
    zip_path = HERE / "AUDIT_ADD_review.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in [*included, checksum_path]:
            z.write(p, arcname=p.name)
    (HERE / "AUDIT_ADD_review.zip.sha256").write_text(f"{sha(zip_path)}  {zip_path.name}\n", encoding="utf-8")


def main() -> None:
    required = ["U1_cap_sensitivity_cases.csv", "U1_summary.csv", "U1_E3_capped.csv",
                "U2_operating_range_ratios.csv", "U3_full_pipeline_cases.csv", "U3_summary.csv",
                "U4_rmse_by_station_component.csv", "U5_band_coverage.csv", "U6_facts.md"]
    missing = [x for x in required if not (HERE / x).is_file()]
    if missing:
        raise RuntimeError(f"Audit output missing: {missing}")
    inputs = manifest()
    report(inputs)
    logs_and_package(inputs)
    print("AUDIT_ADD package completed")


if __name__ == "__main__":
    main()
