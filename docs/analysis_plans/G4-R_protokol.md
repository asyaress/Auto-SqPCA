# Protokol G4-R: Kesesuaian Keputusan Pemilihan PC (jalur K10) — Auto-SqPCA

**Versi:** G4R-v1
**Tanggal:** 13 November 2026
**Status:** APPROVED (peneliti utama, 13 Nov 2026)
**Dasar:** G2-R selesai: varian **V1** (centering rata-rata harian) dibekukan (`G2R_frozen_config.json`, SHA-256 `25676d83…a320`); label struktur holdout **S-DEVIATE** (3/9 lulus). G1 HOLD (reg-2 dan reg-3) tidak berubah.
**Bukan amandemen.** Protokol ini tidak mengubah hasil, toleransi, atau label G0–G2-R.

---

## 0. Catatan dari review G2-R (dicatat, tidak mengubah label)

| No | Temuan | Status |
|---|---|---|
| R1 | V1 teridentifikasi oleh dua bukti independen: median galat Frobenius pengembangan V1 0,0151 vs V3 0,509, V2 0,978, V0-A 2.909,7; uji `meanField` s_daily 0,05–0,06 nT vs s_night 1,9–6,8 nT | Hasil lokal |
| R2 | Holdout: \|r\| PC1 ≥ 0,9998 di 9/9 matriks; \|r\| PC2 dan PC3 ≥ 0,995; selisih VF maksimum 0,0069; galat Frobenius 0,8–5,3%, terbesar Januari 2009 | Hasil lokal |
| R3 | Toleransi G2-R tidak saling konsisten: \|r\| ≥ 0,999 mengizinkan galat bentuk ±4,5% (√(2(1−r))), sedangkan Frobenius ≤ 1% menuntut \|r\| ≥ 0,99995 | Analisis reviewer; **label S-DEVIATE tetap** |
| R4 | Dugaan: selisih absolut data kecil dan hampir konstan (~0,05 nT) menjadi galat relatif besar saat Sq lemah (minimum matahari) | Hipotesis; tidak diuji |

**Pelajaran desain yang berlaku mulai G4-R:** setiap aturan atau ambang baru diuji konsistensinya pada data sintetis sebelum data nyata dihitung (bagian 7).

---

## 1. Tujuan dan klaim

G4-R menjawab satu pertanyaan: **apakah aturan klasifikasi asal, bila dijalankan pada PC hasil implementasi ulang, memberi keputusan yang sama dengan bila dijalankan pada PC yang dipublikasikan?** Ini klaim **D-agreement** (kesesuaian keputusan), bukan replikasi Tabel klasifikasi DIFI3 + DTW artikel asal.

G4-R juga menjalankan konfigurasi V1 beku pada seluruh matriks COI 2007–2017 (**G3-R deskriptif**), karena PC lengkap diperlukan untuk klasifikasi. Hasil struktur G3-R hanya dilaporkan, tidak diberi label lulus/gagal baru.

**Tidak termasuk:** DIFI, DTW, CM5, classifier ML. Karena itu kategori X di Tabel artikel asal (berbasis DIFI3 + DTW) **tidak** direplikasi dan tidak boleh diklaim.

---

## 2. Aturan klasifikasi

### 2.1 Bagian yang terdokumentasi di artikel asal (dipakai apa adanya)

| Kode | Aturan | Sumber |
|---|---|---|
| CR1 | Ukuran kesamaan: \|r\| Pearson antara PC_k dan kurva acuan Sq | Artikel 2023 |
| CR2 | PC_k dianggap mirip Sq bila \|r\| ≥ 0,45 **dan** signifikan menurut uji surrogate acak-fase (Ebisuzaki 1997) | Artikel 2023 |
| CR3 | Acuan Sq_IQD per bulan = rata-rata variasi harian lima IQD bulan itu setelah baseline malam (00:30, 01:30, 02:30, 03:30, 23:30 UTC) dikurangkan | Artikel 2021, 2023 |
| CR4 | Pemeriksaan sanity Y/Z: artikel melaporkan PC1 = Sq di semua kasus dengan \|r\| ≥ 0,88 | Artikel 2023 |

