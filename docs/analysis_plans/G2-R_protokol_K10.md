# Protokol G2-R (jalur K10): Implementasi Ulang dengan Deviasi Terdokumentasi — Auto-SqPCA

**Versi:** G2R-v1
**Tanggal:** 13 November 2026
**Status:** APPROVED (peneliti utama, 13 Nov 2026)
**Dasar:** G1 HOLD di bawah G0-registration-2 dan G0-registration-3 (baris 0a). Keputusan K10 berlaku: replikasi ketat dihentikan; proyek lanjut dengan implementasi ulang dengan deviasi terdokumentasi.
**Bukan amandemen benchmark.** Protokol ini tidak mengubah hasil, toleransi, atau status mana pun dari G0, D1, D2, S7-A, S7-B, atau S7-C.

---

## 0. Catatan permanen dari S7-C

Status resmi tetap: **G1 HOLD (reg-2), G1 HOLD (reg-3, baris 0a)**. Analisis berikut adalah analisis **eksploratoris pasca-hasil** atas `S7C_wdc_crosscheck.csv` (dalam `S7C_review.zip`, SHA-256 `fdf3a0b2…baa5`). Analisis ini tidak mengubah status apa pun.

| No | Temuan | Arti |
|---|---|---|
| E1 | Untuk X, Y, Z (masing-masing 95.018 jam berpasangan), nilai format WDC = pembulatan *round-half-to-even* nilai per jam 0,1 nT ke nT bulat pada **100%** jam; selisih −0,5 s.d. +0,5 nT | Format WDC menyimpan nT bulat. Batas validasi 0,1 nT di registration-3 adalah **kesalahan spesifikasi**, bukan bukti inkonsistensi data |
| E2 | Tabular base WDC sekarang: X 203–206, Y −66 s.d. −60, Z 312 (berubah antartahun untuk X dan Y) | Tidak cocok dengan konstanta eksploratoris Mendeley (25.000; −1.800; 36.000 nT). Hipotesis "`meanField` = rata-rata tabular value format WDC sekarang" **terbantah** |
| E3 | Seandainya batas validasi benar, d′ = d − base×100 masih sekitar 4.200–4.800 nT di ketiga komponen, sehingga semua bulan terkena baris 0b | **Keputusan tidak berubah:** G1 tetap HOLD dan K10 tetap berlaku. Kesalahan spesifikasi hanya mengubah baris penyebab (0a, bukan 0b) |
| E4 | Data WDC X, Y, Z konsisten lintas tiga format (menit, per jam IAGA, format WDC) | Fondasi data proyek bersih |

**Kesimpulan untuk naskah:** rata-rata harian dalam dataset publik memakai level acuan yang tidak terdokumentasi dan tidak dapat diturunkan dari metadata WDC. Konstanta eksploratoris boleh disebut hanya sebagai pengamatan eksploratoris, bukan transformasi yang terbukti.

---

## 1. Kerangka klaim

| Klaim lama | Klaim baru di G2-R | Arti |
|---|---|---|
| R1 reproduksi persis | Tidak menjadi target | — |
| R2 IQD sampai konstanta | Bukti bentuk saja (sudah ada, `DEVELOPMENT_SEEN`) | Keterbatasan O1 tetap |
| R3 struktur PCA | **S-agreement**: kesesuaian struktur PCA dengan keluaran publikasi | Diuji di G2-R |
| R4 keputusan klasifikasi | **D-agreement**: kesesuaian keputusan pemilihan PC | Diuji di G4-R (instruksi terpisah) |

Kata "replikasi" tidak dipakai untuk hasil G2-R. Istilah yang dipakai: **"implementasi ulang independen; kesesuaian dengan keluaran publikasi"**.

---

## 2. Deviasi terdokumentasi (dibekukan)

| Kode | Pilihan | Dasar |
|---|---|---|
| DV1 | Masukan = data per jam WDC sekarang, nT absolut, snapshot ber-hash dari G0. Label HH:00 = rata-rata menit HH:00–HH:59, diposisikan di HH:30 | D2 (terkonfirmasi) |
| DV2 | Celah diinterpolasi linear di dalam bulan, sebelum matriks dibentuk. Jumlah jam terinterpolasi per hari dicatat; hari dengan > 12 jam terinterpolasi diberi bendera (tidak dikeluarkan) | Artikel data 2021 (interpolasi linear); panjang celah maksimum tidak disebut sumber |
| DV3 | 29 Februari dibuang dari matriks PCA | D1 (terkonfirmasi) |
| DV4 | Level acuan = nT absolut. Level acuan penulis tidak terdokumentasi; varian V0-T **dihapus** karena tidak dapat dibuktikan | S7-C, E2–E3 |
| DV5 | SVD dengan NumPy/LAPACK, float64, matriks 24 × N (baris = jam, kolom = hari) | Artikel 2021/2023 (SVD, 24 × N) |
| DV6 | Tanda: setiap PC_k dibalik bila korelasinya dengan PC_k Mendeley negatif; EOF_k ikut dibalik. Mode tidak terpengaruh tanda | Artikel 2023 (\|r\|) |

