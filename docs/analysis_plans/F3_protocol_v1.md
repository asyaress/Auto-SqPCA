# Protokol Fase 3: Pengembangan dan Evaluasi Auto-SqPCA

**Versi:** F3-v1
**Tanggal:** 14 November 2026
**Status:** APPROVED (peneliti utama, 14 Nov 2026)
**Dasar:** Fase 2 ditutup. G1 HOLD (reg-2, reg-3); G2-R S-DEVIATE (V1 teridentifikasi; median galat Frobenius G3-R 1,1–1,8%, |r| PC1 ≥ 0,9993); G4-R D-AGREE (2.661/2.667 keputusan sama). Fase 3 tidak memakai benchmark Mendeley lagi.

---

## 0. Prinsip

1. **Uji sintetis dulu.** Semua metrik, ambang, dan aturan abstain diuji konsistensinya pada data sintetis sebelum data nyata dihitung (bagian 8).
2. **Pengembangan dan holdout dipisah.** Semua pilihan dibuat di set pengembangan, dibekukan dengan SHA-256, baru holdout dihitung satu kali.
3. **Label tidak menghentikan proyek.** Hasil negatif dilaporkan dan menentukan kalimat klaim serta judul (bagian 7).
4. **Tidak ada forensik benchmark.** Masalah data dicatat sebagai keterbatasan.
5. **Anti-sirkular.** Acuan yang dipakai untuk memilih kandidat Sq (IQD) tidak pernah menjadi satu-satunya acuan evaluasi. Evaluasi memakai kebenaran semi-sintetis dan model DIFI.

---

## 1. Kontribusi yang diuji

| Kode | Kontribusi | Eksperimen | Kriteria berhasil (holdout) |
|---|---|---|---|
| C1 | Penanganan data hilang | E1 | Kurva galat vs data hilang dilaporkan beserta batas aman p*; metode terpilih **lebih baik nyata** daripada interpolasi linear asal (bagian 7) |
| C2 | Pemilihan kombinasi PC | E2 | Galat Sq komponen X lebih kecil nyata daripada aturan PC tunggal |
| C3 | Ketidakpastian dan abstain | E2 | Galat pada kasus diterima lebih kecil nyata daripada semua kasus, pada coverage ≥ 80% |
| C4 | Transfer lintas stasiun dan lintang | E3 | Deskriptif: kinerja dan tingkat abstain per stasiun terhadap lintang geomagnet |
| C5 | Kode terbuka dan reproduksibel | Semua | Satu perintah menjalankan ulang seluruh Fase 3 |

---

## 2. Pipeline Auto-SqPCA v1

| Tahap | Definisi |
|---|---|
| S1 Data | Data per jam WDC, nT absolut. Bila API WDC per jam memberi `NO_DATA` untuk stasiun–tahun, turunkan dari data menit Fase 1 dengan aturan A (rata-rata HH:00–HH:59, hanya bila 60 menit X/Y/Z valid, dipotong menuju nol ke 0,1 nT; terbukti identik dengan WDC di D2). Catat sumber per stasiun–tahun |
| S2 Waktu lokal | Deret digeser bilangan bulat jam Δ = round(bujur timur / 15). Kolom matriks = **hari waktu matahari lokal** 00–24 LT. Contoh: COI −1, KDU +9, GUA +10, PLR +7, TUN +7 (dihitung kode dari metadata) |
| S3 Data hilang | Metode M-INT, M-EXC, atau M-EM (bagian 3); dipilih di E1 dan dibekukan |
| S4 Centering | V1: setiap kolom (hari) dikurangi rata-rata 24 jamnya (hasil Fase 2) |
| S5 Dekomposisi | SVD matriks 24 × N; PC1–3 (vektor satuan), EOF_k = S_k·V_k (nT), VF_k |
| S6 Kandidat | 7 kandidat: PC1, PC2, PC3, {1,2}, {1,3}, {2,3}, {1,2,3}. Kurva kandidat dalam nT: Ŝq_S(h) = Σ_{k∈S} PC_k(h) · mean_d(EOF_k), kebal tanda |
| S7 Acuan pemilihan | Sq_IQD dari data itu sendiri: rata-rata 5 IQD GFZ setelah baseline malam **waktu lokal** (rata-rata jam 23:30, 00:30, 01:30, 02:30, 03:30 LT) dikurangkan, lalu dipusatkan ke rata-rata nol |
| S8 Pemilihan | Kandidat lolos bila \|r\| ≥ 0,45 dan p < 0,05 (surrogate acak-fase, aturan G4-R IC1). Dari yang lolos, ambil \|r\| maksimum; **aturan hemat:** pilih kandidat dengan PC paling sedikit yang \|r\|-nya dalam 0,02 dari maksimum (mencegah pilihan {1,2,3} yang praktis sama dengan rata-rata semua hari, yaitu S, bukan Sq) |
| S9 Ketidakpastian | Bootstrap hari B = 200 (resampling kolom dengan pengembalian), ulangi S4–S8: stabilitas s = frekuensi kandidat terpilih sama; pita 90% Ŝq per jam; lebar pita relatif w = median lebar pita / (maks − min Ŝq) |
| S10 Abstain | Abstain bila salah satu: A1 tidak ada kandidat lolos; A2 s < θ_s; A3 fraksi data teramati < θ_d; A4 w > θ_w. Nilai θ dipilih di E2 (pengembangan) dan dibekukan |

