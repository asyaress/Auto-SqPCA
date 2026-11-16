"""Turn completed S7 CSV/JSON evidence into reviewable decisions and a small ZIP."""
from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "phase2a/S7"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(name: str) -> list[dict]:
    with (OUT / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def f(value: str) -> float:
    return float(value)


def main() -> None:
    decision_path = OUT / "S7_decision.json"
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    modes = read_csv("S7_mode_consistency.csv")
    sq = read_csv("S7_sq_baseline_diagnostics.csv")
    manifest = read_csv("S7_benchmark_manifest.csv")
    if not decision["integrity_before"]["all_sha256_match"] or not decision["integrity_after"]["all_sha256_match"]:
        raise RuntimeError("Frozen integrity verification failed")
    if len(modes) != 288 or len(sq) != 1350 or len(manifest) != 684:
        raise RuntimeError(f"Evidence row counts invalid: {len(modes)}, {len(sq)}, {len(manifest)}")
    controls = [r for r in sq if r["record_type"] == "wdc_reconstruction"]
    night = [r for r in controls if r["candidate"] == "night"]
    centered = [r for r in controls if r["candidate"] == "daily_mean"]
    if len(night) != 18 or len(centered) != 18:
        raise RuntimeError("Representative Sq controls must contain 18 XYZ series each")
    mean_equal = max(abs(f(a["rmse_absolute_nT"]) - f(b["rmse_absolute_nT"])) for a, b in zip(
        centered, [r for r in controls if r["candidate"] == "night_then_center"]))
    y_feb = [r for r in modes if r["month"] == "2" and r["observed_component"] == "Y"]
    z_match = [r for r in y_feb if r["prediction_component"] == "Z"]
    y_match = [r for r in y_feb if r["prediction_component"] == "Y"]
    z_2014 = [r for r in modes if r["month"] == "2" and r["scope"] == "per_year" and
              r["year"] == "2014" and r["observed_component"] == "Z" and r["prediction_component"] == "Z"]
    exact_z = sum(f(r["max_abs_direct_nT"]) < 1e-9 for r in z_match)
    best_y_rel = min(f(r["relative_frobenius_residual"]) for r in y_match)
    if exact_z != 21 or best_y_rel < .1:
        raise RuntimeError(f"February Y adjudication inconsistent: exact Z={exact_z}/24, best Y residual={best_y_rel}")
    if decision["status_counts"] != {"VERIFIED": 624, "SUSPECT": 54,
                                      "UNUSABLE_FOR_NUMERIC_BENCHMARK": 6}:
        raise RuntimeError(f"Unexpected quarantine counts: {decision['status_counts']}")
    decision["summary_metrics"] = {
        "february_Y_mode_comparisons_against_Z": len(z_match),
        "february_Y_mode_exact_direct_Z": exact_z,
        "february_Y_mode_best_relative_residual_against_Y": best_y_rel,
        "february_Z_2014_annual_mode_signed_scale_rmse_nT": {
            r["mode"]: f(r["rmse_signed_scale_nT"]) for r in z_2014},
        "Sq_24h_zero_columns": {role: v["columns"] for role, v in decision["sq_profile"].items()},
        "nonfebruary_Sq_control_series": len(night),
        "night_rmse_absolute_range_nT": [min(f(r["rmse_absolute_nT"]) for r in night),
                                         max(f(r["rmse_absolute_nT"]) for r in night)],
        "daily_mean_rmse_absolute_range_nT": [min(f(r["rmse_absolute_nT"]) for r in centered),
                                              max(f(r["rmse_absolute_nT"]) for r in centered)],
        "daily_mean_max_abs_range_nT": [min(f(r["max_abs_absolute_nT"]) for r in centered),
                                       max(f(r["max_abs_absolute_nT"]) for r in centered)],
        "daily_mean_controls_with_max_abs_le_0p1nT": sum(f(r["max_abs_absolute_nT"]) <= .1 for r in centered),
        "daily_mean_equals_night_then_center_max_metric_difference": mean_equal,
        "correlation_range": [min(f(r["correlation"]) for r in centered),
                              max(f(r["correlation"]) for r in centered)]}
    decision["decisions"] = {
        "S7": {"status": "PARTIALLY RESOLVED", "basis": "February Y meanField/mode duplication proven; Y modes follow Z for 10/11 annual years and combined mode1, with Z 2014 and combined mode2 caveats; 24h centering systematic in Sq/SD/S; exact source processing/provenance unresolved"},
        "G1_recommendation": {"status": "HOLD", "basis": "Frozen Level-1 absolute Sq tolerance and source discrepancy unresolved; six Y numeric benchmarks unusable; D1-IQD provisional; proposed exceptions require protocol review/versioning"},
        "D1-IQD": {"status": "PROVISIONAL", "basis": "Official Q5=29 Feb 2016 has best shape in X/Y/Z, but absolute benchmark and source version remain unresolved"},
        "D2-DATA-F": {"status": "UNRESOLVED; deferral proposed for XYZ-only PCA", "basis": "F not used in source PCA input X/Y/Z; original D2 status not retroactively altered"},
        "Y_February_PC_EOF": {"status": "SUSPECT", "basis": "Distinct from Z; own modes invalid as validation targets, independent scientific validity not established"}}
    decision["scripts_sha256"] = {name: sha(OUT / name) for name in ("s7_investigate.py", "s7_finalize.py")}
    decision["source_article"] = "https://arxiv.org/pdf/2103.13899"
    decision["limitations"] = [
        "No author-era WDC snapshot or author calculation/export script, so cause of 24h centering cannot be uniquely identified.",
        "Daily-mean baseline and night-baseline followed by 24h centering are algebraically equivalent, not independent confirmations.",
        "Signed scale in mode comparison is diagnostic; D4 normalization and sign convention remain undecided.",
        "Z February 2014 annual modes do not exactly equal the associated Z PC x EOF; responsible source file not isolated.",
        "No WDC PCA/SVD, D3/D4, physical Sq validation, classifier, DTW or DIFI performed."]
    decision_path.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def mode_row(month: int, mode: int, scope: str, year: str, observed: str, predicted: str) -> dict:
        matches = [r for r in modes if r["month"] == str(month) and r["mode"] == str(mode) and
                   r["scope"] == scope and r["year"] == year and r["observed_component"] == observed and
                   r["prediction_component"] == predicted]
        if len(matches) != 1:
            raise RuntimeError(f"Mode selection ambiguous: {month}, {mode}, {scope}, {year}, {observed}, {predicted}")
        return matches[0]

    report = [
        "# S7-A — Audit kontradiksi benchmark Mendeley dan baseline Sq",
        "",
        "**Keputusan: S7 PARTIALLY RESOLVED. Rekomendasi G1: HOLD.** Enam duplikasi Y/Z Februari dan pemusatan 24 jam seluruh Sq/SD/S terverifikasi. Mekanisme pengolahan/ekspor sumber, seri WDC yang dipakai penulis, dan beberapa inkonsistensi mode tetap belum terpecahkan.",
        "",
        "## Cakupan, sumber, dan aturan",
        "",
        "- Protokol beku `G0-registration-1` dibaca tanpa perubahan. D1-PCA CONFIRMED, D1-IQD PROVISIONAL, D2-TIME CONFIRMED untuk XYZ, D2-DATA F UNRESOLVED, dan D2-BENCHMARK SOURCE_DISCREPANCY tetap sebagaimana dilaporkan.",
        "- [Artikel data Morozova, Rebbah, Ribeiro (2021)](https://arxiv.org/pdf/2103.13899) menyebut Sq lima IQD GFZ dan baseline lima jam malam per hari (00:30, 01:30, 02:30, 03:30, 23:30 menurut tabel jam; teks menulis 02:03). Artikel mendeskripsikan mode sebagai hasil PC dan EOF. Datum Mendeley V1 `10.17632/jcmdrm5f5x.1` dipakai sebagaimana tersimpan di G0.",
        "- Hanya produk `PC × EOF` terbitan Mendeley dihitung, tanpa PCA/SVD baru pada WDC. Produk disusun `outer(EOF_day, PC_hour)` lalu diratakan berurutan hari-jam. Skala bertanda optimal dipasang **hanya untuk diagnosis bentuk**; galat langsung pada skala 1 tetap ditampilkan. Nilai `|r|` sendiri tidak membuktikan amplitudo.",
        "- Sq kontrol memakai lima IQD GFZ resmi, baseline per hari dari indeks jam UTC `[0,1,2,3,23]`, tanpa interpolasi. Enam bulan kontrol dipilih karena 5×24 nilai X/Y/Z valid: 2008-01, 2008-03, 2012-06, 2016-10, 2017-06, 2017-10. Toleransi Tingkat 1 Sq maksimum absolut ≤0,1 nT **tidak diubah**.",
        "",
        "## A. Enam pasangan Y/Z Februari",
        "",
        "Keenam pasangan berikut identik **byte demi byte**; header, jumlah baris, dan kolom juga identik. Hash di bawah adalah SHA-256 yang sama untuk Y dan Z; path lengkap kedua sisi ada di `S7_decision.json` dan manifest.",
        "",
        "| Keluaran | Cakupan | Baris × kolom | SHA-256 Y=Z |",
        "|---|---|---:|---|",
    ]
    for pair in decision["duplicate_pairs"]:
        report.append(f"| {pair['role']} | {pair['scope']} | {pair['rows']}×{pair['columns']} | `{pair['sha256_y']}` |")
    report += ["", "### Rekonstruksi PC × EOF dan kontrol tetangga", "",
               "Tabel ini memuat tahun 2008 untuk kontrol Januari/Februari/Maret, serta keluaran gabungan. RMSE fit dan residu Frobenius relatif memakai skala bertanda optimal; RMSE langsung memakai faktor 1. Residu relatif 0 berarti bentuk beserta skala bertanda cocok.", "",
               "| Bulan | Mode | Cakupan | Mode berlabel Y vs PC×EOF | Skala fit | RMSE langsung (nT) | RMSE fit (nT) | Residu relatif |",
               "|---:|---:|---|:---:|---:|---:|---:|---:|"]
    for month in (1, 2, 3):
        for mode in (1, 2):
            for scope, year in (("per_year", "2008"), ("all_years", "all")):
                for predicted in "YZ":
                    r = mode_row(month, mode, scope, year, "Y", predicted)
                    report.append(f"| {month:02d} | {mode} | {year} | Y←{predicted} | {f(r['fitted_scale_signed']):.6f} | {f(r['rmse_direct_nT']):.4g} | {f(r['rmse_signed_scale_nT']):.4g} | {f(r['relative_frobenius_residual']):.4g} |")
    report += ["", "Pada Februari, mode Y per tahun cocok **persis** dengan PC×EOF Z pada 10 dari 11 tahun untuk masing-masing mode; tahun 2014 adalah pengecualian karena mode Z sendiri tidak cocok persis dengan PC×EOF Z. Mode gabungan 1 cocok persis; mode gabungan 2 adalah negatif PC×EOF Z (skala −1, residu fit ~nol). Mode Y tidak cocok dengan PC×EOF Y bahkan setelah tanda/skala bebas. Januari 2008 dan Maret 2008 menunjukkan mode Y cocok dengan Y sendiri pada skala 1 dan tidak cocok dengan Z. Ini mendukung salah label/salin pada enam berkas, tanpa membuktikan proses yang menyebabkan kesalahan itu.",
               "", "Pengecualian tambahan: Z Februari 2014 per tahun memiliki RMSE setelah skala bertanda 0,7439 nT (mode 1) dan 0,3409 nT (mode 2); file PC, EOF, dan mode mana yang bertanggung jawab belum dapat ditentukan. Januari 2010 Y memiliki residu kecil 0,00035/0,00023 nT untuk mode 1/2. Mode gabungan 2 Maret Z juga berbeda tanda (−1) tetapi tepat setelah tanda diperhitungkan. Normalisasi final masih D4.",
               "", "**Adjudikasi:** enam berkas Februari berlabel Y untuk `meanField`, `mode1`, `mode2` (tahunan/gabungan) **UNUSABLE_FOR_NUMERIC_BENCHMARK** komponen Y. PC/EOF Y Februari berbeda dari Z dan tetap **SUSPECT**, dapat diuji secara independen kelak tetapi tidak divalidasi menggunakan mode Y yang salah label. Enam berkas Z Februari per tahun yang terkait PC/EOF/mode 1/2 diberi **SUSPECT** karena kasus 2014; berkas Z lainnya tidak otomatis gagal.",
               "", "## B. Baseline Sq dan pola seluruh bulan", "",
               "Ke-36 DAT IQD berisi masing-masing 24 jam × 37 kolom (`h` dan 12 kolom per Sq, SD, S). Dari 432 kolom per jenis, maksimum nilai mutlak mean 24 jam adalah:", "",
               "| Jenis | Kolom | Maks. |mean 24 jam| (nT) | Kolom dengan |mean malam| >0,1 nT | Median |mean malam| (nT) |",
               "|---|---:|---:|---:|---:|"]
    for role, q in decision["sq_profile"].items():
        report.append(f"| {role} | {q['columns']} | {q['max_abs_mean24_nT']:.3g} | {q['night_abs_gt_0p1_count']} | {q['median_abs_night_mean_nT']:.4f} |")
    report += ["", f"Identitas internal `S = Sq + SD` juga diperiksa pada 432 kombinasi komponen/bulan/tahun; maksimum |S−Sq−SD| = {decision['S_minus_Sq_minus_SD_max_abs_nT']:.3g} nT. Jadi kolom Sq, SD, dan S konsisten secara aljabar.",
               "", "Pemusatan mean 24 jam adalah sifat **sistematis** seluruh berkas IQD Mendeley, bukan hanya Februari. Ini belum menentukan apakah penulis memakai baseline mean harian sejak awal, menambahkan pemusatan sesudah baseline malam, atau melakukan transformasi saat ekspor. Dua rumus terakhir yang dibandingkan di bawah (`daily_mean` dan `night_then_center`) ekuivalen secara aljabar untuk rerata linear, sehingga tidak dihitung sebagai dua konfirmasi terpisah.",
               "", "### Pembandingan enam bulan di luar Februari", "",
               "RMSE bentuk = RMSE sesudah offset rerata 24 jam selisih dihilangkan; kolom maksimum untuk `daily_mean` adalah maksimum absolut selisih per jam, relevan ke ambang beku. Semua besaran kecuali korelasi dalam nT.", "",
               "| Tahun-bulan | Komp. | IQD Q1–Q5 | RMSE malam abs. | RMSE mean harian abs. / bentuk | Maks. abs. mean harian | r | Offset malam |",
               "|---|:---:|---|---:|---:|---:|---:|---:|"]
    for a, b in zip(night, centered):
        if any(a[k] != b[k] for k in ("year", "month", "component")):
            raise RuntimeError("Sq night/centered row order mismatch")
        report.append(f"| {a['year']}-{int(a['month']):02d} | {a['component']} | {a['iqd_days'].replace('|', ',')} | {f(a['rmse_absolute_nT']):.4f} | {f(b['rmse_absolute_nT']):.4f} | {f(b['max_abs_absolute_nT']):.4f} | {f(b['correlation']):.6f} | {f(a['offset_mean_residual_nT']):+.4f} |")
    report += ["", f"Pada 18 kontrol XYZ, RMSE absolut malam {decision['summary_metrics']['night_rmse_absolute_range_nT'][0]:.4f}–{decision['summary_metrics']['night_rmse_absolute_range_nT'][1]:.4f} nT; setelah mean harian {decision['summary_metrics']['daily_mean_rmse_absolute_range_nT'][0]:.4f}–{decision['summary_metrics']['daily_mean_rmse_absolute_range_nT'][1]:.4f} nT, dengan r {decision['summary_metrics']['correlation_range'][0]:.6f}–{decision['summary_metrics']['correlation_range'][1]:.6f}. Namun maksimum absolut mean harian {decision['summary_metrics']['daily_mean_max_abs_range_nT'][0]:.4f}–{decision['summary_metrics']['daily_mean_max_abs_range_nT'][1]:.4f} nT: **0/18** memenuhi ≤0,1 nT. Kecocokan bentuk sangat kuat, tetapi reproduksi numerik Tingkat 1 tetap gagal pada kontrol ini.",
               "", "**Pemisahan hipotesis:** offset beberapa nT tidak dijelaskan oleh kuantisasi WDC 0,1 nT saja. Kuantisasi/pembulatan dapat berkontribusi ke residu bentuk kecil, tetapi 0,17–0,34 nT maksimum setelah pemusatan tidak boleh langsung dianggap akibat pembulatan. Versi WDC saat penulis menghitung data dan langkah pemusatan/ekspor tidak tersedia; kedua hal itu belum dapat dipisahkan. Duplikasi Y/Z sudah terbukti pada isi file, sedangkan alasan kesalahan ekspor/salin hanya hipotesis. Tidak ada validasi fisis Sq di S7.",
               "", "## C. Karantina dan implikasi gate", "",
               "`S7_benchmark_manifest.csv` mencakup **seluruh 684 DAT numerik** Mendeley, path asli, SHA-256, ukuran, status, dan batas pemeriksaan. Plot PNG tetap tercatat di inventaris G0, tetapi bukan benchmark DAT numerik. Ringkasan status: **624 VERIFIED, 54 SUSPECT, 6 UNUSABLE_FOR_NUMERIC_BENCHMARK**. VERIFIED berarti tidak ditemukan kontradiksi pada pemeriksaan yang dilakukan, bukan jaminan validitas ilmiah penuh. Tidak ada DAT yang diubah atau referensi turunan yang dipromosikan menjadi ORIGINAL.",
               "", "- **Lokal/sistematis:** duplikasi label Y/Z terbatas enam berkas Februari di antara pasangan yang diperiksa D2; satu inkonsistensi Z 2014 memerlukan pemeriksaan kelak. Mean 24 jam nol berlaku sistematis pada Sq, SD, S sepanjang 12 bulan dan 12 kolom tahun/gabungan.",
               "- **D1-IQD tetap PROVISIONAL:** Q5 resmi 29 Februari 2016 unggul dalam bentuk menurut D1, tetapi offset absolut dan provenans versi WDC belum tuntas. D2-TIME sudah mengonfirmasi pemetaan HH:00 WDC ke jendela 00–59 menit untuk XYZ, sehingga ketidakpastian waktu berkurang tanpa menuntaskan benchmark.",
               "- **F dapat diajukan untuk ditunda pada jalur PCA XYZ:** artikel sumber menyebut hanya X/Y/Z sebagai masukan PCA; ini tidak mengubah D2-DATA F yang masih UNRESOLVED. Keputusan penundaan perlu dicatat pada versi protokol baru.",
               "- **G1 HOLD:** ambang Sq absolut beku tidak terpenuhi pada kontrol; enam target Y numerik tidak dapat dipakai; D1-IQD provisional dan inkonsistensi Z 2014 masih ada. G1 CONDITIONAL PASS baru layak dipertimbangkan setelah amandemen yang membatasi benchmark diterima dan bukti tambahan sesuai kriteria tertulis tersedia. Proposal terpisah di bawah belum berlaku.",
               "", "## Reproduksibilitas dan batas", "",
               "Jalankan `python -B phase2a/S7/s7_investigate.py` lalu `python -B phase2a/S7/s7_finalize.py`. Input hash per DAT ada di manifest, hash pasangan duplikat dan input representatif ada di `S7_decision.json`, serta setiap baris mode/Sq mencatat path/hash yang dipakai. Hash 3.659 raw, 11 ZIP menit beku, dan 16 berkas G0/D1/D2/protokol cocok **sebelum dan sesudah** komputasi. CSV mencatat 288 pembandingan mode dan 1.350 baris Sq (1.296 kolom asli + 54 rekonstruksi); log menyimpan tahapan dan kesalahan asli bila muncul. Python/NumPy/platform dicatat di JSON. ZIP review hanya berisi kode, tabel, laporan, JSON, dan log kecil. Tidak ada unduhan, PCA/SVD WDC, D3/D4, DTW, DIFI, atau classifier.",
               "", "**Keputusan akhir: S7 PARTIALLY RESOLVED; G1 HOLD.**"]
    (OUT / "S7_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    proposal = """# Proposal amandemen protokol Fase 2A — S7-A (belum berlaku)

**Status: PROPOSED FOR REVIEW.** Protokol `G0-registration-1` dan semua artefak Fase 1/G0/D1/D2 tetap beku. Versi usulan: `G0-registration-2-S7-draft`, 13 November 2026. Proposal ini belum mengubah keputusan historis ataupun mengaktifkan perhitungan D3/D4.

## Perubahan yang diusulkan

1. Tambahkan daftar karantina berbasis SHA-256 dari `S7_benchmark_manifest.csv`. Enam `COI_Y_{meanField,mode1,mode2}_m02[ _y_all].dat` (nama tepat tercatat dalam manifest) dikeluarkan hanya dari benchmark numerik **Y Februari**. Tetap tersedia baca saja sebagai bukti sumber. Y PC/EOF/VF Februari diklasifikasikan SUSPECT dan diuji independen terhadap WDC di tahap yang memang mengizinkannya; jangan gunakan mode Y yang salah label sebagai validator. Enam berkas Z Februari per tahun terkait PC/EOF/mode 1/2 tetap SUSPECT sampai anomali 2014 dilokalisasi. Semua pengecualian harus dicatat dalam metrik cakupan dan tidak boleh dianggap PASS otomatis.
2. Pertahankan rumus Sq IQD protokol: baseline malam lima jam per hari pada lima IQD GFZ, termasuk 29 Februari 2016 secara **provisional**. Tambahkan perbandingan sekunder kurva setelah offset rerata 24 jam dihilangkan, diberi label `SHAPE_ONLY` atau `RECONSTRUCTED` bila disimpan. Tidak boleh menggantikan seri ORIGINAL Mendeley atau mengubah ambang Tingkat 1 selisih maksimum absolut ≤0,1 nT. Perbandingan `daily_mean` dan `night_then_center` dilaporkan sebagai satu kelas ekuivalen, bukan dua hipotesis independen.
3. Untuk jalur PCA yang hanya memakai X/Y/Z, izinkan F dinyatakan `DEFERRED_FOR_XYZ_PCA` setelah review. Status D2-DATA F tetap UNRESOLVED pada laporan beku dan harus kembali diperiksa jika tahap lain memakai F.
4. Pertahankan G1 HOLD sampai ruang lingkup benchmark, perlakuan seri SUSPECT, dan kriteria lulus bersyarat ditetapkan **sebelum** D3/D4. Jika paket amandemen diterima, nilai ulang G1 sebagai CONDITIONAL PASS hanya setelah reviewer memastikan gate dapat menilai D1/D2 tanpa memakai target tidak sah. Jangan menandai G1 PASS atau menyatakan Tingkat 1 Sq tercapai dari kecocokan bentuk.

## Dampak dan jejak perubahan

- G1: membutuhkan keputusan review eksplisit tentang karantina dan D1-IQD; status saat ini HOLD.
- G2/G3 serta replikasi penuh: denominator cakupan, komponen/bulan yang dikecualikan, dan metrik absolut vs bentuk harus dibedakan. Kegagalan Tingkat 1 pada seri lain tetap kegagalan.
- Data asli, SHA-256, nama/path, dan protokol asal tidak berubah. Implementasi hanya boleh memakai lapisan baca yang memeriksa hash dan mengeluarkan flag; referensi turunan harus bernama `RECONSTRUCTED`.
- Setiap adopsi harus mendapat nomor versi baru, tanggal, alasan berbasis S7, dan pencatatan pengaruh terhadap ambang serta cakupan sebelum eksperimen selanjutnya. Pembatalan dilakukan dengan kembali ke aturan `G0-registration-1` dan menjaga artefak S7 sebagai bukti.

## Bukti dasar

Enam hash Y/Z identik ada di `S7_decision.json`. Februari Y mode cocok dengan produk PC×EOF Z pada 10/11 tahun untuk masing-masing mode; Z 2014 menyisakan inkonsistensi. Semua 432 kolom Sq memiliki mean 24 jam ≤1,95×10⁻¹² nT; 18 kontrol luar Februari memiliki maksimum selisih sesudah pemusatan 0,1725–0,3425 nT, sehingga 0/18 memenuhi ambang 0,1 nT. Detail, hash, dan keterbatasan ada di laporan dan CSV.
"""
    (OUT / "S7_protocol_amendment_proposal.md").write_text(proposal, encoding="utf-8")
    with (OUT / "S7_execution.log").open("a", encoding="utf-8") as log:
        log.write("INFO S7 report/proposal/decision finalized; S7 PARTIALLY RESOLVED; G1 HOLD\n")
    files = ["s7_investigate.py", "s7_finalize.py", "S7_report.md", "S7_benchmark_manifest.csv",
             "S7_mode_consistency.csv", "S7_sq_baseline_diagnostics.csv", "S7_decision.json",
             "S7_protocol_amendment_proposal.md", "S7_execution.log"]
    checksums = "".join(f"{sha(OUT / name)}  {name}\n" for name in files)
    (OUT / "S7_checksums.sha256").write_text(checksums, encoding="utf-8")
    files.append("S7_checksums.sha256")
    zip_path = OUT / "S7_review.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 13, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, (OUT / name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED,
                             compresslevel=9)
    with zipfile.ZipFile(zip_path) as archive:
        if archive.testzip() is not None or sorted(archive.namelist()) != sorted(files):
            raise RuntimeError("S7 review ZIP CRC or member set failed")
        for name in files:
            if archive.read(name) != (OUT / name).read_bytes():
                raise RuntimeError(f"ZIP member mismatch: {name}")
    print(f"S7 PARTIALLY RESOLVED; G1 HOLD; ZIP={zip_path.stat().st_size} bytes, sha256={sha(zip_path)}")


if __name__ == "__main__":
    main()
