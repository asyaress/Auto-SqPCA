# D2 — Audit hourly WDC, minute Fase 1, waktu, dan benchmark Mendeley

**Keputusan D2: CONDITIONAL PASS.** D2-TIME **CONFIRMED**; D2-DATA **UNRESOLVED** (XYZ setara, F belum terjelaskan); D2-BENCHMARK **SOURCE_DISCREPANCY**. **G1 belum PASS dan ditahan untuk review S7 bersama D1-IQD provisional.**

## Sumber, integritas, dan aturan

- Input yang dibaca: 11 ZIP COI hourly G0, 11 ZIP COI minute Fase 1, GFZ IQD Februari 2008/2012/2016, dan DAT Mendeley asli. `D2_validation.json` mencatat SHA-256 460 berkas yang dipakai serta hash konfigurasi Fase 1/G0/D1. Seluruh 3,659 berkas raw dan 11 ZIP minute cocok dengan manifest G0 sebelum dan sesudah eksekusi; hash konfigurasi beku juga identik.
- IAGA-2002/XYZF diverifikasi pada 4,018 header berkas harian minute dan 132 header bulanan hourly. Data minute mempunyai 5,785,920 timestamp pada 4.018 hari, hourly 96,432 timestamp. Tidak ada timestamp yang hilang dari arsip; sentinel komponen tetap diperlakukan missing. Nilai nonmissing X/Y/Z/F berada pada grid 0,1 nT meski dicetak dua desimal.
- Header arsip hourly hanya menyebut `Data Interval Type 1-hour`; batas menit rerata **UNKNOWN dari metadata arsip itu sendiri**. [Standar INTERMAGNET](https://tech-man.intermagnet.org/latest/chapters/submitdata/standardsformeans.html) menetapkan mean aritmetika menit 00–59, berpusat pada HH:29:30, dan mengizinkan hasil bila ≥90% menit tersedia. [Panduan WDC Edinburgh](https://wdc.bgs.ac.uk/how-to-guide) menyatakan semua waktu UTC. Data diuji langsung di bawah ini.
- A = mean menit HH:00–HH:59; B = mean HH−30–HH+29; C = menit tepat HH:00. Perbandingan utama A/B memakai **60 dari 60 menit valid** untuk komponen bersangkutan, tanpa interpolasi. Jam yang tidak lengkap dicatat satu per satu di `D2_timestamp_diagnostics.csv` dan dikeluarkan dari metrik utama.

## Perbandingan seluruh periode 2007–2017

Galat = hourly WDC − kandidat dari minute Fase 1. Semua angka di tabel berikut berasal dari jam berpasangan sesuai aturan validitas tiap kandidat; C hanya membutuhkan satu menit.

| Komp. | Kandidat | Pasangan | Mean / median (nT) | MAE / RMSE (nT) | P95 / maks. | r | ≤0,1 nT |
|:---:|:---:|---:|---:|---:|---:|---:|---:|
| X | A | 92,963 | -0.049 / -0.050 | 0.049 / 0.057 | 0.095 / 0.098 | 1.000000 | 100.00% |
| X | B | 92,924 | -0.047 / 0.057 | 2.206 / 3.432 | 6.855 / 93.798 | 0.999323 | 4.55% |
| X | C | 95,009 | -0.057 / 0.000 | 2.559 / 4.079 | 8.100 / 83.400 | 0.999039 | 5.78% |
| Y | A | 92,964 | 0.049 / 0.048 | 0.049 / 0.057 | 0.093 / 0.098 | 1.000000 | 100.00% |
| Y | B | 92,925 | 0.052 / 0.398 | 2.692 / 3.889 | 8.335 / 43.422 | 0.999817 | 4.08% |
| Y | C | 95,009 | 0.054 / 0.400 | 2.961 / 4.362 | 9.000 / 55.900 | 0.999769 | 5.43% |
| Z | A | 92,967 | -0.049 / -0.050 | 0.049 / 0.057 | 0.093 / 0.098 | 0.999998 | 100.00% |
| Z | B | 92,928 | -0.048 / -0.065 | 1.879 / 2.754 | 6.023 / 25.553 | 0.983918 | 6.63% |
| Z | C | 95,009 | -0.017 / 0.000 | 2.013 / 2.941 | 6.300 / 29.900 | 0.981853 | 8.80% |
| F | A | 88,749 | -0.067 / -0.067 | 0.068 / 0.078 | 0.135 / 0.192 | 1.000000 | 79.25% |
| F | B | 88,715 | -0.066 / 0.048 | 1.944 / 2.884 | 5.952 / 76.037 | 0.997692 | 5.45% |
| F | C | 90,765 | -0.043 / 0.100 | 2.173 / 3.277 | 6.600 / 76.200 | 0.996998 | 7.15% |

Korelasi tinggi pada B/C tidak menentukan konvensi: komponen geomagnet mempunyai level dan variasi lambat yang mendominasi r. MAE, RMSE, persentase dalam 0,1 nT, pola residu, dan aturan pembulatan semuanya memilih A untuk X/Y/Z.

### Resolusi, pemotongan, dan data hilang

| Komp. | Jam A lengkap & hourly valid | Cocok tepat dengan pemotongan menuju nol ke 0,1 nT | Selisih dari aturan itu | Hourly valid dengan 54–59 menit | Hourly missing dengan ≤53 menit |
|:---:|---:|---:|---:|---:|---:|
| X | 92,963 | 100.0000% | 0 | 2,055 | 1,414 |
| Y | 92,964 | 100.0000% | 0 | 2,054 | 1,414 |
| Z | 92,967 | 100.0000% | 0 | 2,051 | 1,414 |
| F | 88,749 | 74.5608% | 22,577 | 2,024 | 5,659 |

Untuk X/Y/Z, **setiap** mean A dari 60 menit valid sama dengan hourly setelah dipotong menuju nol pada 0,1 nT; tidak ada mismatch. Pola mean residu sekitar −0,049 nT untuk X/Z dan +0,049 nT untuk Y sesuai arah pemotongan nilai positif/negatif. Semua komponen menunjukkan batas ketersediaan tepat 54/60 menit: tidak ada hourly valid di bawah 54 atau hourly missing pada 54 ke atas. Ini bukti empiris aturan 90%, tetapi metrik A/B tetap memakai 60/60.
F berbeda: 22,577/88,749 jam A lengkap tidak cocok dengan pemotongan serupa, dengan selisih tambahan maksimum 0.100 nT. Penyebabnya tidak dapat dipastikan dari arsip ini; F tidak dipakai untuk menjustifikasi kesetaraan X/Y/Z atau keputusan PCA. Perbedaan F tidak disebut revisi historis tanpa arsip versi lama.

## Bulan fokus dan batas waktu

Tabel bulanan penuh untuk semua tahun dan komponen ada di `D2_hourly_vs_minute.csv`. Berikut bulan yang diwajibkan, memakai MAE X/Y/Z (nT); `A pasangan X` dan `A tidak lengkap X` memperlihatkan dampak missing.

| Bulan | A MAE X/Y/Z | B MAE X/Y/Z | C MAE X/Y/Z | A pasangan X | A tidak lengkap X |
|---|---:|---:|---:|---:|---:|
| 2008-02 | 0.050/0.050/0.049 | 2.726/2.269/1.523 | 3.161/2.777/1.744 | 668 | 28 |
| 2012-02 | 0.051/0.049/0.051 | 2.396/2.224/1.676 | 2.739/2.528/1.859 | 667 | 29 |
| 2016-02 | 0.049/0.049/0.050 | 2.255/2.809/1.718 | 2.663/3.157/1.939 | 694 | 2 |
| 2012-01 | 0.052/0.048/0.050 | 1.881/1.998/1.212 | 2.147/2.201/1.380 | 499 | 245 |
| 2013-01 | 0.051/0.048/0.052 | 1.777/1.546/1.213 | 1.990/1.682/1.289 | 500 | 244 |
| 2008-05 | 0.047/0.050/0.049 | 1.953/2.181/1.784 | 2.243/2.345/1.913 | 552 | 192 |
| 2017-06 | 0.050/0.050/0.051 | 2.028/2.763/1.957 | 2.335/2.931/2.042 | 720 | 0 |
| 2017-10 | 0.049/0.050/0.050 | 2.579/2.936/2.046 | 3.078/3.316/2.235 | 743 | 1 |

Pada bulan fokus, korelasi residu B terhadap kemiringan hourly X berkisar kuat positif (rinci di `D2_timestamp_diagnostics.csv`), sesuai salah letak jendela sekitar setengah jam. Residu A setelah median per hari dihilangkan mempunyai RMSE bentuk sekitar 0,03 nT pada X; pola ini konsisten dengan kuantisasi, bukan bukti revisi yang mengubah bentuk. Tidak ada klaim mengenai versi hourly yang dipakai penulis sekitar 2020.

Contoh B di batas periode menunjukkan indeks UTC benar dan tidak terpotong pada arsip tahunan:

| Timestamp hourly | Jendela B | Menit valid X/Y/Z/F |
|---|---|---|
| 2008-03-01 00:00:00 | 2008-02-29 23:30:00 – 2008-03-01 00:29:00 | 59/59/59/59 |
| 2012-01-01 00:00:00 | 2011-12-31 23:30:00 – 2012-01-01 00:29:00 | 60/60/60/60 |
| 2013-01-01 00:00:00 | 2012-12-31 23:30:00 – 2013-01-01 00:29:00 | 60/60/60/60 |
| 2016-03-01 00:00:00 | 2016-02-29 23:30:00 – 2016-03-01 00:29:00 | 60/60/60/60 |
| 2017-06-01 00:00:00 | 2017-05-31 23:30:00 – 2017-06-01 00:29:00 | 60/60/60/60 |
| 2017-07-01 00:00:00 | 2017-06-30 23:30:00 – 2017-07-01 00:29:00 | 60/60/60/60 |

Jam 2008-03-01 00:00 memiliki 59/60 menit valid pada B: ini missing nyata pada satu menit lintas batas, bukan kesalahan timestamp. Contoh 2012-01-01 dan 2013-01-01 melintasi tahun dengan 60/60 menit.

## Offset Sq Mendeley: Februari 2008, 2012, 2016

Tiga formulasi diuji pada lima IQD GFZ resmi: (1) baseline rerata lima jam malam per hari, (2) rerata 24 jam per hari, (3) baseline malam lalu pusatkan kurva rata-rata ke mean 24 jam nol. Formulasi 2 dan 3 ekuivalen secara aljabar untuk rata-rata linear; maksimum selisih numeriknya 9.1e-13 nT, sehingga bukan dua bukti independen. Februari 2016 memakai 29 Februari sesuai hipotesis D1-IQD yang masih provisional.

| Tahun | Komp. | RMSE malam absolut | RMSE mean harian absolut | RMSE malam setelah offset dihilangkan | Mean residu malam | Mean malam acuan Mendeley |
|---:|:---:|---:|---:|---:|---:|---:|
| 2008 | X | 2.4927 | 0.1261 | 0.1261 | 2.4895 | -2.5450 |
| 2008 | Y | 3.0567 | 0.1076 | 0.1076 | -3.0548 | 3.1517 |
| 2008 | Z | 1.1381 | 0.1622 | 0.1622 | -1.1265 | 1.0367 |
| 2012 | X | 5.8871 | 0.1163 | 0.1163 | 5.8860 | -5.8983 |
| 2012 | Y | 6.0339 | 0.1111 | 0.1111 | -6.0328 | 6.0983 |
| 2012 | Z | 4.0140 | 0.1313 | 0.1313 | -4.0118 | 4.0283 |
| 2016 | X | 1.3475 | 0.1306 | 0.1306 | 1.3412 | -1.3967 |
| 2016 | Y | 5.2288 | 0.1078 | 0.1078 | -5.2277 | 5.2583 |
| 2016 | Z | 3.4724 | 0.1424 | 0.1424 | -3.4695 | 3.5150 |

Semua kurva Sq Mendeley yang diuji mempunyai mean 24 jam ≈0, tetapi mean lima jam malamnya tidak nol. Kurva baseline malam sebaliknya mempunyai mean lima jam malam ≈0. Selisih utama bersifat offset aditif: mean harian mengurangi RMSE absolut dari 1–6 nT menjadi sekitar 0,11–0,16 nT, sama dengan RMSE setelah offset dihilangkan. Korelasi dan beda amplitudo untuk ketiga formulasi tersedia per kasus di `D2_benchmark_offset.csv`. Nilai sekitar 0,11–0,16 nT masih **di atas** ambang Sq 0,1 nT protokol, sehingga D2 tidak mengklaim reproduksi IQD numerik berhasil atau mengganti baseline malam secara diam-diam. Konvensi waktu kini mendukung A, tetapi versi data penulis dan langkah ekspor/pemusatan Mendeley belum diketahui.

## Duplikasi meanField dan mode Y/Z

Semua 180 pasangan DAT PCA Y/Z yang sejenis diperiksa lewat struktur dan SHA-256. Tepat enam pasangan identik, seluruhnya **Februari**:

- `COI_Y_meanField_m02.dat` = `COI_Z_meanField_m02.dat` (SHA-256 `0711725279a00903e357cc37740470cf1cc6f43de1daade0730a23cd065bb873`).
- `COI_Y_meanField_m02_y_all.dat` = `COI_Z_meanField_m02_y_all.dat` (SHA-256 `ff2a177dc221cc9155b79c22df1c984b390f166dc484a01c354eae6941bdd220`).
- `COI_Y_mode1_m02.dat` = `COI_Z_mode1_m02.dat` (SHA-256 `4597a176d1b6cbdd4908e44c866a5dde101de8a35b2270a31cce5c56bb2bb059`).
- `COI_Y_mode1_m02_y_all.dat` = `COI_Z_mode1_m02_y_all.dat` (SHA-256 `de3975981e87c45aa871cc5600a078c9864d0933db270453fd747ee456754fc5`).
- `COI_Y_mode2_m02.dat` = `COI_Z_mode2_m02.dat` (SHA-256 `92114eee1c91650ee352ee7582e2b31cd62a3d7a85a615a2279f3d944983d6ca`).
- `COI_Y_mode2_m02_y_all.dat` = `COI_Z_mode2_m02_y_all.dat` (SHA-256 `3da2fb56e6a89a894ab0f61818859077d09f22cdc9fdb85bfa2c07bd4f6b933d`).

EOF1–EOF3, PC1–PC3, serta berkas serupa pada bulan lain mempunyai hash Y/Z berbeda. Jadi anomali meluas dari `meanField` ke `mode1` dan `mode2` Februari, tetapi pemeriksaan ini tidak menjalankan PCA atau membuktikan isi EOF/PC benar.

Pencocokan `COI_Y_meanField_m02.dat` terhadap rerata 24 jam WDC setelah satu offset konstan:

| Tahun | WDC Y: RMSE (nT) | WDC Z: RMSE (nT) |
|---:|---:|---:|
| 2008 | 1.6616 | 0.0586 |
| 2012 | 3.3103 | 0.0449 |
| 2016 | 3.5191 | 0.0768 |

Isi `meanField Y` lebih cocok dengan komponen WDC **Z**. Ini diskrepansi sumber yang nyata, bukan izin mengedit DAT asli. Usulan untuk tahap berikutnya ialah lapisan pembacaan terpisah yang memberi flag/karantina pada enam berkas Februari dengan provenance SHA-256; koreksi atau rekonstruksi Y tidak diaktifkan tanpa review dan versi protokol baru bila mengubah aturan benchmark.

## Keputusan D2 dan kesiapan G1

- **D2-TIME — CONFIRMED:** A sesuai seluruh 92.963/92.964/92.967 jam X/Y/Z berpasangan setelah pemotongan 0,1 nT; B/C jauh lebih buruk. Arsip sendiri tidak menyebut interval rinci, tetapi standar dan bukti empiris konsisten dengan menit 00–59 dan label artikel HH:30.
- **D2-DATA — UNRESOLVED:** X/Y/Z ekuivalen pada jendela 60 menit penuh, termasuk aturan ketersediaan 54/60 yang teramati. F menyisakan 22.577 mismatch kuantisasi kecil yang belum dijelaskan. Jam tidak lengkap dan sentinel ditandai; penyebab historis tidak disimpulkan.
- **D2-BENCHMARK — SOURCE_DISCREPANCY:** dokumentasi baseline malam dan berkas Sq terpusat 24 jam tidak sepenuhnya sejalan; enam duplikasi Y/Z Februari mencakup meanField dan mode. Evaluasi kondisi berhenti **S7 terpicu** untuk review sumber.
- **Keputusan akhir D2 — CONDITIONAL PASS.** Diagnostik waktu selesai, namun status data penuh dan benchmark bersyarat. **Rekomendasi G1: HOLD**, nilai D1-IQD provisional dan S7 bersama sebelum G1 dapat dinyatakan lolos. D3/D4, PCA penuh, DTW, DIFI, dan classifier tidak dijalankan.

## Reproduksibilitas

Jalankan `python -B phase2a/D2/d2_compute.py` lalu `python -B phase2a/D2/d2_report.py`. `D2_execution.log` mencatat setiap tahap. CSV bulanan, fokus, jendela tidak lengkap, dan anomali berisi angka serta path/hash sumber; JSON memuat parameter dan versi Python/NumPy. `D2_review.zip` hanya berisi kode, laporan, JSON, CSV, checksum, dan log; ZIP raw tidak disertakan.
