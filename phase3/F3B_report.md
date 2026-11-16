# Fase 3 Tugas B — E2, E3, dan audit klaim

**C1 BERHASIL; C2 GAGAL; C3 GAGAL; C4 DESKRIPTIF; C5 PARSIAL.** Judul yang didukung: *Auto-SqPCA: A Quality-Aware Workflow for Extracting Solar Quiet Geomagnetic Variations at Low and Equatorial Latitudes*.

## Dasar dan integritas

Protokol F3-v1 SHA-256 `617c96d0cbda26fa3f6333ea1638030a35db1836fd99ba35f2a3bb18ea091327` dan amandemen F3-v1.1 SHA-256 `8dae6289ef71f1829d37ba6d5726253fd206c679221da7106b1a820421900a8f`. E1 tetap beku: konfigurasi `a2a2cd09ccf4c16c87a9033d792de80762d253c2db16455f81cc4329ad26981d`, CSV holdout `1acbda1a8825b6b878704395973fea0c37b4fd1324ee470df106f2344d1aceb3`. ZIP review Tugas A tetap `ece7681a70c886966f3ad6818288f5277f3cfe7f8203bbb8e29af2cf9be5c1d8`. Preflight menemukan 161 keluaran Fase 1–2 cocok hash, 42 ZIP menit dan 3.702 entri G0 tervalidasi. Verifikasi cache reproduksi F3A lulus 9 tahap; ini **belum** membuktikan satu perintah membangun ulang seluruh Fase 3 dari data mentah (C5 parsial).

## Pelaporan tambahan E1

`F3_E1_secondary_metrics.csv` memuat kandidat tetap, sudut PC1, dan kesepakatan kandidat untuk 69 kombinasi metode–topeng–p, dengan penyebut berhingga dicatat. M-EM mencapai 500 iterasi pada 116,777/185,220 kasus (63.0%); di antaranya 6.5% memiliki perubahan akhir <10⁻⁴ nT dan 2.6% <10⁻⁶ nT. Ini temuan deskriptif, tidak mengubah C1 atau p*. Review amandemen menerima guard M-EM 10⁻⁸ nT dan koreksi GFZ 2018 dengan pengungkapan; topeng DAY setara menurut konstruksi.

## SSB dan E2

SSB memakai 162 bulan QC≥95% dan 8,748 kasus, `pyDIFI` 8.1.5 dengan `model_name=DIFI8` eksplisit; default pustaka ialah xDIFI2 sehingga tidak dipakai. Kurva DIFI-8 dirata-ratakan atas hari pada jam LT HH:30, lalu dipusatkan. Residu berasal dari observasi yang diisi M-EM dan dipusatkan V1. Hash koefisien DIFI dan F10.7 ada di `F3_ssb_month_provenance.json`. Sebanyak 19 sampel UTC (GUA 2014-01: 10; KDU 2014-01: 9) jatuh pada 31 Desember 2013 karena pergeseran LT; `pyDIFI` memberi peringatan bahwa waktu ini di luar rentang rekomendasi DIFI-8, tetapi menghasilkan nilai. Titik batas itu dipertahankan dan dampaknya belum diuji terpisah.

Pengembangan E2: 58 bulan, 3.132 kasus; tidak ada titik grid dengan coverage strata tanpa topeng ≥80%. Sesuai A-4, dipilih coverage terbesar: **θ_s=0.5, θ_w=INF, θ_d=0.9**, coverage pengembangan 73.24%. Konfigurasi dibekukan SHA-256 `7a4597814baad09c6fe1ca781f991181c7286ba1c6fca2f376c7e6cf8592a34e` sebelum holdout. Holdout: 104 bulan, 5.616 kasus; strata utama 2.808 tanpa topeng dan strata bertopeng 2.808 MCAR 20%.