---

## 3. Varian yang diuji

Untuk matriks A (24 × N, nT absolut):

| Varian | Definisi |
|---|---|
| V0-A | A tanpa centering |
| V1 | Setiap kolom (hari) dikurangi rata-rata 24 jamnya |
| V2 | Setiap baris (jam) dikurangi rata-ratanya lintas hari |
| V3 | Setiap kolom dikurangi baseline malamnya: rata-rata jam 00:30, 01:30, 02:30, 03:30, 23:30 UTC (indeks 0, 1, 2, 3, 23) |

Untuk setiap varian: A_v = U S Vᵀ; PC_k = U[:, k] (vektor satuan, 24 nilai); EOF_k = S_k · V[:, k] (nT per hari); mode_k = PC_k ⊗ EOF_k (24 × N, nT); VF_k = S_k² / Σ S². Orientasi mode disesuaikan dengan berkas Mendeley (S7-A memakai `outer(EOF_day, PC_hour)`).

---

## 4. Benchmark dan bulan

**Benchmark:** DAT PCA Mendeley dengan `allowed_use = ORIGINAL_ABSOLUTE` dan `d3_eligible = true` di `S7B_benchmark_policy.csv`, ditambah delta `S7C_benchmark_policy_delta.csv`. Februari tidak dipakai. Berkas `SUSPECT_DIAGNOSTIC` dan `EXCLUDED` tidak dipakai untuk pemilihan.

| Set | Matriks (masing-masing X, Y, Z) | Fungsi |
|---|---|---|
| Pengembangan | 2017-06, 2017-10, gabungan Juni (24 × 330) | Memilih varian |
| Holdout | 2009-01, 2015-03, gabungan Oktober | Evaluasi sesudah varian dibekukan |

Total: 9 matriks pengembangan dan 9 matriks holdout. Bila salah satu matriks tidak ada atau tidak eligible menurut kebijakan, catat sebagai `NOT_ELIGIBLE` dan jangan menggantinya dengan bulan lain.

---

## 5. Metrik dan toleransi (dari protokol Fase 2A, tidak diubah)

| Metrik | Toleransi | Catatan |
|---|---|---|
| Selisih absolut VF_k (k = 1–3) | ≤ 0,005 | |
| \|r\| PC_k, pasangan non-degenerat | ≥ 0,999 | |
| RMSE EOF_k | ≤ 0,1 nT | Hanya bila skala PC/EOF Mendeley terkonfirmasi (lihat 5.2) |
| Sudut subruang, pasangan degenerat | ≤ 5° | Degenerat bila \|λ_k − λ_k+1\| < λ_k √(2/N) (North dkk. 1982) |
| Galat Frobenius relatif, jumlah mode 1–3 | ≤ 1% | **Metrik utama**; kebal tanda dan pembagian skala PC/EOF |

Toleransi final = nilai terbesar antara angka di tabel dan 2 × resolusi cetak berkas Mendeley (sudah dicatat di G0/S7-B).

### 5.1 Uji `meanField` (didaftarkan di protokol Fase 2A sebagai bagian D3; kini dipakai dalam bentuk kebal offset)

Untuk setiap matriks pengembangan non-gabungan, hitung untuk komponen yang sama:
- s_daily = simpangan baku (rata-rata harian kita − `meanField`) lintas hari;
- s_night = simpangan baku (baseline malam kita − `meanField`) lintas hari.

Prediksi: V1 → s_daily ≤ 0,1 nT dan s_night jauh lebih besar; V3 → kebalikannya. V2 tidak memprediksi N nilai harian. Simpangan baku kebal terhadap level acuan yang tidak terdokumentasi, jadi tidak ada konstanta yang dipasang. Hasil uji ini hanya dipakai sebagai pemutus seri (bagian 6), bukan syarat lulus.

### 5.2 Skala PC dan EOF (D4)

Uji apakah norma PC Mendeley = 1 dan apakah PC × EOF = berkas `mode` Mendeley. Bila skala tidak terkonfirmasi, metrik RMSE EOF dilaporkan sebagai `NOT_APPLICABLE` dan penilaian memakai galat Frobenius mode.

---

## 6. Aturan pemilihan varian (dibekukan sebelum perhitungan)

