# S7-A — Audit kontradiksi benchmark Mendeley dan baseline Sq

**Keputusan: S7 PARTIALLY RESOLVED. Rekomendasi G1: HOLD.** Enam duplikasi Y/Z Februari dan pemusatan 24 jam seluruh Sq/SD/S terverifikasi. Mekanisme pengolahan/ekspor sumber, seri WDC yang dipakai penulis, dan beberapa inkonsistensi mode tetap belum terpecahkan.

## Cakupan, sumber, dan aturan

- Protokol beku `G0-registration-1` dibaca tanpa perubahan. D1-PCA CONFIRMED, D1-IQD PROVISIONAL, D2-TIME CONFIRMED untuk XYZ, D2-DATA F UNRESOLVED, dan D2-BENCHMARK SOURCE_DISCREPANCY tetap sebagaimana dilaporkan.
- [Artikel data Morozova, Rebbah, Ribeiro (2021)](https://arxiv.org/pdf/2103.13899) menyebut Sq lima IQD GFZ dan baseline lima jam malam per hari (00:30, 01:30, 02:30, 03:30, 23:30 menurut tabel jam; teks menulis 02:03). Artikel mendeskripsikan mode sebagai hasil PC dan EOF. Datum Mendeley V1 `10.17632/jcmdrm5f5x.1` dipakai sebagaimana tersimpan di G0.
- Hanya produk `PC × EOF` terbitan Mendeley dihitung, tanpa PCA/SVD baru pada WDC. Produk disusun `outer(EOF_day, PC_hour)` lalu diratakan berurutan hari-jam. Skala bertanda optimal dipasang **hanya untuk diagnosis bentuk**; galat langsung pada skala 1 tetap ditampilkan. Nilai `|r|` sendiri tidak membuktikan amplitudo.
- Sq kontrol memakai lima IQD GFZ resmi, baseline per hari dari indeks jam UTC `[0,1,2,3,23]`, tanpa interpolasi. Enam bulan kontrol dipilih karena 5×24 nilai X/Y/Z valid: 2008-01, 2008-03, 2012-06, 2016-10, 2017-06, 2017-10. Toleransi Tingkat 1 Sq maksimum absolut ≤0,1 nT **tidak diubah**.

## A. Enam pasangan Y/Z Februari

Keenam pasangan berikut identik **byte demi byte**; header, jumlah baris, dan kolom juga identik. Hash di bawah adalah SHA-256 yang sama untuk Y dan Z; path lengkap kedua sisi ada di `S7_decision.json` dan manifest.

| Keluaran | Cakupan | Baris × kolom | SHA-256 Y=Z |
|---|---|---:|---|
| meanField | per_year | 28×12 | `0711725279a00903e357cc37740470cf1cc6f43de1daade0730a23cd065bb873` |
| meanField | all_years | 308×2 | `ff2a177dc221cc9155b79c22df1c984b390f166dc484a01c354eae6941bdd220` |
| mode1 | per_year | 672×12 | `4597a176d1b6cbdd4908e44c866a5dde101de8a35b2270a31cce5c56bb2bb059` |
| mode1 | all_years | 7392×2 | `de3975981e87c45aa871cc5600a078c9864d0933db270453fd747ee456754fc5` |
| mode2 | per_year | 672×12 | `92114eee1c91650ee352ee7582e2b31cd62a3d7a85a615a2279f3d944983d6ca` |
| mode2 | all_years | 7392×2 | `3da2fb56e6a89a894ab0f61818859077d09f22cdc9fdb85bfa2c07bd4f6b933d` |

### Rekonstruksi PC × EOF dan kontrol tetangga

Tabel ini memuat tahun 2008 untuk kontrol Januari/Februari/Maret, serta keluaran gabungan. RMSE fit dan residu Frobenius relatif memakai skala bertanda optimal; RMSE langsung memakai faktor 1. Residu relatif 0 berarti bentuk beserta skala bertanda cocok.

| Bulan | Mode | Cakupan | Mode berlabel Y vs PC×EOF | Skala fit | RMSE langsung (nT) | RMSE fit (nT) | Residu relatif |
|---:|---:|---|:---:|---:|---:|---:|---:|
| 01 | 1 | 2008 | Y←Y | 1.000000 | 1.524e-14 | 1.519e-14 | 2.353e-15 |
| 01 | 1 | 2008 | Y←Z | 0.751312 | 5.751 | 5.658 | 0.8763 |
| 01 | 1 | all | Y←Y | 1.000000 | 1.563e-14 | 1.518e-14 | 2.265e-15 |
| 01 | 1 | all | Y←Z | 0.674543 | 6.136 | 5.952 | 0.8879 |
| 01 | 2 | 2008 | Y←Y | 1.000000 | 4.523e-15 | 4.578e-15 | 2.419e-15 |
| 01 | 2 | 2008 | Y←Z | 0.382681 | 2.016 | 1.81 | 0.9569 |
| 01 | 2 | all | Y←Y | 1.000000 | 4.252e-15 | 4.241e-15 | 1.935e-15 |
| 01 | 2 | all | Y←Z | 0.508679 | 2.181 | 2.028 | 0.9256 |
| 02 | 1 | 2008 | Y←Y | 0.483188 | 5.82 | 4.317 | 0.7638 |
| 02 | 1 | 2008 | Y←Z | 1.000000 | 1.314e-14 | 1.307e-14 | 2.313e-15 |
| 02 | 1 | all | Y←Y | 0.480040 | 7.1 | 5.631 | 0.8157 |
| 02 | 1 | all | Y←Z | 1.000000 | 1.344e-14 | 1.329e-14 | 1.926e-15 |
| 02 | 2 | 2008 | Y←Y | 0.482491 | 1.939 | 1.432 | 0.7614 |
| 02 | 2 | 2008 | Y←Z | 1.000000 | 5.072e-15 | 5.063e-15 | 2.692e-15 |
| 02 | 2 | all | Y←Y | 0.293692 | 2.495 | 1.594 | 0.8941 |
| 02 | 2 | all | Y←Z | -1.000000 | 3.565 | 3.544e-15 | 1.988e-15 |
| 03 | 1 | 2008 | Y←Y | 1.000000 | 2.263e-14 | 2.265e-14 | 2.368e-15 |
| 03 | 1 | 2008 | Y←Z | 0.672469 | 8.206 | 7.735 | 0.8086 |
| 03 | 1 | all | Y←Y | 1.000000 | 2.397e-14 | 2.319e-14 | 1.992e-15 |
| 03 | 1 | all | Y←Z | 0.735676 | 9.636 | 9.303 | 0.7992 |
| 03 | 2 | 2008 | Y←Y | 1.000000 | 6.188e-15 | 5.563e-15 | 2.185e-15 |
| 03 | 2 | 2008 | Y←Z | 0.638654 | 2.232 | 2.068 | 0.8124 |
| 03 | 2 | all | Y←Y | 1.000000 | 8.462e-15 | 8.462e-15 | 2.375e-15 |
| 03 | 2 | all | Y←Z | -0.803668 | 5.64 | 2.821 | 0.7918 |

Pada Februari, mode Y per tahun cocok **persis** dengan PC×EOF Z pada 10 dari 11 tahun untuk masing-masing mode; tahun 2014 adalah pengecualian karena mode Z sendiri tidak cocok persis dengan PC×EOF Z. Mode gabungan 1 cocok persis; mode gabungan 2 adalah negatif PC×EOF Z (skala −1, residu fit ~nol). Mode Y tidak cocok dengan PC×EOF Y bahkan setelah tanda/skala bebas. Januari 2008 dan Maret 2008 menunjukkan mode Y cocok dengan Y sendiri pada skala 1 dan tidak cocok dengan Z. Ini mendukung salah label/salin pada enam berkas, tanpa membuktikan proses yang menyebabkan kesalahan itu.

Pengecualian tambahan: Z Februari 2014 per tahun memiliki RMSE setelah skala bertanda 0,7439 nT (mode 1) dan 0,3409 nT (mode 2); file PC, EOF, dan mode mana yang bertanggung jawab belum dapat ditentukan. Januari 2010 Y memiliki residu kecil 0,00035/0,00023 nT untuk mode 1/2. Mode gabungan 2 Maret Z juga berbeda tanda (−1) tetapi tepat setelah tanda diperhitungkan. Normalisasi final masih D4.

**Adjudikasi:** enam berkas Februari berlabel Y untuk `meanField`, `mode1`, `mode2` (tahunan/gabungan) **UNUSABLE_FOR_NUMERIC_BENCHMARK** komponen Y. PC/EOF Y Februari berbeda dari Z dan tetap **SUSPECT**, dapat diuji secara independen kelak tetapi tidak divalidasi menggunakan mode Y yang salah label. Enam berkas Z Februari per tahun yang terkait PC/EOF/mode 1/2 diberi **SUSPECT** karena kasus 2014; berkas Z lainnya tidak otomatis gagal.

## B. Baseline Sq dan pola seluruh bulan

Ke-36 DAT IQD berisi masing-masing 24 jam × 37 kolom (`h` dan 12 kolom per Sq, SD, S). Dari 432 kolom per jenis, maksimum nilai mutlak mean 24 jam adalah:

| Jenis | Kolom | Maks. |mean 24 jam| (nT) | Kolom dengan |mean malam| >0,1 nT | Median |mean malam| (nT) |
|---|---:|---:|---:|---:|
| Sq | 432 | 1.94e-12 | 426 | 3.0267 |
| SD | 432 | 2.02e-12 | 415 | 1.4720 |
| S | 432 | 1.05e-12 | 427 | 3.5303 |

Identitas internal `S = Sq + SD` juga diperiksa pada 432 kombinasi komponen/bulan/tahun; maksimum |S−Sq−SD| = 1.02e-13 nT. Jadi kolom Sq, SD, dan S konsisten secara aljabar.

Pemusatan mean 24 jam adalah sifat **sistematis** seluruh berkas IQD Mendeley, bukan hanya Februari. Ini belum menentukan apakah penulis memakai baseline mean harian sejak awal, menambahkan pemusatan sesudah baseline malam, atau melakukan transformasi saat ekspor. Dua rumus terakhir yang dibandingkan di bawah (`daily_mean` dan `night_then_center`) ekuivalen secara aljabar untuk rerata linear, sehingga tidak dihitung sebagai dua konfirmasi terpisah.

### Pembandingan enam bulan di luar Februari

RMSE bentuk = RMSE sesudah offset rerata 24 jam selisih dihilangkan; kolom maksimum untuk `daily_mean` adalah maksimum absolut selisih per jam, relevan ke ambang beku. Semua besaran kecuali korelasi dalam nT.

| Tahun-bulan | Komp. | IQD Q1–Q5 | RMSE malam abs. | RMSE mean harian abs. / bentuk | Maks. abs. mean harian | r | Offset malam |
|---|:---:|---|---:|---:|---:|---:|---:|
| 2008-01 | X | 3,2,22,30,4 | 1.9093 | 0.0863 | 0.2067 | 0.999733 | +1.9073 |
| 2008-01 | Y | 3,2,22,30,4 | 3.7669 | 0.1335 | 0.2775 | 0.999800 | -3.7645 |
| 2008-01 | Z | 3,2,22,30,4 | 0.2720 | 0.1602 | 0.3425 | 0.998884 | -0.2198 |
| 2008-03 | X | 7,6,24,25,4 | 1.1056 | 0.1279 | 0.2725 | 0.998751 | +1.0982 |
| 2008-03 | Y | 7,6,24,25,4 | 3.8633 | 0.1110 | 0.2117 | 0.999934 | -3.8617 |
| 2008-03 | Z | 7,6,24,25,4 | 4.1797 | 0.1355 | 0.2808 | 0.999900 | -4.1775 |
| 2012-06 | X | 19,15,21,14,20 | 3.5650 | 0.1457 | 0.2950 | 0.999727 | +3.5620 |
| 2012-06 | Y | 19,15,21,14,20 | 2.4255 | 0.1142 | 0.2992 | 0.999976 | -2.4228 |
| 2012-06 | Z | 19,15,21,14,20 | 5.1557 | 0.1099 | 0.2058 | 0.999962 | -5.1545 |
| 2016-10 | X | 21,11,20,9,22 | 0.6505 | 0.0856 | 0.2958 | 0.999884 | -0.6448 |
| 2016-10 | Y | 21,11,20,9,22 | 4.8095 | 0.0990 | 0.3075 | 0.999969 | -4.8085 |
| 2016-10 | Z | 21,11,20,9,22 | 3.6791 | 0.0901 | 0.2067 | 0.999963 | -3.6780 |
| 2017-06 | X | 4,20,10,8,30 | 0.3922 | 0.0964 | 0.1725 | 0.999735 | +0.3802 |
| 2017-06 | Y | 4,20,10,8,30 | 1.3930 | 0.1103 | 0.2233 | 0.999971 | -1.3887 |
| 2017-06 | Z | 4,20,10,8,30 | 5.6275 | 0.1155 | 0.2683 | 0.999942 | -5.6263 |
| 2017-10 | X | 30,9,29,31,10 | 0.8428 | 0.1166 | 0.2183 | 0.998592 | +0.8347 |
| 2017-10 | Y | 30,9,29,31,10 | 3.7848 | 0.1379 | 0.2567 | 0.999911 | -3.7823 |
| 2017-10 | Z | 30,9,29,31,10 | 3.6761 | 0.1433 | 0.3017 | 0.999851 | -3.6733 |

Pada 18 kontrol XYZ, RMSE absolut malam 0.2720–5.6275 nT; setelah mean harian 0.0856–0.1602 nT, dengan r 0.998592–0.999976. Namun maksimum absolut mean harian 0.1725–0.3425 nT: **0/18** memenuhi ≤0,1 nT. Kecocokan bentuk sangat kuat, tetapi reproduksi numerik Tingkat 1 tetap gagal pada kontrol ini.

**Pemisahan hipotesis:** offset beberapa nT tidak dijelaskan oleh kuantisasi WDC 0,1 nT saja. Kuantisasi/pembulatan dapat berkontribusi ke residu bentuk kecil, tetapi 0,17–0,34 nT maksimum setelah pemusatan tidak boleh langsung dianggap akibat pembulatan. Versi WDC saat penulis menghitung data dan langkah pemusatan/ekspor tidak tersedia; kedua hal itu belum dapat dipisahkan. Duplikasi Y/Z sudah terbukti pada isi file, sedangkan alasan kesalahan ekspor/salin hanya hipotesis. Tidak ada validasi fisis Sq di S7.

## C. Karantina dan implikasi gate

`S7_benchmark_manifest.csv` mencakup **seluruh 684 DAT numerik** Mendeley, path asli, SHA-256, ukuran, status, dan batas pemeriksaan. Plot PNG tetap tercatat di inventaris G0, tetapi bukan benchmark DAT numerik. Ringkasan status: **624 VERIFIED, 54 SUSPECT, 6 UNUSABLE_FOR_NUMERIC_BENCHMARK**. VERIFIED berarti tidak ditemukan kontradiksi pada pemeriksaan yang dilakukan, bukan jaminan validitas ilmiah penuh. Tidak ada DAT yang diubah atau referensi turunan yang dipromosikan menjadi ORIGINAL.

- **Lokal/sistematis:** duplikasi label Y/Z terbatas enam berkas Februari di antara pasangan yang diperiksa D2; satu inkonsistensi Z 2014 memerlukan pemeriksaan kelak. Mean 24 jam nol berlaku sistematis pada Sq, SD, S sepanjang 12 bulan dan 12 kolom tahun/gabungan.
- **D1-IQD tetap PROVISIONAL:** Q5 resmi 29 Februari 2016 unggul dalam bentuk menurut D1, tetapi offset absolut dan provenans versi WDC belum tuntas. D2-TIME sudah mengonfirmasi pemetaan HH:00 WDC ke jendela 00–59 menit untuk XYZ, sehingga ketidakpastian waktu berkurang tanpa menuntaskan benchmark.
- **F dapat diajukan untuk ditunda pada jalur PCA XYZ:** artikel sumber menyebut hanya X/Y/Z sebagai masukan PCA; ini tidak mengubah D2-DATA F yang masih UNRESOLVED. Keputusan penundaan perlu dicatat pada versi protokol baru.
- **G1 HOLD:** ambang Sq absolut beku tidak terpenuhi pada kontrol; enam target Y numerik tidak dapat dipakai; D1-IQD provisional dan inkonsistensi Z 2014 masih ada. G1 CONDITIONAL PASS baru layak dipertimbangkan setelah amandemen yang membatasi benchmark diterima dan bukti tambahan sesuai kriteria tertulis tersedia. Proposal terpisah di bawah belum berlaku.

## Reproduksibilitas dan batas

Jalankan `python -B phase2a/S7/s7_investigate.py` lalu `python -B phase2a/S7/s7_finalize.py`. Input hash per DAT ada di manifest, hash pasangan duplikat dan input representatif ada di `S7_decision.json`, serta setiap baris mode/Sq mencatat path/hash yang dipakai. Hash 3.659 raw, 11 ZIP menit beku, dan 16 berkas G0/D1/D2/protokol cocok **sebelum dan sesudah** komputasi. CSV mencatat 288 pembandingan mode dan 1.350 baris Sq (1.296 kolom asli + 54 rekonstruksi); log menyimpan tahapan dan kesalahan asli bila muncul. Python/NumPy/platform dicatat di JSON. ZIP review hanya berisi kode, tabel, laporan, JSON, dan log kecil. Tidak ada unduhan, PCA/SVD WDC, D3/D4, DTW, DIFI, atau classifier.

**Keputusan akhir: S7 PARTIALLY RESOLVED; G1 HOLD.**
