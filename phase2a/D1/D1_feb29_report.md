# D1 — Diagnosis 29 Februari pada PCA dan Sq IQD

**D1-PCA: CONFIRMED. D1-IQD: PROVISIONAL.** G1 belum dinilai karena D2 belum dijalankan.

## Acuan dan parameter yang dikunci untuk D1

Protokol `G0-registration-1` (DOCX SHA-256 tercatat di `D1_validation.json`) membatasi D1 pada U1/U2. Artikel data asli menyatakan semua matriks PCA Februari 24×28, Sq adalah rata-rata lima IQD GFZ, dan baseline malam per hari memakai 00:30, 01:30, 02:30, 03:30, 23:30 UTC. Artikel mencetak `02:03`; Tabel 2 memetakan indeks 3 ke 02:30, sehingga D1 memakai indeks jam 0,1,2,3,23. [Artikel data Morozova dkk. 2021](https://arxiv.org/pdf/2103.13899), hlm. 11–13.

Deret WDC berstempel HH:00 dipasangkan sementara dengan jam bernomor 1–24 pada Mendeley. Makna HH:00 terhadap HH:30 baru diuji di D2. Tidak ada interpolasi untuk Sq; semua jam pada IQD terpilih harus valid. Baseline malam dikurangi **pada setiap hari sebelum** lima kurva dirata-ratakan. Semua selisih dan amplitudo memakai nT berdasarkan artikel sumber.

## A. Struktur Mendeley dan kalender

| Komponen | meanField per tahun | EOF1 per tahun | meanField gabungan | EOF1 gabungan | VF1 | Sq Februari |
|---|---:|---:|---:|---:|---:|---:|
| X | 28×12 | 28×12 | 308×2 | 341×2 | 12×2 | 24×37 |
| Y | 28×12 | 28×12 | 308×2 | 341×2 | 12×2 | 24×37 |
| Z | 28×12 | 28×12 | 308×2 | 341×2 | 12×2 | 24×37 |

Per tahun, indeks `day` adalah tepat 1–28 untuk ketiga komponen dan semua kolom 2007–2017. `meanField_m02_y_all` mempunyai indeks 1–308 dan isinya **identik secara teks** dengan sebelas blok tahun × 28 hari dalam urutan tahun lalu hari. `EOF1_y_all_m02` memiliki 341 indeks, tetapi hanya 1–308 numerik; 309–341 adalah 33 `NA` di ujung. Nilai EOF gabungan berasal dari PCA gabungan dan bukan salinan EOF per tahun. `VF1_m02.dat` tidak mempunyai header: 11 baris `y.YYYY` serta `y.all`. Sq Februari mempunyai indeks jam `h=1–24`, kolom `Sq.y.2007` sampai `Sq.y.2017` dan kolom SD/S.

WDC Februari 2008, 2012, dan 2016 masing-masing mempunyai 696 timestamp unik HH:00 dan **24 jam pada 29 Februari** untuk X/Y/Z. IQD GFZ Q1–Q5: 2008 = 24,25,22,26,9; 2012 = 17,23,12,2,16; 2016 = 22,28,27,21,29. Jadi 29 Februari hanya berada dalam lima IQD pada 2016. Seluruh jam pada enam kandidat hari tenang 2016 tersedia tanpa sentinel.

### Hari mana yang tidak dipakai PCA?

Untuk setiap kemungkinan penghapusan satu hari dari 1–29, rerata 24 jam WDC X/Z dicocokkan ke `meanField` Mendeley dengan satu offset konstan yang diperkirakan dari median selisih. Hari WDC yang tak lengkap tidak ikut skor; Februari 2016 memiliki tiga nilai XYZ hilang pada hari 4. Offset hanya membantu identifikasi indeks kalender, bukan keputusan centering D3.

| Tahun | Komponen | Hari dibuang terbaik: RMSE | Pesaing terbaik berikutnya: RMSE | Hari valid |
|---:|:---:|---:|---:|---:|
| 2008 | X | 29: 0.0620 nT | 28: 1.0805 nT | 28 |
| 2008 | Z | 29: 0.0586 nT | 28: 0.1107 nT | 28 |
| 2012 | X | 29: 0.0595 nT | 28: 0.5498 nT | 28 |
| 2012 | Z | 29: 0.0449 nT | 28: 0.4797 nT | 28 |
| 2016 | X | 29: 0.0512 nT | 28: 0.1934 nT | 27 |
| 2016 | Z | 29: 0.0768 nT | 28: 0.1594 nT | 27 |

Berkas `COI_Y_meanField_m02.dat` dan `COI_Z_meanField_m02.dat` memiliki SHA-256 identik. Karena anomali sumber itu, Y **tidak** dipakai sebagai suara independen untuk pemetaan hari. X dan Z masing-masing memilih hari 29 pada ketiga tahun, dengan galat terendah <0,1 nT dan pesaing yang lebih buruk. Indeks serta blok gabungan mendukung pemakaian tanggal 1–28, tanpa penggantian hari lain.

### SVD terbatas: Februari 2008 X

| Centering diagnostik | 28 hari: VF1 / abs(r EOF1) | 29 hari: VF1 / abs(r EOF1) |
|---|---:|---:|
| V0 | 1.000000 / 0.380043 | 1.000000 / 0.380038 |
| V1 | 0.462012 / 0.999933 | 0.460958 / 0.998783 |
| V2 | 0.445789 / 0.513179 | 0.434698 / 0.535772 |
| V3 | 0.441619 / 0.897644 | 0.460440 / 0.873944 |

Benchmark VF1 X 2008 = 0.462985. SVD hanya menguji panjang kalender pada X Februari 2008, tanpa interpolasi karena seluruh nilainya valid. Perbandingan EOF memakai korelasi absolut karena tanda SVD bebas dan 29 hari dibandingkan pada 28 posisi pertama. VF/EOF mendukung 28 hari pada V1, tetapi tidak dipakai untuk memilih centering final; V0–V3 tetap urusan D3.

## B. Tiga kandidat Sq IQD Februari 2016

1. `official_Q1_Q5`: 22,28,27,21,29.
2. `replace_29_with_Q6`: 22,28,27,21,10.
3. `omit_29_no_replacement`: 22,28,27,21.

Setiap kurva dihitung dari data WDC hourly setelah rerata lima jam malam **per hari** dikurangi. Kolom RMSE dan maksimum adalah selisih absolut terhadap `Sq.y.2016` Mendeley. RMSE bentuk menghilangkan **hanya offset aditif** dari masing-masing kurva untuk diagnosis; itu bukan perubahan baseline metode. Amplitudo ialah maksimum–minimum 24 jam.

| Komp. | Kandidat | r | RMSE (nT) | Maks. (nT) | RMSE bentuk (nT) | Amplitudo (nT) | Δ amplitudo vs acuan (nT) |
|:---:|---|---:|---:|---:|---:|---:|---:|
| X | `official_Q1_Q5` | 0.999135 | 1.3475 | 1.6287 | 0.1306 | 12.380 | -0.020 |
| X | `replace_29_with_Q6` | 0.743276 | 2.8552 | 6.2887 | 2.4672 | 12.380 | -0.020 |
| X | `omit_29_no_replacement` | 0.808604 | 2.2888 | 4.8267 | 2.0900 | 13.225 | +0.825 |
| Y | `official_Q1_Q5` | 0.999953 | 5.2288 | 5.4743 | 0.1078 | 39.940 | +0.140 |
| Y | `replace_29_with_Q6` | 0.997334 | 5.0303 | 6.8463 | 1.1636 | 36.120 | -3.680 |
| Y | `omit_29_no_replacement` | 0.997938 | 4.3821 | 5.8183 | 0.7804 | 38.625 | -1.175 |
| Z | `official_Q1_Q5` | 0.999837 | 3.4724 | 3.7670 | 0.1424 | 25.860 | -0.140 |
| Z | `replace_29_with_Q6` | 0.993680 | 4.3294 | 6.5270 | 0.9837 | 26.600 | +0.600 |
| Z | `omit_29_no_replacement` | 0.997442 | 3.6071 | 5.3700 | 0.6323 | 27.000 | +1.000 |

Pada X/Y/Z, kandidat resmi mempunyai korelasi tertinggi dan RMSE bentuk terkecil. RMSE absolut **tidak** selalu memilihnya karena offset benchmark: semua kolom Sq Mendeley yang diperiksa mempunyai mean 24 jam mendekati nol, sedangkan baseline malam per hari membuat mean **lima jam malam** kurva kandidat nol. Sebagai kontrol, IQD resmi 2008/2012 juga memperlihatkan offset tetapi kesesuaian bentuk tinggi; metriknya ada di `D1_validation.json` dan `D1_evidence.csv`. Ketidaksesuaian level ini menunjukkan langkah pemusatan tambahan atau perbedaan ekspor/metode yang belum dijelaskan oleh teks artikel. D1 tidak mengubah baseline atau menyesuaikan offset untuk metrik absolut.

## Keputusan terpisah dan batas bukti

**D1-PCA — CONFIRMED:** tanggal 1–28 dipakai dalam matriks PCA Februari 2008/2012/2016; 29 Februari dikeluarkan. Dasarnya indeks per tahun, 308 posisi gabungan, dan pencocokan urutan harian X/Z terhadap WDC untuk semua kemungkinan satu hari dibuang. Y `meanField` duplikat Z adalah anomali berkas yang harus dibawa ke D3.

**D1-IQD — PROVISIONAL:** referensi Sq IQD Februari 2016 paling konsisten secara bentuk dengan lima IQD resmi, **termasuk 29 Februari**; penggantian dengan Q6 atau penghapusan tanpa penggantian lebih buruk pada X/Y/Z. Konvensi HH:00 WDC terhadap HH:30 artikel menunggu D2; offset absolut Mendeley juga belum terjelaskan. Karena itu belum ada klaim reproduksi numerik penuh atau atribusi seluruh selisih kepada hari kabisat.

**G1 belum PASS:** G1 mensyaratkan D1 dan D2. D2 tidak dijalankan di sini. Anomali meanField Y/Z dan mean Sq yang bertentangan dengan ekspektasi baseline malam ditandai sebagai potensi kondisi S7 dan memerlukan investigasi sebelum gate berikutnya; protokol tidak diubah. SVD V0–V3 dan RMSE bentuk adalah diagnostik tambahan, bukan pemilihan preprocessing atau toleransi baru.

## Jejak audit

`D1_validation.json` mencatat SHA-256 25 berkas input yang dipakai, parameter, seluruh 29 alternatif penghapusan/tahun/komponen, metrik kandidat, dan versi Python/NumPy. Semua 3,659 berkas raw cocok dengan SHA-256 manifest G0 **sebelum dan sesudah** eksekusi; SHA-256 laporan, validasi, dan manifest G0 juga tidak berubah. `D1_evidence.csv` berisi 320 baris bukti, termasuk input hash per baris. `D1_review.zip` hanya memuat laporan, kode, tabel, JSON, checksum, dan log kecil; tidak berisi data mentah.