1. Varian **lulus pengembangan** bila galat Frobenius mode 1–3 ≤ 1% dan VF lolos di **semua** 9 matriks pengembangan, serta PC1 Y dan Z lolos (\|r\| ≥ 0,999 atau subruang ≤ 5° bila degenerat).
2. Bila tepat satu varian lulus: varian itu dipilih.
3. Bila lebih dari satu lulus: pilih yang konsisten dengan uji `meanField` (5.1). Bila masih seri: pilih galat Frobenius median terkecil.
4. Bila tidak ada yang lulus: pilih varian dengan galat Frobenius median terkecil, label `DEVIATION_STRUCTURAL`. **Pekerjaan tetap lanjut** (K10).
5. Varian dan seluruh konfigurasi dibekukan (`G2R_frozen_config.json` + SHA-256) **sebelum** holdout dihitung. Setelah itu tidak ada perubahan.

---

## 7. Label hasil (holdout)

| Label | Syarat | Klaim di naskah |
|---|---|---|
| `S-AGREE` | Varian terpilih lolos semua metrik di 9 matriks holdout | "Struktur PCA sesuai dengan keluaran publikasi dalam toleransi numerik" |
| `S-PARTIAL` | ≥ 6/9 matriks holdout lolos galat Frobenius, dan PC1 Y/Z lolos di semua holdout | "Sesuai sebagian; deviasi dilaporkan per matriks" |
| `S-DEVIATE` | Selain itu | "Implementasi ulang menyimpang secara terdokumentasi dari keluaran publikasi" |

**Ketiga label tidak menghentikan proyek.** Label hanya menentukan kalimat klaim. Langkah berikutnya tetap G4-R (kesesuaian keputusan) lalu Fase 3.

---

## 8. Kondisi berhenti untuk investigasi (terbatas)

Hanya satu: **dugaan bug kode.** Bila di semua varian PC1 Y atau Z memiliki \|r\| < 0,9 pada matriks pengembangan, jalankan uji unit sintetis (bagian 9) satu kali. Jika uji unit lulus, lanjutkan dengan label `S-DEVIATE`. Jika gagal, perbaiki kode, jalankan ulang pengembangan satu kali, catat di log.

**Tidak ada lagi forensik benchmark.** Setiap ketidakcocokan dicatat sebagai deviasi dan pekerjaan tetap jalan.

---

## 9. Uji unit wajib (tanpa data observatorium)

1. Matriks sintetis 24 × 30 dengan SVD yang diketahui: PC, EOF, VF hasil kode sama dengan nilai yang diketahui (selisih < 10⁻¹⁰).
2. Σ VF = 1.
3. Penjumlahan semua mode = matriks masukan setelah centering.
4. Pembalikan tanda PC dan EOF tidak mengubah mode.
5. V1 memberi rata-rata kolom nol; V2 rata-rata baris nol; V3 nilai baseline malam nol per kolom.
6. Offset konstan pada masukan tidak mengubah hasil V1, V2, V3.

---

## 10. Larangan

- Tidak ada DTW, DIFI, uji surrogate, classifier, ICA, NMF, autoencoder (itu G4-R dan Fase 3).
- Tidak memakai konstanta 25.000 / −1.800 / 36.000 nT atau tabular base WDC dalam perhitungan apa pun.
- Tidak memakai Februari atau berkas `SUSPECT_DIAGNOSTIC`/`EXCLUDED` untuk pemilihan varian.
- Tidak mengubah toleransi, aturan pemilihan, atau label setelah hasil terlihat.
- Tidak melihat hasil holdout sebelum `G2R_frozen_config.json` dibekukan.
- Tidak mengganti bulan yang `NOT_ELIGIBLE`.
- Tidak mengubah artefak beku G0–S7-C.
- Tidak menulis "replikasi berhasil".

---

## 11. Jalur paralel K11 (setelah G2-R selesai, dalam tugas yang sama)

Diizinkan: loader data per jam WDC untuk PLR, TUN, KDU, GUA (2014–2018) dan fungsi konversi jam UTC → waktu matahari lokal (berdasarkan bujur), beserta uji unitnya.
Dilarang: menghitung Sq, PCA, statistik hasil, atau gambar data untuk stasiun-stasiun tersebut.

---

## 12. Instruksi untuk Claude Code

Simpan dokumen ini sebagai `phase2a/G2R/G2R_protocol_v1.md`, catat SHA-256-nya, lalu jalankan:

