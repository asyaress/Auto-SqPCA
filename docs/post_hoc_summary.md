Public reading copy: one local filesystem path was redacted. Original source SHA-256: `d3be94a6c2f1f28459ef7b34c3e2aa5c0bd9756e2d27d6690c7fe63d5865dff2`. This copy is not byte-identical to the original.

# AUDIT_ADD — audit tambahan Fase 3

Status: **EXPLORATORY_POST_HOC**. Audit deskriptif pasca-hasil; tidak mengubah metode, ambang, konfigurasi beku, atau hasil lama.

## Integritas dan sumber

Verifikasi ulang 27 input yang memiliki hash acuan cocok; satu path yang diminta tidak ada: `F3_E1_holdout_cases.csv.gz`. Seluruh modul `auto_sqpca/*.py`, protokol, amandemen, serta konfigurasi E1/E2 cocok dengan hash beku. Setiap cache bulanan/kurva yang dipakai diperiksa terhadap hash pada inventaris atau tabel kasus.

U2 dan U3 memakai `work/E1_holdout_cases.csv` sebagai sumber alternatif **yang terautentikasi**: SHA-256-nya sama dengan `F3_C1_result.json`, dan berkas hasil C1 tersebut tercakup dalam `F3B_checksums.sha256`. Ketiadaan path gzip tetap dicatat sebagai `UNRESOLVED`; tidak ada data yang direkonstruksi dari asumsi.

Percobaan awal U1 berhenti dengan pesan asli `FileNotFoundError: [Errno 2] No such file or directory: '<LOCAL_PATH>'`. Ini adalah salah path pada skrip audit. Pembacaan 2018 dikoreksi ke `phase3/raw/gfz/QD_days2018.txt` dan hash-nya diverifikasi terhadap `F3_GFZ2018_source.json`; tidak ada sumber beku yang diubah. Log percobaan dan eksekusi ulang disertakan.

Semua analisis U1–U5 memakai set *holdout*. Seed topeng E1 berasal dari `f3_e1.py`; bootstrap E2/E3 memakai seed dasar 20261114. Resampel klaster untuk CI U2/U3: 2.000, seed 20261115, unit stasiun–tahun–bulan. Lingkungan: Python 3.12.6, Windows-11-10.0.26200-SP0.

## U1 — sensitivitas batas iterasi

Sumber E1 holdout memuat 149 bulan dan 420 pasangan bulan–komponen yang memiliki target kurva tanpa topeng. U1 menggunakan empat topeng 10% dan lima replikasi pertama, sehingga ada 8.400 kasus.

`fill_em_cap(a, 500)` menghasilkan array, keep-mask, iterasi, dan perubahan akhir yang bit-identik dengan `gaps.fill_em` pada 20 kasus (10 mencapai cap, 10 berhenti lebih awal). Kasus yang berhenti sebelum 500 menggunakan hasil E1 terautentikasi karena cap 5000 mengikuti kondisi berhenti yang sama; kasus yang mencapai cap 500 dihitung ulang dan checkpoint iterasi 500 dibandingkan dengan E1. Pada E3, checkpoint cap-500 juga dicocokkan dengan kandidat dan kurva cache beku.

| Topeng 10% | Kasus | Cap 500 | Konvergen <5000 | Kandidat sama | Kurva berpasangan | Beda kurva median / p90 / maks (L2 relatif) | Galat E1 median 500 / 5000 | Galat E1 p90 500 / 5000 |
|---|---:|---:|---:|---:|---:|---|---|---|
| MCAR | 2100 | 4.0% | 99.0% | 99.4% | 2093 | 0.0000 / 0.0000 / 0.6416 | 0.0272 / 0.0272 | 0.0931 / 0.0933 |
| BLOCK6 | 2100 | 89.5% | 60.8% | 87.8% | 2069 | 0.0014 / 0.1767 / 48.5767 | 0.0634 / 0.0718 | 0.2745 / 0.3766 |
| BLOCK24 | 2100 | 92.8% | 18.0% | 79.5% | 2055 | 0.0424 / 0.2666 / 24.5013 | 0.0749 / 0.1027 | 0.2840 / 0.4192 |
| BLOCK72 | 2100 | 62.9% | 52.3% | 90.6% | 2073 | 0.0022 / 0.1346 / 17.6440 | 0.0619 / 0.0693 | 0.2196 / 0.2968 |