### 2.2 Pilihan implementasi (tidak terdokumentasi lengkap; dibekukan di sini)

| Kode | Pilihan | Alasan |
|---|---|---|
| IC1 | Surrogate: 1.000 deret acak-fase per uji, amplitudo spektrum dipertahankan, komponen DC dan Nyquist tidak diacak; seed tetap `20261113`; p = (1 + jumlah surrogate dengan \|r\| ≥ \|r\|_obs) / 1.001; signifikan bila p < 0,05 | Ebisuzaki 1997; jumlah surrogate dan α tidak disebut di sumber |
| IC2 | Klasifikasi kombinasi: untuk setiap subset {PC1, PC2}, {PC1, PC3}, {PC2, PC3}, {PC1, PC2, PC3}, deret gabungan = Σ w_k · PC_k dengan w_k = rata-rata EOF_k bulan itu (nT); diuji dengan CR1–CR2 | Artikel 2023 menyebut penjumlahan berbobot dengan rata-rata EOF bulanan; detail tambahan tidak disebut |
| IC3 | Kategori keputusan per matriks: daftar biner 7 kandidat (3 PC tunggal + 4 kombinasi), masing-masing `SQ_LIKE` atau `NOT_SQ` | Unit keputusan yang paling sederhana dan sepenuhnya ditentukan oleh CR1–CR2 |
| IC4 | Untuk PC Mendeley, bobot IC2 memakai EOF Mendeley; untuk PC kita, EOF kita | Setiap pipeline memakai keluarannya sendiri |
| IC5 | Tanda tidak berpengaruh (\|r\|); bobot IC2 dipakai dengan tanda setelah penyelarasan tanda DV6 dari G2-R | Konsisten dengan G2-R |

---

## 3. Desain perbandingan

Klasifikasi dijalankan pada empat kombinasi:

| Kode | PC | Acuan Sq_IQD | Fungsi |
|---|---|---|---|
| P-own | PC kita (V1 beku) | IQD kita (CR3, dari data WDC) | Pipeline implementasi ulang lengkap |
| P-pub | PC Mendeley | IQD Mendeley | Pipeline publikasi |
| P-mixA | PC kita | IQD Mendeley | Memisahkan efek PCA |
| P-mixB | PC Mendeley | IQD kita | Memisahkan efek acuan IQD |

**Perbandingan utama:** P-own vs P-pub.
**Perbandingan diagnostik:** P-own vs P-mixA (efek acuan IQD), P-pub vs P-mixA (efek PCA). Ini menjalankan uji kesepakatan keputusan K2: offset dan pemusatan IQD Mendeley tidak berpengaruh pada |r|, jadi keputusan yang sama berarti selisih kurva IQD tidak material.

---

## 4. Cakupan dan kelayakan

- **Matriks:** 132 matriks bulan–tahun × X, Y, Z, ditambah 12 gabungan × X, Y, Z (dilaporkan terpisah).
- **Kelayakan** mengikuti `S7B_benchmark_policy.csv` + `S7C_benchmark_policy_delta.csv`:
  - `EXCLUDED` (6 DAT Februari Y): tidak dibandingkan, tercatat di penyebut.
  - `SUSPECT_DIAGNOSTIC` (PCA Februari Y; Februari Z terkait 2014; X 2008-04/06/09/11): dihitung, dilaporkan terpisah, tidak masuk penyebut utama.
  - Februari X/Z lain: penyebut utama dengan bendera `FEBRUARY`.
  - `DEVELOPMENT_SEEN`: dilaporkan terpisah (termasuk bulan pengembangan G2-R 2017-06 dan 2017-10).
  - Matriks dengan jam batas bulan yang tidak bisa diinterpolasi (`UNRESOLVED_MISSING`, aturan G2-R): tidak dihitung, tercatat.
- **Sq_IQD Februari 2016:** Q1–Q5 resmi termasuk 29 Februari (K7, `PROVISIONAL`).

---

## 5. Metrik dan label

### 5.1 Metrik