```text
PERAN: Scientific Python developer + reproducibility auditor.
PROYEK: Auto-SqPCA. Akar: <REPOSITORY_ROOT>
CAKUPAN: G2-R (pilot PCA implementasi ulang, jalur K10) + K11 infrastruktur.
DASAR: phase2a/G2R/G2R_protocol_v1.md = APPROVED (13 Nov 2026). Ikuti PERSIS.

LANGKAH 0 - Verifikasi dan pencatatan
- Verifikasi SHA-256 artefak beku G0, D1, D2, S7-A, S7-B, S7-C.
- Semua keluaran baru di phase2a/G2R/. Jangan mengubah folder lain.
- G2R_changes.md: catat transisi K10, temuan eksploratoris E1-E4 S7-C
  (dari protokol bagian 0, tandai EXPLORATORY_POST_HOC), dan bahwa status
  G1 reg-2 dan reg-3 tetap HOLD.

LANGKAH 1 - Uji unit (bagian 9)
- tests/test_pca_core.py; semua 6 uji wajib lulus sebelum data disentuh.
- Simpan keluaran pytest di G2R_unit_tests.log.

LANGKAH 2 - Penyusunan matriks
- Dari data per jam WDC (snapshot G0), susun matriks 24 x N untuk 18
  matriks di bagian 4 (X, Y, Z). Interpolasi linear di dalam bulan (DV2);
  catat jam terinterpolasi per hari dan bendera > 12 jam.
- Cek kelayakan tiap matriks terhadap S7B_benchmark_policy.csv +
  S7C_benchmark_policy_delta.csv. Tidak eligible -> NOT_ELIGIBLE, jangan
  diganti.
- Keluaran: G2R_matrix_inventory.csv (dimensi, hari, jam terinterpolasi,
  eligibility, hash berkas Mendeley pembanding).

LANGKAH 3 - Pengembangan (HANYA 9 matriks pengembangan)
- Hitung V0-A, V1, V2, V3 sesuai bagian 3.
- D4 (bagian 5.2): norma PC Mendeley dan uji PC x EOF = mode.
- Metrik bagian 5 per matriks x komponen x varian; kriteria degenerasi
  North; uji meanField (5.1) untuk matriks non-gabungan.
- Terapkan aturan pemilihan bagian 6 secara mekanis.
- Keluaran: G2R_dev_metrics.csv, G2R_meanfield_test.csv,
  G2R_variant_selection.json (semua varian, aturan yang terpenuhi, varian
  terpilih, label DEVIATION_STRUCTURAL bila berlaku).

LANGKAH 4 - Pembekuan
- G2R_frozen_config.json: varian, definisi matriks, interpolasi, orientasi
  mode, konvensi tanda, versi pustaka, hash kode. Hitung SHA-256-nya.
- JANGAN membaca atau menghitung matriks holdout sebelum langkah ini selesai.

LANGKAH 5 - Holdout (9 matriks holdout, satu kali)
- Jalankan HANYA varian beku. Metrik bagian 5.
- Tentukan label S-AGREE / S-PARTIAL / S-DEVIATE sesuai bagian 7.
- Keluaran: G2R_holdout_metrics.csv, G2R_result.json (label, tabel
  penyebut: target_total, not_eligible, suspect, eligible, pass, fail).

LANGKAH 6 - K11 infrastruktur (bagian 11)
- Loader WDC hourly untuk PLR, TUN, KDU, GUA 2014-2018 + konversi UTC ke
  waktu matahari lokal + uji unit. TIDAK ADA Sq/PCA/statistik/gambar data.

LANGKAH 7 - Paket
- G2R_report.md (ringkas: varian terpilih, label, penyebut, deviasi),
  G2R_execution.log, G2R_checksums.sha256 (berkas isi saja).
- G2R_review.zip tanpa data mentah; SETELAH ZIP final, hitung SHA-256 ke
  G2R_review.zip.sha256 DI LUAR ZIP.

KONDISI BERHENTI: hanya bagian 8 (dugaan bug kode). Tidak ada forensik
benchmark. Ketidakcocokan dicatat sebagai deviasi, pekerjaan lanjut.

LARANGAN: bagian 10 protokol.

JIKA RAGU: tulis UNRESOLVED dengan bukti spesifik; jangan menebak; lanjut
ke langkah yang tidak bergantung padanya.

SELESAI: setelah G2R_review.zip dan .sha256 pendampingnya dibuat, BERHENTI
dan laporkan dalam satu paragraf: varian terpilih, label holdout, tabel
penyebut ringkas, deviasi utama, status K11.
```

---

## 13. Sesudah G2-R

1. **G4-R (ringan):** kesesuaian keputusan pemilihan PC. Y/Z: PC1 = Sq dengan IQD sebagai acuan. X: dengan DIFI hanya bila versi yang tersedia jelas; bila tidak, cukup dengan IQD dan klaim dibatasi.
2. **Fase 3:** eksperimen inti Auto-SqPCA (dampak data hilang dengan topeng TND, abstain/ketidakpastian, transfer ke PLR, TUN, KDU, GUA dengan baseline waktu lokal). Bagian ini yang menentukan kekuatan paper.