E3 nyata berstatus OK dan M-EM mencapai 500 iterasi: **57 kasus** (kasus E3 non-OK tidak termasuk). Sebanyak **36** masih mencapai cap 5.000. Kandidat berubah: **9**; keputusan abstain berubah: **6** (3 abstain→diterima, 3 diterima→abstain). Beda kurva median/maks pada kurva berpasangan: **0.0245 / 0.7399**. Perubahan r AUTO–DIFI median pada kasus diterima di kedua cap: **-0.000004** (n=37).

Cap 5.000 tidak berarti seluruh kasus telah konvergen; maksimum beda L2 relatif juga harus dibaca bersama norma kurva cap-500 yang menjadi penyebutnya. Rincian tiap kasus ada di tabel U1.

## U2 — rentang operasi 5–10% hilang

Rasio memakai galat relatif L2 E1; kasus tanpa keluaran diberi galat tak hingga. CI 95% menggunakan resampel klaster bulan–stasiun. Rasio di bawah 1 berarti galat M-EM lebih kecil untuk ringkasan tersebut; median dan p90 dapat bergerak berbeda.

| Topeng | M-EM/pembanding | Rasio median (CI 95%) | Rasio p90 (CI 95%) | Tanpa keluaran M-EM / pembanding |
|---|---|---|---|---|
| BLOCK24 10% | M-EM/M-INT | 0.576 (0.555–0.598) | 1.391 (1.232–1.530) | 1.5% / 1.0% |
| BLOCK24 10% | M-EM/M-EXC | 1.202 (1.167–1.242) | 1.435 (1.311–1.568) | 1.5% / 1.2% |
| BLOCK6 10% | M-EM/M-INT | 0.785 (0.751–0.821) | 1.694 (1.575–1.850) | 1.3% / 1.2% |
| BLOCK6 10% | M-EM/M-EXC | 0.715 (0.684–0.745) | 0.932 (0.830–1.045) | 1.3% / 2.1% |
| BLOCK72 10% | M-EM/M-INT | 0.817 (0.789–0.845) | 1.252 (1.142–1.359) | 1.1% / 1.1% |
| BLOCK72 10% | M-EM/M-EXC | 1.039 (1.011–1.062) | 1.195 (1.108–1.270) | 1.1% / 1.3% |
| DAY 10% | M-EM/M-INT | 1.000 (1.000–1.000) | 1.000 (1.000–1.000) | 0.9% / 0.9% |
| DAY 10% | M-EM/M-EXC | 1.000 (1.000–1.000) | 1.000 (1.000–1.000) | 0.9% / 0.9% |
| MCAR 5% | M-EM/M-INT | 1.240 (1.206–1.276) | 1.577 (1.463–1.707) | 0.5% / 0.4% |
| MCAR 5% | M-EM/M-EXC | 0.426 (0.412–0.442) | 0.437 (0.398–0.485) | 0.5% / 0.9% |
| MCAR 10% | M-EM/M-INT | 1.102 (1.064–1.142) | 1.502 (1.377–1.665) | 0.5% / 0.5% |
| MCAR 10% | M-EM/M-EXC | 0.258 (0.248–0.268) | 0.257 (0.226–0.295) | 0.5% / 2.5% |

## U3 — pipeline beku lengkap

Untuk kedua metode, matriks dengan hari berisi <6 jam observasi dihentikan sebelum imputasi (`DAY_LT6`); untuk matriks lain dijalankan pengisian, PCA/seleksi, bootstrap 200 kali, A1/A2/A3, dengan A4 tidak aktif. Seed bootstrap E3 per stasiun–bulan–komponen sama untuk dua metode. Galat dihitung terhadap kurva bulan tanpa topeng menurut definisi E1. Alasan abstain dalam CSV dapat tumpang tindih.