**Target ekstraksi:** variasi harian tenang reguler rata-rata bulanan per komponen, dipusatkan ke rata-rata nol. Di stasiun elektrojet ekuator (bila dipakai, E3b), target mencakup kontribusi elektrojet; ini dinyatakan eksplisit di naskah.

---

## 3. E1 — Penanganan data hilang (C1)

### 3.1 Data

- **Bulan lengkap:** ≥ 99% jam X/Y/Z valid dan tidak ada celah > 2 jam; celah kecil diisi linear untuk membentuk "data lengkap". Catat jumlahnya.
- **Stasiun:** COI 2007–2017, KDU 2014–2018, GUA 2014–2018.
- **Pengembangan:** COI 2007–2011, KDU 2014–2015.
- **Holdout:** COI 2012–2017, KDU 2016–2018, **GUA seluruhnya** (stasiun yang belum pernah dilihat).

### 3.2 Topeng data hilang (seed `20261114`, 20 replikasi per pengaturan)

| Jenis | Parameter |
|---|---|
| MCAR per jam | p = 5, 10, 20, 30, 40, 50% |
| Blok jam | panjang blok L = 6, 24, 72 jam; fraksi total p = 10, 20, 30, 40% |
| Hari hilang | p = 10, 20, 30, 40% hari dihapus utuh |
| Topeng nyata TND | 12 topeng bulanan TND 2017 (jam hilang bila tidak ada 60 menit X/Y/Z valid). Diselaraskan menurut indeks hari dan jam; bulan target lebih panjang memakai siklus dari awal topeng. Satu replikasi (deterministik) |

### 3.3 Metode

| Kode | Definisi |
|---|---|
| M-INT | Interpolasi linear deret per jam di dalam bulan (metode asal). Tepi: nilai jam valid terdekat di hari yang sama. Hari tanpa satu pun jam valid dibuang |
| M-EXC | Buang hari dengan < 22 dari 24 jam valid (≈ aturan 90% Fase 1); sisa celah diinterpolasi linear di dalam hari |
| M-EM | Imputasi SVD iteratif rank 3: isi awal dengan rata-rata hari yang teramati; ulangi centering V1 → SVD rank 3 → isi ulang entri hilang, sampai perubahan maksimum < 10⁻⁴ nT atau 500 iterasi. Hari dengan < 6 jam valid dibuang |

### 3.4 Metrik dan kebenaran

- **Kebenaran:** keluaran pipeline (S4–S8) pada bulan yang sama tanpa topeng.
- **Utama:** galat relatif L2 Ŝq (pipeline lengkap) = ‖Ŝq_topeng − Ŝq_lengkap‖ / ‖Ŝq_lengkap‖.
- **Sekunder:** galat relatif untuk kandidat tetap (kandidat terpilih di data lengkap); sudut subruang PC1; kesepakatan kandidat terpilih.
- **Batas aman p*:** fraksi data hilang terbesar dengan median galat ≤ ε dan persentil 90 ≤ 2ε, per jenis topeng dan metode. **ε = 0,05** (didaftarkan); sensitivitas ε = 0,03 dan 0,10 dilaporkan.