**C2:** untuk X, median selisih berpasangan galat ASAL − AUTO-NA = 0.00000, CI 95% [0.00000, 0.00000]; batas bawah tidak >0. Y/Z ada di `F3_E2_C2.csv`. **C3:** median galat semua AUTO-NA 0.06560 versus AUTO diterima 0.04623; selisih 0.01937, CI 95% [0.01564, 0.02275]. Coverage utama 74.18% <80%, sehingga C3 gagal walau selisih positif. Seluruh 2,808 kasus bertopeng abstain; A3 berlaku pada semuanya (alasan bisa tumpang tindih). Uji α=0: 205/312 tidak diterima (65.7%); 31 kasus menghasilkan korelasi kandidat tidak terdefinisi dan dicatat sebagai `ERROR`, tidak disamakan dengan keputusan abstain A1 murni. Residu R masih mengandung variasi Sq nyata menurut konstruksi SSB.

## E3 transfer nyata

E3 utama memakai 190 bulan di COI, KDU, GUA, PLR, TUN; E3b eksploratoris memakai 166 bulan di HUA, TTB, MBO yang memenuhi syarat manifest Fase 1. E3b menurunkan jam dari ZIP menit beku dengan 60 menit XYZ valid per jam dan aturan A. Pipeline M-EM/V1/S7–S10 serta θ beku dipakai tanpa penyetelan stasiun. DIFI-8 adalah acuan evaluasi utama; korelasi IQD ditandai tidak independen. Lintang geomagnet dihitung dari dipol terpusat IGRF-13 epoch 2015 (`ppigrf` 1.1.0, koefisien dan rumus di `F3_E3_provenance.json`). Audit sesudah perhitungan menemukan lintang geodetik metadata perlu dikonversi ke arah radial geosentris sebelum rumus dipol; hanya kolom lintang geomagnet dikoreksi (maksimum 0.18543°), dengan CSV awal dan hash disimpan di `phase3/work/E3_cases_before_geocentric_lat_fix.csv`. Semua metrik kurva, keputusan abstain, dan hasil E2 tetap identik. Dari 1,068 kasus komponen, 69 tidak mempertahankan semua hari setelah M-EM; indeks IQD tidak digeser dan kasus itu abstain.

| Stasiun | Cakupan | Bulan | Diterima/kasus | Median r AUTO–DIFI | Abstain |
|---|---|---:|---:|---:|---:|
| COI | utama | 48 | 98/144 | 0.915 | 31.9% |
| KDU | utama | 60 | 154/180 | 0.961 | 14.4% |
| GUA | utama | 60 | 138/180 | 0.959 | 23.3% |
| PLR | utama | 10 | 12/30 | 0.698 | 60.0% |
| TUN | utama | 12 | 24/36 | 0.938 | 33.3% |
| HUA | E3b eksploratoris | 60 | 140/180 | 0.950 | 22.2% |
| TTB | E3b eksploratoris | 51 | 121/153 | 0.926 | 20.9% |
| MBO | E3b eksploratoris | 55 | 143/165 | 0.966 | 13.3% |

Rincian per komponen, alasan A1–A4, rasio amplitudo, perbandingan berpasangan terhadap ASAL, lebar pita bootstrap, dan korelasi IQD ada di `F3_E3_cases.csv` serta `F3_E3_station_summary.csv`. Gambar 3 menunjukkan risk–coverage, Gambar 4 transfer menurut lintang dipol, dan Gambar 5 kurva contoh dengan pita 90% untuk COI/KDU/PLR/TUN. Temuan ini deskriptif untuk stasiun yang diuji; tidak mendukung klaim umum “berlaku untuk Indonesia”.

## Klaim dan batas

C1 mendukung kata **Quality-Aware**. C2 gagal, sehingga kombinasi PC dilaporkan sebagai opsi. C3 gagal, sehingga **Uncertainty-Guided** tidak boleh dipakai pada judul atau klaim. C5 parsial karena pembungkus Tugas A menjalankan verifikasi hash cache, bukan pembangunan ulang penuh satu perintah. Paket review hanya memuat laporan, kode, tabel, gambar, log, dan metadata kecil; matriks kerja, ZIP WDC/Mendeley, serta data mentah tidak disertakan. Hasil E1 dan Fase 1–2 tidak diubah.