| Topeng | Metode | Diterima | Galat diterima median / p90 | Pasangan diterima keduanya | Median Δ galat M-EM − M-INT (CI 95%) |
|---|---|---:|---|---:|---|
| BLOCK24 10% | M-EM | 3.6% | 0.0724 / 0.1313 | 66 | -0.0489 (-0.0595–-0.0326) |
| BLOCK24 10% | M-INT | 3.5% | 0.1158 / 0.1489 | 66 | -0.0489 (-0.0595–-0.0326) |
| BLOCK6 10% | M-EM | 13.7% | 0.0502 / 0.1308 | 272 | -0.0224 (-0.0269–-0.0155) |
| BLOCK6 10% | M-INT | 13.6% | 0.0731 / 0.1187 | 272 | -0.0224 (-0.0269–-0.0155) |
| BLOCK72 10% | M-EM | 0.0% | NA / NA | 0 | NA (NA–NA) |
| BLOCK72 10% | M-INT | 0.0% | NA / NA | 0 | NA (NA–NA) |
| DAY 10% | M-EM | 0.0% | NA / NA | 0 | NA (NA–NA) |
| DAY 10% | M-INT | 0.0% | NA / NA | 0 | NA (NA–NA) |
| MCAR 5% | M-EM | 85.0% | 0.0156 / 0.0357 | 1752 | 0.0026 (0.0023–0.0030) |
| MCAR 5% | M-INT | 84.6% | 0.0128 / 0.0255 | 1752 | 0.0026 (0.0023–0.0030) |
| MCAR 10% | M-EM | 41.2% | 0.0225 / 0.0549 | 839 | 0.0009 (0.0001–0.0016) |
| MCAR 10% | M-INT | 40.8% | 0.0217 / 0.0385 | 839 | 0.0009 (0.0001–0.0016) |

Alasan abstain berikut adalah jumlah kasus dan dapat tumpang tindih:

| Topeng | Metode | A1 | A2 | A3 | Hari <6 jam |
|---|---|---:|---:|---:|---:|
| BLOCK24 10% | M-EM | 1 | 45 | 1513 | 1920 |
| BLOCK24 10% | M-INT | 10 | 44 | 1513 | 1920 |
| BLOCK6 10% | M-EM | 30 | 383 | 1755 | 12 |
| BLOCK6 10% | M-INT | 40 | 327 | 1755 | 12 |
| BLOCK72 10% | M-EM | 0 | 0 | 1400 | 2100 |
| BLOCK72 10% | M-INT | 0 | 0 | 1400 | 2100 |
| DAY 10% | M-EM | 0 | 0 | 205 | 2100 |
| DAY 10% | M-INT | 0 | 0 | 205 | 2100 |
| MCAR 5% | M-EM | 6 | 311 | 0 | 0 |
| MCAR 5% | M-INT | 10 | 321 | 0 | 0 |
| MCAR 10% | M-EM | 10 | 308 | 1073 | 0 |
| MCAR 10% | M-INT | 13 | 328 | 1073 | 0 |

## U4 — RMSE terhadap DIFI-8

Pada 24 kombinasi stasiun × komponen, median RMSE di antara kasus diterima berkisar **1.47–12.18 nT**. RMSE dihitung dari 24 nilai jam kurva AUTO dan DIFI-8, lalu dibagi amplitudo puncak-ke-puncak DIFI untuk versi ternormalisasi. Korelasi AUTO–IQD adalah pembanding nonindependen karena IQD dipakai dalam seleksi.