### 3.5 Pemilihan metode (pengembangan) dan holdout

- Metode terpilih = median galat utama terkecil, dirata-rata atas semua jenis topeng pada p ≤ 30% dan komponen X/Y/Z. Seri: metode yang lebih sederhana (M-INT < M-EXC < M-EM).
- Dibekukan di `F3_E1_frozen.json`, lalu holdout dihitung satu kali: kurva galat, p* per jenis topeng, hasil topeng TND.
- **Uji keunggulan (holdout):** untuk p ∈ {20, 30, 40}% pada MCAR, blok 24 jam, dan hari hilang: rasio median galat (metode terpilih / M-INT) dengan CI 95% bootstrap (resampling bulan, 2.000 kali). "Lebih baik nyata" = batas atas CI < 1.

---

## 4. Benchmark semi-sintetis (SSB) untuk E2

### 4.1 Konstruksi

Untuk bulan nyata stasiun s, komponen c:

1. **Residu nyata:** R = A_V1 − Ā ⊗ 1, dengan A_V1 matriks bulan setelah centering V1, Ā = rata-rata kolomnya (variasi harian rata-rata bulan). R memuat gangguan, variabilitas Sq harian, dan derau, tanpa kurva rata-rata bulanan.
2. **Kurva kebenaran:** Sq_true = kurva Sq model DIFI-8 (`pyDIFI`) di lokasi stasiun, rata-rata atas semua hari bulan itu, diindeks ulang ke jam LT (S2), dipusatkan. Sumber kebenaran ini **independen** dari acuan pemilihan (IQD).
3. **Variabilitas harian:** pengali amplitudo per hari a_d ~ lognormal(σ = 0,3), dinormalkan ke rata-rata 1.
4. **Skala:** α ∈ {0,5; 1; 2} × amplitudo DIFI (Sq lemah, normal, kuat).
5. **Data sintetis:** Y = α · Sq_true ⊗ a + R. Kebenaran rata-rata bulanan = α · Sq_true (tepat, karena rata-rata a_d = 1 dan rata-rata kolom R = 0).
6. **Topeng:** tanpa topeng, dan MCAR 20%; metode data hilang = beku dari E1.
7. **Replikasi:** 3 per kombinasi (bulan, komponen, α, topeng), seed `20261114`.

**Keterbatasan yang dinyatakan:** kebenaran semi-sintetis bukan Sq alami; R masih memuat variabilitas Sq nyata yang ikut menyulitkan ekstraksi (ini disengaja agar realistis).

### 4.2 Data

- **Stasiun–bulan:** COI 2014–2017, KDU 2014–2018, GUA 2014–2018; bulan dengan ≥ 95% jam valid. DIFI-8 mencakup 2014–2023.
- **Pengembangan:** KDU 2014–2016, COI 2014–2015.
- **Holdout:** GUA 2014–2018 (stasiun belum dilihat), KDU 2017–2018, COI 2016–2017.

---

## 5. E2 — Kombinasi PC dan abstain (C2, C3)

### 5.1 Varian yang dibandingkan

| Kode | Definisi |
|---|---|
| ASAL | PC tunggal dengan \|r\| tertinggi terhadap Sq_IQD (tanpa kombinasi, tanpa abstain; selalu memberi keluaran) |
| AUTO-NA | Pipeline S1–S8 (kombinasi + aturan hemat), tanpa abstain; bila tidak ada kandidat lolos, ambil \|r\| tertinggi |
| AUTO | Pipeline lengkap S1–S10 |

### 5.2 Metrik

Galat relatif L2: ‖Ŝq − α·Sq_true‖ / ‖α·Sq_true‖, per bulan–komponen–α–topeng–replikasi. Coverage = fraksi kasus tidak abstain.

### 5.3 Pemilihan θ (pengembangan saja)

- Grid: θ_s ∈ {0,5; 0,6; 0,7; 0,8; 0,9}; θ_w ∈ {0,25; 0,5; 1,0; ∞}; θ_d = 1 − p*_MCAR dari holdout E1 untuk metode terpilih (bila p* tidak terdefinisi, θ_d = 0,5).
- Tujuan: median galat kasus diterima terkecil dengan syarat coverage ≥ 0,80. Seri: coverage lebih besar.
- Dibekukan di `F3_E2_frozen.json` sebelum holdout.

