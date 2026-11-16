# D2b — Perbandingan meanField Mendeley dengan rata-rata harian WDC COI

**Hasil aturan D2b: 10953/10953 pasangan valid berlabel REVISION; 121/121 bulan tahun terdampak. G1: HOLD menurut baris R4.** Label REVISION di sini hanya keluaran ambang `|d| > 0,5 nT`; tidak membuktikan bahwa data WDC pernah direvisi secara historis.

## Aturan dan preflight

D2b mulai `2026-11-13T12:42:13.999153+00:00` dan selesai `2026-11-13T12:42:35.304272+00:00`. Cakupan ialah Januari serta Maret–Desember 2007–2017 untuk X/Y/Z; Februari tidak dibandingkan. Semua 3702 file dalam manifest G0, termasuk 42 ZIP Fase 1, serta 54 artefak G0/D1/D2/S7-A cocok SHA-256 sebelum dan sesudah D2b. Hash per input ada di `D2b_preflight.json` dan `D2b_meanfield_comparison.csv`.

Semua 132 anggota bulanan WDC memiliki timestamp berurutan HH:00, DOY kalender, header IAGA-2002/XYZF, dan CRC ZIP valid. Sentinel `88888.xx`/`99999.xx` diperlakukan sebagai missing. Hanya celah yang terkurung oleh dua jam valid di dalam bulan diinterpolasi linear; tidak ada ekstrapolasi batas bulan atau pengisian satu hari yang seluruh jamnya hilang. Aturan konservatif ini mencatat gap yang melintasi satu hari kosong sebagai unresolved.

Ketiga puluh tiga DAT tahunan `meanField` memiliki indeks hari 1–30/31 sesuai kalender dan kolom `y.2007`–`y.2017`. Setiap berkas mencetak paling banyak dua desimal, sehingga resolusi cetak per berkas yang didaftarkan sebelum perbandingan adalah **0,01 nT** dan batas MATCH = 0,025 nT. Aturan MATCH dan QUANT memang tumpang tindih secara logis pada 0,02 < |d| ≤ 0,025 nT. Kode mencatat semua predikat tanpa prioritas; **0** pasangan aktual ambigu. Rentang jumlah desimal per file dicatat di preflight JSON.

Berkas `_y_all` hanya diperiksa terhadap gabungan nilai tahunan, tidak dibandingkan ke WDC. Dari 33 berkas, 29 konsisten persis. Empat berkas X memiliki 30 posisi tidak cocok masing-masing:

| Bulan/komponen | Posisi tidak cocok | Posisi pertama | Maks. beda nilai (nT) |
|---|---:|---:|---:|
| 04:X | 30 | 31 | 35.34 |
| 06:X | 30 | 31 | 31.16 |
| 09:X | 30 | 31 | 23.50 |
| 11:X | 30 | 31 | 30.76 |

Inkonsistensi gabungan ini tidak dipakai untuk menggeser alignment per tahun dan tidak menyentuh keputusan D2b per hari. Penyebabnya tidak diperiksa lebih jauh sesuai K9.

## Hasil numerik

Selisih `d = mean_daily_WDC − meanField_Mendeley` dihitung langsung tanpa offset fit. Denominator utama D2b ialah pasangan hari–komponen valid, sedangkan target_total juga menampilkan yang tidak dapat dihitung.

| Metrik | Jumlah | Persen dari valid |
|---|---:|---:|
| Target hari kalender non-Februari | 3707 | — |
| Target pasangan hari–komponen | 11121 | — |
| Dapat dihitung | 10953 | 100,00% |
| MATCH | 0 | 0.00% |
| QUANT | 0 | 0.00% |
| SMALL_UNEXPLAINED | 0 | 0.00% |
| REVISION (label ambang) | 10953 | 100.00% |
| ALIGNMENT_FAIL | 0 | — |
| ALL_DAY_MISSING | 138 | — |
| UNRESOLVED_MISSING | 30 | — |

Seluruh 10.953 pasangan valid berlabel REVISION. Sebanyak 138 pasangan adalah hari kosong sepenuhnya, dan 30 pasangan menyisakan gap yang tidak boleh diisi; ketiganya sama antar komponen, yakni 46 dan 10 hari kalender. Sebanyak 585 jam komponen terinterpolasi pada 177 pasangan hari–komponen. Tidak ada `ALIGNMENT_FAIL` pada DAT tahunan.

| Komponen | Target hari | Valid | Median d (nT) | H-a |
|:---:|---:|---:|---:|---|
| X | 3707 | 3651 | +25000.000833 | NOT_SUPPORTED |
| Y | 3707 | 3651 | -1800.000000 | NOT_SUPPORTED |
| Z | 3707 | 3651 | +35999.999167 | NOT_SUPPORTED |

Median X/Y/Z berada dekat +25.000/−1.800/+36.000 nT, jauh di luar interval tanda kuantisasi H-a (±0,02–0,08 nT). **H-a NOT_SUPPORTED.** Nilai level besar ini konsisten dengan kemungkinan acuan level berbeda, tetapi D2b tidak memasang offset, tidak memulihkan versi WDC penulis, dan tidak menetapkan sebabnya. Karena itu persentase REVISION tidak boleh diterjemahkan sebagai bukti revisi historis luas.

Bulan terdampak didefinisikan oleh ≥1 REVISION pada X/Y/Z: **121/121 = 100.00%**. Daftar lengkap 121 bulan ada di `D2b_revision_months.csv` dan `D2b_summary.json`. Semua Januari serta Maret–Desember pada setiap tahun 2007–2017 masuk daftar; Februari memang di luar cakupan. Dari pasangan REVISION, 1803 juga berada pada Q1–Q5 GFZ; status IQD dan jam terinterpolasi per hari ada di CSV utama. Jika pengecualian R4 diterapkan ke G3, seluruh bulan non-Februari akan dikeluarkan sehingga penyebut bersih kosong; G2/G3 tidak dimulai pada G1 HOLD.

## Keputusan dan keterbatasan

Baris G1 yang terpenuhi hanya **R4: bulan terdampak REVISION >10%**, sehingga status **HOLD**. R1/R2/R3 tidak terpenuhi; R5 tidak diputuskan berdasarkan semantik `meanField` karena D2b tidak boleh melakukan investigasi lebih jauh, sedangkan alignment tahunan lulus. Potensi overlap MATCH/QUANT tidak berpengaruh pada data aktual (0 ambigu). K10 tidak otomatis dijalankan: syaratnya ialah pilot G2 non-Februari gagal, sedangkan pilot belum dijalankan dan G1 HOLD melarang memulainya.

R1 numerik persis tidak tercapai; R2 hanya didukung oleh hasil bentuk S7-A yang telah dilihat, tanpa uji baru; R3/R4 belum diuji. D1-IQD Februari 2016 tetap PROVISIONAL; F ditunda hanya untuk PCA XYZ dengan pemicu pembukaan kembali K6. Forensik benchmark ditutup setelah D2b sesuai K9. Residu yang belum terjelaskan dicatat sebagai keterbatasan, tanpa menyalahkan penulis asal atau mengubah 18 kontrol Sq yang gagal absolut.

Kode: `d2b_meanfield.py`; uji sintetis: `d2b_test.py` (overlap kelas, celah internal, hari kosong, tepi bulan). Data sintetis tidak digunakan dalam angka penelitian. Seluruh angka laporan diturunkan dari CSV/JSON hasil eksekusi D2b satu kali.