| Stasiun | Komp. | Diterima / total | Abstain | RMSE median [Q1, Q3] nT | RMSE ternormalisasi median | r AUTO–IQD < 0 |
|---|---|---:|---:|---|---:|---:|
| COI | X | 9/48 | 81.2% | 3.84 [3.57, 5.23] | 0.198 | 0 |
| COI | Y | 43/48 | 10.4% | 7.01 [5.21, 8.93] | 0.172 | 0 |
| COI | Z | 46/48 | 4.2% | 3.75 [3.25, 4.41] | 0.159 | 0 |
| GUA | X | 47/60 | 21.7% | 4.31 [3.43, 5.36] | 0.093 | 0 |
| GUA | Y | 47/60 | 21.7% | 5.31 [3.77, 6.58] | 0.179 | 0 |
| GUA | Z | 44/60 | 26.7% | 1.47 [1.05, 1.87] | 0.090 | 0 |
| HUA | X | 58/60 | 3.3% | 8.69 [6.89, 10.51] | 0.082 | 0 |
| HUA | Y | 38/60 | 36.7% | 5.30 [4.41, 6.24] | 0.274 | 0 |
| HUA | Z | 44/60 | 26.7% | 1.62 [1.23, 1.87] | 0.120 | 0 |
| KDU | X | 36/60 | 40.0% | 3.56 [2.88, 4.25] | 0.114 | 0 |
| KDU | Y | 59/60 | 1.7% | 4.72 [3.58, 6.09] | 0.146 | 0 |
| KDU | Z | 59/60 | 1.7% | 1.58 [1.18, 2.13] | 0.088 | 0 |
| MBO | X | 48/55 | 12.7% | 4.62 [3.85, 5.26] | 0.080 | 0 |
| MBO | Y | 47/55 | 14.5% | 4.44 [3.54, 5.93] | 0.163 | 0 |
| MBO | Z | 48/55 | 12.7% | 3.30 [2.61, 3.92] | 0.074 | 0 |
| PLR | X | 3/10 | 70.0% | 5.12 [4.70, 6.60] | 0.136 | 0 |
| PLR | Y | 4/10 | 60.0% | 4.08 [3.53, 4.50] | 0.222 | 0 |
| PLR | Z | 5/10 | 50.0% | 12.18 [10.70, 12.42] | 0.618 | 0 |
| TTB | X | 43/51 | 15.7% | 9.53 [7.13, 11.12] | 0.168 | 0 |
| TTB | Y | 42/51 | 17.6% | 6.77 [5.16, 8.58] | 0.174 | 0 |
| TTB | Z | 36/51 | 29.4% | 3.89 [3.05, 4.87] | 0.590 | 0 |
| TUN | X | 8/12 | 33.3% | 5.75 [4.37, 6.31] | 0.116 | 0 |
| TUN | Y | 7/12 | 41.7% | 5.26 [4.81, 5.97] | 0.404 | 0 |
| TUN | Z | 9/12 | 25.0% | 2.63 [2.17, 2.97] | 0.126 | 0 |

## U5 — cakupan band pada E2 semi-sintetis

Verifikasi ulang 20 kasus cocok untuk kandidat dan stabilitas; seluruh kasus holdout tanpa topeng yang diterima dihitung ulang dengan seed bootstrap beku. Target per jam adalah `alpha × Sq_target` (DIFI-8). **Band 5–95% bersifat pointwise, bersyarat pada matriks terisi dan acuan IQD; ini bukan uji interval kepercayaan nominal.**

| Komp. | α | Kasus | Rata-rata fraksi jam tercakup | Kasus ≥22/24 jam | Median lebar band (nT) |
|---|---:|---:|---:|---:|---:|
| X | 0.5 | 118 | 87.7% | 66.9% | 4.08 |
| X | 1.0 | 205 | 95.3% | 86.3% | 5.00 |
| X | 2.0 | 283 | 98.4% | 92.9% | 6.31 |
| Y | 0.5 | 155 | 87.6% | 66.5% | 2.26 |
| Y | 1.0 | 281 | 98.3% | 94.3% | 2.63 |
| Y | 2.0 | 311 | 99.9% | 100.0% | 3.12 |
| Z | 0.5 | 167 | 89.3% | 71.3% | 1.39 |
| Z | 1.0 | 260 | 96.1% | 90.8% | 1.65 |
| Z | 2.0 | 303 | 98.6% | 96.7% | 2.02 |

## U6 — fakta kode dan kalender

Cache Februari kabisat Fase 3 berukuran 24 × 29 × 3; 29 Februari **ikut** dalam matriks E1/E2/E3. Rincian per stasiun, jam tepi deret UTC, dan irisan hari GFZ UTC/lokal ada di `U6_facts.md`. Fakta ini berbeda dari kalimat naskah MethodsX yang menyatakan 29 Februari dibuang. Audit ini tidak mengubah naskah atau preprocessing.

## UNRESOLVED dan batas interpretasi

- `F3_E1_holdout_cases.csv.gz`: **UNRESOLVED_MISSING**. U2 dan U3 menggunakan `work/E1_holdout_cases.csv` yang hash-nya terverifikasi sebagai sumber alternatif; path gzip yang diminta tetap belum tersedia.
- Tidak ada baris `ERROR` pada U3. Status `PRECHECK_DAY_LT6` adalah abstain yang ditetapkan oleh aturan kelengkapan, bukan error komputasi.

Semua hasil U1–U5 bersifat deskriptif pasca-hasil. Tidak ada ambang atau klaim keberhasilan baru yang ditetapkan dari audit ini.