### 5.4 Uji di holdout

- **C2:** komponen X: median selisih berpasangan (galat ASAL − galat AUTO-NA) dengan CI 95% bootstrap (resampling bulan). Berhasil bila batas bawah CI > 0. Y dan Z dilaporkan.
- **C3:** selisih (median galat semua kasus AUTO-NA − median galat kasus diterima AUTO) dengan CI 95% bootstrap. Berhasil bila batas bawah CI > 0 **dan** coverage holdout ≥ 0,80.
- **Kurva risk–coverage** (θ_s kontinu 0–1, θ lain beku) dilaporkan deskriptif.
- **Uji abstain pada kasus tanpa sinyal:** α = 0 (hanya R) pada holdout: laporkan tingkat abstain (harapan: tinggi). Deskriptif.

---

## 6. E3 — Transfer lintas stasiun dan lintang (C4), data nyata

### 6.1 Stasiun

| Stasiun | Periode | Peran |
|---|---|---|
| COI | 2014–2017 | Acuan lintang menengah |
| KDU, GUA | 2014–2018 | Lintang rendah Asia-Pasifik |
| PLR, TUN | 2017, bulan lolos QC Fase 1 | Indonesia |
| HUA, TTB, MBO (E3b, opsional) | 2014–2018 bila ≥ 6 bulan lolos per tahun menurut manifest Fase 1 | Eksploratoris; HUA/TTB = elektrojet, target Sq + EEJ |

### 6.2 Metrik (deskriptif, tanpa label lulus/gagal)

- Tingkat abstain dan alasannya (A1–A4) per stasiun dan komponen.
- Untuk kasus diterima: r(Ŝq, Sq_DIFI) dan rasio amplitudo (maks − min) terhadap DIFI. **Acuan evaluasi utama = DIFI** (independen dari pemilihan).
- r(Ŝq, Sq_IQD) dilaporkan sebagai sekunder, ditandai **tidak independen** (IQD dipakai dalam pemilihan).
- Perbandingan berpasangan AUTO vs ASAL: r terhadap DIFI per bulan.
- Lebar pita bootstrap.
- Semua metrik terhadap **lintang geomagnet dipol** (dihitung dari koefisien IGRF-13 epoch 2015, dipol terpusat, pustaka `ppigrf` atau setara; catat versi).

### 6.3 Konfigurasi

Pipeline beku dari E1 dan E2 dipakai **tanpa perubahan**. Tidak ada penyetelan per stasiun.

---

## 7. Aturan klaim dan judul (didaftarkan sekarang)

| Hasil holdout | Akibat |
|---|---|
| C1 berhasil (metode terpilih lebih baik nyata dari M-INT pada ≥ 2 dari 3 jenis topeng uji) | Boleh memakai "quality-aware" |
| C3 berhasil | Boleh memakai "uncertainty-guided" |
| Keduanya berhasil | Judul utama: *Auto-SqPCA: A Quality-Aware and Uncertainty-Guided Workflow for Extracting Solar Quiet Geomagnetic Variations at Low and Equatorial Latitudes* |
| Salah satu atau keduanya gagal | Kata sifat yang tidak didukung dihapus; bila keduanya gagal, judul konservatif: *Automated PCA-based Sq extraction at low and equatorial latitudes: validation using selected Indonesian and INTERMAGNET observatories* |
| C2 gagal | Kombinasi PC dilaporkan sebagai opsi, bukan kontribusi |
| C1 hanya menghasilkan p* (tanpa keunggulan) | Dilaporkan sebagai "batas operasi yang terukur", tanpa klaim metode lebih baik |

Kalimat "berlaku untuk Indonesia" tidak dipakai; klaim terbatas pada stasiun yang diuji.

---

## 8. Uji sintetis wajib (sebelum data nyata)