- Kesepakatan keputusan per kandidat (7 per matriks) dan per matriks (semua 7 sama), per komponen.
- Cohen's κ per komponen untuk PC1, PC2, PC3 tunggal.
- **Zona sensitif** (dari protokol Fase 2A, Tingkat 2): kasus dengan \|r\| dalam ±0,02 dari 0,45, atau p dalam ±0,01 dari 0,05, di salah satu pipeline. Ketidaksepakatan di zona ini wajar karena perbedaan numerik kecil.
- Sanity CR4: persentase matriks Y/Z dengan PC1 \|r\| ≥ 0,88 di P-own dan P-pub.
- G3-R deskriptif: galat Frobenius, selisih VF, \|r\| PC1–3 untuk semua matriks, dengan toleransi G2-R sebagai pembanding (dihitung lulus/gagal, **tanpa label baru**).

### 5.2 Label D-agreement (perbandingan utama, penyebut utama)

| Label | Syarat |
|---|---|
| `D-AGREE` | Semua ketidaksepakatan berada di zona sensitif |
| `D-PARTIAL` | Keputusan PC1 Y dan Z sama di 100% matriks; ada ketidaksepakatan di luar zona sensitif pada X atau pada PC2/PC3 |
| `D-DEVIATE` | Ada ketidaksepakatan keputusan PC1 Y atau Z di luar zona sensitif |

Seperti G2-R, **label tidak menghentikan proyek**; label hanya menentukan kalimat klaim. Setelah G4-R, proyek lanjut ke Fase 3.

---

## 6. Kondisi berhenti (terbatas)

Hanya dugaan bug kode: bila sanity CR4 pada **P-pub** (PC dan IQD Mendeley sendiri) di bawah 90% untuk Y atau Z, implementasi aturan klasifikasi kemungkinan salah, karena artikel melaporkan 100%. Jalankan uji unit bagian 7 satu kali; bila lulus, lanjut dan catat; bila gagal, perbaiki dan jalankan ulang satu kali.

**Tidak ada forensik benchmark.** Ketidaksepakatan dicatat dan dilaporkan.

---

## 7. Uji unit wajib (sebelum data nyata)

1. Surrogate acak-fase mempertahankan amplitudo spektrum (selisih < 10⁻¹⁰) dan rata-rata.
2. Dengan seed tetap, p-value identik pada dua kali jalan.
3. Deret identik dengan acuan: \|r\| = 1, p < 0,05. Deret derau putih tak berkorelasi (100 kasus sintetis): tingkat positif palsu pada α = 0,05 berada di 0,01–0,10.
4. **Uji konsistensi aturan (pelajaran R3):** pada 200 kasus sintetis (kurva Sq sintetis 24 jam + derau Gaussian dengan simpangan baku 0,05 nT), keputusan CR2 pada versi asli dan versi berderau harus sama di ≥ 95% kasus di luar zona sensitif. Bila tidak, catat sebagai keterbatasan aturan **sebelum** data nyata dihitung.
5. Bobot IC2: kombinasi dengan satu bobot nol sama dengan PC tunggal.
6. Pembalikan tanda PC tidak mengubah keputusan.

---

## 8. Larangan

- Tidak ada DIFI, DTW, CM5, classifier, ICA, NMF, autoencoder.
- Tidak mengklaim replikasi Tabel klasifikasi X artikel asal.
- Tidak mengubah toleransi, label, atau status G0–G2-R; tidak mengubah `G2R_frozen_config.json`.
- Tidak mengubah IC1–IC5, zona sensitif, atau label 5.2 setelah hasil terlihat.
- Tidak menganalisis stasiun K11 (PLR, TUN, KDU, GUA).
- Tidak menimpa artefak beku.

---

## 9. Instruksi untuk Claude Code

Simpan dokumen ini sebagai `phase2a/G4R/G4R_protocol_v1.md`, catat SHA-256-nya, lalu jalankan:

```text
PERAN: Scientific Python developer + reproducibility auditor.
PROYEK: Auto-SqPCA. Akar: <REPOSITORY_ROOT>
CAKUPAN: G3-R deskriptif + G4-R (kesesuaian keputusan pemilihan PC).
DASAR: phase2a/G4R/G4R_protocol_v1.md = APPROVED (13 Nov 2026). Ikuti PERSIS.

LANGKAH 0 - Verifikasi
- Verifikasi SHA-256 artefak beku G0, D1, D2, S7-A, S7-B, S7-C, G2-R,
  termasuk G2R_frozen_config.json (25676d83...a320) dan kode beku G2-R.
- Semua keluaran baru di phase2a/G4R/. Jangan mengubah folder lain.
- G4R_changes.md: catat temuan review G2-R (protokol bagian 0, label
  ANALISIS_REVIEWER / HIPOTESIS), dan bahwa label S-DEVIATE serta status G1
  tidak berubah.

LANGKAH 1 - Uji unit (bagian 7)
- tests/test_classification.py; keenam uji wajib dijalankan sebelum data.
- Uji 4 (konsistensi aturan): jika < 95%, JANGAN berhenti; catat sebagai
  keterbatasan di G4R_rule_consistency.json lalu lanjut.
- Keluaran: G4R_unit_tests.log, G4R_rule_consistency.json.

LANGKAH 2 - G3-R deskriptif
- Jalankan konfigurasi V1 beku (pakai kode beku G2-R, jangan menulis ulang
  PCA) pada semua 132 matriks bulan-tahun dan 12 gabungan, X/Y/Z.
- Kelayakan menurut bagian 4. UNRESOLVED_MISSING dicatat, tidak diganti.
- Metrik struktur G2-R per matriks; hitung lulus/gagal terhadap toleransi
  G2-R TANPA label baru.
- Keluaran: G3R_structure_metrics.csv, G3R_denominator.json.

LANGKAH 3 - Acuan Sq_IQD kita
- CR3 dari data per jam WDC (snapshot G0), IQD GFZ; baseline malam UTC
  sesuai artikel; Februari 2016 dengan 29 Feb (PROVISIONAL).
- Keluaran: G4R_sq_iqd_own.csv.

LANGKAH 4 - Klasifikasi empat pipeline (bagian 3)
- P-own, P-pub, P-mixA, P-mixB; 7 kandidat per matriks (IC2-IC3);
  surrogate IC1 dengan seed 20261113.
- Keluaran: G4R_classification_long.csv (matriks x pipeline x kandidat:
  r, abs_r, p, decision, sensitive_zone).

LANGKAH 5 - Kesepakatan dan label
- Metrik bagian 5.1; label bagian 5.2 untuk perbandingan utama.
- Sanity CR4 untuk P-own dan P-pub; bila P-pub < 90% (Y atau Z) terapkan
  bagian 6.
- Daftar setiap ketidaksepakatan di luar zona sensitif beserta r dan p.
- Keluaran: G4R_agreement.csv, G4R_result.json (label, penyebut:
  target_total, excluded, suspect, development_seen, unresolved, eligible,
  agree, disagree_in_zone, disagree_outside_zone; kappa; sanity CR4).

LANGKAH 6 - Paket
- G4R_report.md (ringkas: G3-R deskriptif, label D, penyebut, keterbatasan),
  G4R_execution.log, G4R_checksums.sha256 (berkas isi saja).
- G4R_review.zip tanpa data mentah; SETELAH ZIP final, hitung SHA-256 ke
  G4R_review.zip.sha256 DI LUAR ZIP.

KONDISI BERHENTI: hanya bagian 6. Tidak ada forensik benchmark.
LARANGAN: bagian 8.
JIKA RAGU: tulis UNRESOLVED dengan bukti spesifik; jangan menebak.

SELESAI: setelah G4R_review.zip dan .sha256 pendampingnya dibuat, BERHENTI
dan laporkan dalam satu paragraf: label D, kappa PC1-3 per komponen,
sanity CR4, ringkasan G3-R, keterbatasan utama.
```

---

## 10. Sesudah G4-R

**Fase 3** (protokol terpisah): eksperimen inti Auto-SqPCA, yaitu dampak data hilang dengan topeng celah TND, ketidakpastian/abstain, dan transfer ke PLR, TUN, KDU, GUA dengan baseline waktu lokal. Acuan kebenarannya benchmark semi-sintetis. Semua toleransi Fase 3 diuji konsistensinya pada data sintetis sebelum data nyata dihitung.