| No | Uji | Syarat lulus |
|---|---|---|
| T1 | M-EM pada matriks rank 3 tanpa derau, MCAR 30% | Galat rekonstruksi < 10⁻⁶ nT |
| T2 | Semua metrik kebal terhadap pembalikan tanda PC/EOF | Identik |
| T3 | Bootstrap pada Sq rank 1 tanpa derau | s = 1, w ≈ 0 |
| T4 | Generator SSB: rata-rata kolom Y − R sama dengan α·Sq_true | Selisih < 10⁻¹⁰ nT |
| T5 | E1 pada 0% data hilang | Galat = 0 untuk ketiga metode |
| T6 | Aturan abstain: (a) hanya derau (rank-3 acak + Gaussian 1 nT, tanpa Sq), 200 kasus; (b) Sq kuat (amplitudo 30 nT) + derau 1 nT, 200 kasus; θ di nilai tengah grid | (a) abstain ≥ 90%; (b) diterima ≥ 90%. Bila gagal: catat sebagai keterbatasan aturan **sebelum** data nyata, jangan ubah aturan |
| T7 | Pergeseran LT | Δ benar untuk COI, KDU, GUA, PLR, TUN dari metadata |
| T8 | Aturan hemat S8 | Pada kasus sintetis dengan PC1 = Sq persis, kandidat terpilih = PC1, bukan kombinasi |

---

## 9. Larangan

- Tidak memakai benchmark Mendeley di Fase 3.
- DIFI hanya untuk kebenaran SSB dan evaluasi E3; **tidak pernah** untuk pemilihan kandidat.
- Tidak ada classifier ML, ICA, NMF, autoencoder di inti Fase 3.
- Tidak menyetel apa pun di holdout; tidak mengubah ε, grid θ, pembagian set, seed, atau aturan setelah hasil terlihat.
- Tidak menambah stasiun di luar daftar bagian 6.1.
- Tidak menulis klaim di luar aturan bagian 7.
- Tidak mengubah artefak Fase 1–2.

---

## 10. Kondisi berhenti

- Uji sintetis T1–T5, T7, T8 gagal → perbaiki kode, jalankan ulang satu kali; bila tetap gagal, berhenti dan laporkan.
- `pyDIFI` tidak dapat dijalankan → E2 memakai kurva kebenaran pengganti: Sq_IQD bulan yang sama dari **tahun lain** di stasiun yang sama (ditandai `TRUTH_FALLBACK`); E3 tanpa evaluasi DIFI (hanya IQD, ditandai tidak independen).
- Data stasiun tidak tersedia → stasiun dibuang, dicatat; tidak diganti.

---

## 11. Keluaran untuk naskah

1. Gambar: kurva galat vs data hilang (per jenis topeng × metode), dengan p* ditandai.
2. Gambar: hasil topeng TND.
3. Gambar: kurva risk–coverage AUTO vs AUTO-NA.
4. Tabel: C2 dan C3 (median, CI 95%).
5. Gambar/tabel: kinerja E3 dan tingkat abstain terhadap lintang geomagnet.
6. Contoh kurva Ŝq dengan pita ketidakpastian untuk COI, KDU, PLR, TUN.
7. Tabel parameter beku dan hash konfigurasi.

---

## 12. Instruksi untuk Claude Code

Simpan dokumen ini sebagai `phase3/F3_protocol_v1.md`, catat SHA-256-nya. Jalankan **Tugas A**, kirim paket review, lalu **Tugas B**.

### Tugas A — Persiapan + E1

```text
PERAN: Scientific Python developer + reproducibility auditor.
PROYEK: Auto-SqPCA Fase 3. Akar: <REPOSITORY_ROOT>
DASAR: phase3/F3_protocol_v1.md = APPROVED (14 Nov 2026). Ikuti PERSIS.
CAKUPAN: Tugas A = persiapan data, paket kode auto_sqpca, uji sintetis
T1-T8, dan E1. TIDAK ADA E2/E3.

LANGKAH 0 - Verifikasi
- Verifikasi SHA-256 artefak beku Fase 1-2 (G0..G4-R) yang dipakai: snapshot
  WDC COI, IQD GFZ, kode beku G2-R (V1), loader K11.
- Semua keluaran di phase3/. Jangan mengubah folder lain.

LANGKAH 1 - Paket kode
- phase3/auto_sqpca/: modul io (S1), localtime (S2), gaps (M-INT, M-EXC,
  M-EM), pca (S4-S5, gunakan ulang inti V1 G2-R), candidates (S6),
  selection (S7-S8, surrogate IC1 G4-R), bootstrap (S9), abstain (S10),
  ssb (bagian 4), metrics. Satu titik masuk CLI.

LANGKAH 2 - Uji sintetis T1-T8 (bagian 8)
- tests/; log ke F3_synthetic_tests.json. T6 gagal -> catat keterbatasan,
  lanjut. Lainnya gagal -> bagian 10.

LANGKAH 3 - Data
- Data per jam KDU, GUA 2014-2018 (dan PLR, TUN 2017; HUA, TTB, MBO hanya
  bila syarat E3b) sesuai S1; catat sumber, hash, tanggal unduh.
- Topeng TND 2017 per jam dari data menit Fase 1.
- F3_data_inventory.csv: stasiun x bulan: jam valid, kelayakan E1 (99%),
  E2 (95%), sumber data, Δ LT.

LANGKAH 4 - E1 pengembangan
- Set pengembangan (3.1), semua topeng (3.2), tiga metode (3.3), metrik
  (3.4). Pilih metode (3.5). Bekukan F3_E1_frozen.json + SHA-256.
- JANGAN menghitung holdout sebelum pembekuan.

LANGKAH 5 - E1 holdout (satu kali)
- Kurva galat, p* (eps 0,05; sensitivitas 0,03 dan 0,10), topeng TND,
  uji keunggulan (3.5). Label C1 sesuai bagian 7.
- Gambar 1 dan 2 (bagian 11).

LANGKAH 6 - Paket
- F3A_report.md, F3A_execution.log, F3A_checksums.sha256 (berkas isi).
- F3A_review.zip tanpa data mentah; SETELAH ZIP final, SHA-256 ke
  F3A_review.zip.sha256 DI LUAR ZIP.

LARANGAN: bagian 9. KONDISI BERHENTI: bagian 10.
JIKA RAGU: UNRESOLVED dengan bukti; jangan menebak.
SELESAI: BERHENTI dan laporkan satu paragraf: metode terpilih, p* per jenis
topeng, hasil TND, uji keunggulan, status C1.
```

### Tugas B — E2 + E3 (setelah paket Tugas A direview)

```text
PERAN, PROYEK, DASAR: sama dengan Tugas A.
CAKUPAN: E2 (SSB, C2, C3) dan E3 (transfer, C4). E1 sudah beku; jangan
diubah.

LANGKAH 0 - Verifikasi hash F3_protocol_v1.md, F3_E1_frozen.json, dan
paket kode Tugas A.

LANGKAH 1 - SSB (bagian 4)
- Bangun data semi-sintetis untuk set pengembangan dan holdout; DIFI-8 via
  pyDIFI (catat versi). Bila pyDIFI gagal: TRUTH_FALLBACK (bagian 10).
- F3_ssb_manifest.csv (bulan, komponen, alpha, topeng, replikasi, seed).

LANGKAH 2 - E2 pengembangan
- ASAL, AUTO-NA, AUTO (5.1); grid theta (5.3); pilih dan bekukan
  F3_E2_frozen.json + SHA-256 sebelum holdout.

LANGKAH 3 - E2 holdout (satu kali)
- Uji C2 dan C3 (5.4), kurva risk-coverage, uji alpha = 0. Label C2, C3
  sesuai bagian 7. Gambar 3, tabel 4.

LANGKAH 4 - E3 (bagian 6)
- Pipeline beku tanpa perubahan pada COI, KDU, GUA, PLR, TUN (+ E3b bila
  syarat terpenuhi). Metrik 6.2; lintang geomagnet dipol IGRF-13 2015.
- Gambar/tabel 5, contoh kurva 6, tabel parameter 7.

LANGKAH 5 - Ringkasan klaim
- F3_claims.json: status C1-C4, judul yang diizinkan menurut bagian 7,
  kalimat klaim yang boleh dipakai.

LANGKAH 6 - Paket
- F3B_report.md, F3B_execution.log, F3B_checksums.sha256.
- F3B_review.zip tanpa data mentah; SHA-256 ke F3B_review.zip.sha256 DI
  LUAR ZIP.

LARANGAN: bagian 9. KONDISI BERHENTI: bagian 10.
SELESAI: BERHENTI dan laporkan satu paragraf: theta beku, hasil C2, C3,
coverage holdout, ringkasan E3 per stasiun, judul yang diizinkan.
```
