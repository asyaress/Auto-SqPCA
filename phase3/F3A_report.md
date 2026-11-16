# Fase 3 Tugas A — persiapan dan E1

**Metode terpilih: M-EM. Status C1 numerik: BERHASIL; adopsi metode menunggu review penyimpangan.** Ini evaluasi E1 dengan kebenaran internal berupa keluaran pipeline pada bulan tanpa topeng. E2/SSB dan E3 belum dijalankan.

## Integritas dan data

Protokol F3-v1 SHA-256 `617c96d0cbda26fa3f6333ea1638030a35db1836fd99ba35f2a3bb18ea091327`; konfigurasi E1 dibekukan dengan SHA-256 `a2a2cd09ccf4c16c87a9033d792de80762d253c2db16455f81cc4329ad26981d` **sebelum** simulasi holdout. Pemeriksaan akhir menemukan 161 artefak Fase 1–2 cocok hash, 42 ZIP menit beku dan 3.702 entri manifest G0 cocok pada preflight, serta 12 ZIP per jam baru cocok hash setelah dipakai. Akuisisi KDU/GUA 2014–2018 dan PLR/TUN 2017 seluruhnya HTTP 200, tanpa fallback menit. COI menggunakan snapshot G0. Data mentah disimpan di `phase3/raw/` dan tidak ada dalam ZIP review.

Holdout terputus setelah 37/149 bulan; berkas parsial disimpan dengan hash dan pemulihan hanya menghitung 112 bulan tersisa. Skrip, batas pemulihan, dan hash keluaran ada di `F3_E1_recovery.json`; rincian ada di `F3A_changes.md`.

**Koreksi input pasca-evaluasi:** GFZ 2018 semula hilang, sehingga evaluasi awal tidak memiliki kasus untuk 20 bulan KDU/GUA 2018. Hasil awal disimpan di `phase3/work/E1_pre_GFZ2018/`; GFZ 2018 resmi kemudian diperoleh dan hanya bulan terdampak dihitung. 476280 baris awal tetap identik. Ini penyimpangan urutan holdout yang material dan dicatat terbuka dalam `F3_E1_2018_correction.json`; metode terpilih dan aturan analisis tidak berubah.

Inventaris mempunyai 276 bulan stasiun; 232 memenuhi E1 (≥99% jam XYZ valid, tanpa celah >2 jam) dan 253 memenuhi ambang E2 (≥95%). Pergeseran LT dihitung dari metadata: COI −1, KDU +9, GUA +10, PLR +7, TUN +7 jam. TND 2017 dipakai hanya sebagai sumber topeng dengan aturan 60 menit XYZ valid.

## Uji sintetis dan deviasi

T1–T8 lulus pada uji ulang; T1 6.12e-08 nT setelah 105 iterasi, T3 stabilitas 1.0 dan w=0.0. T6 abstain pada 200/200 tanpa sinyal dan menerima 200/200 sinyal kuat. **M-EM menggunakan penghalusan internal 10⁻⁸ nT**, lebih ketat daripada batas 10⁻⁴ di protokol agar T1 terpenuhi. Ini deviasi implementasi yang harus direview sebelum mengadopsi metode sebagai spesifikasi final; log awal dan alasan ada di `F3A_changes.md`.

## E1 pengembangan dan holdout

Set pengembangan: 213 komponen-bulan memiliki keluaran lengkap untuk target internal; 12 tidak memiliki target terdefinisi. Skor pemilihan (rerata median galat per jenis topeng × komponen, p≤30%): M-INT=0.093431, M-EXC=0.16361, M-EM=0.083143. Metode **M-EM** dipilih sebelum holdout. Set holdout setelah koreksi GFZ 2018: 420 komponen-bulan bertarget, 27 tanpa target. Rincian kasus dan hash tersedia di `phase3/work/`; CSV ringkasan ada dalam paket review.

Batas aman p* memakai median galat ≤ε dan persentil 90 ≤2ε; ε utama 0,05, sensitivitas 0,03/0,10 ada di `F3_E1_pstar.csv`.

| Topeng | p* (ε=0,05) |
|---|---:|
| MCAR | 0.1 |
| BLOCK6 | UNDEFINED |
| BLOCK24 | UNDEFINED |
| BLOCK72 | UNDEFINED |
| DAY | UNDEFINED |

Uji keunggulan metode terpilih terhadap M-INT memakai rasio median galat dengan CI 95% bootstrap 2.000 resampling bulan. Jenis topeng dihitung berhasil bila batas atas CI<1 pada sedikitnya dua dari p=20,30,40%; C1 butuh sedikitnya dua dari tiga jenis. M-EM mencapai batas 500 iterasi pada 116777 kasus metode holdout; perubahan akhir per kasus tercatat di CSV rinci.

| Topeng | p | Rasio | CI 95% | Keunggulan |
|---|---:|---:|---:|:---:|
| MCAR | 0.2 | 0.9237519256800074 | [0.8716177701655816, 0.9773313527937713] | True |
| MCAR | 0.3 | 0.871945796242123 | [0.8196105228702814, 0.9066061547236628] | True |
| MCAR | 0.4 | 0.8956223352050445 | [0.8446196569126457, 0.93667355290748] | True |
| BLOCK24 | 0.2 | 0.5111410630980905 | [0.49592524814866623, 0.5287100496222108] | True |
| BLOCK24 | 0.3 | 0.4972228102008232 | [0.4818037065343492, 0.5203371777528043] | True |
| BLOCK24 | 0.4 | 0.49873448656229663 | [0.4728290423530608, 0.5216960492165086] | True |
| DAY | 0.2 | 0.9999999999999999 | [0.9999999999999967, 1.0000000000000069] | False |
| DAY | 0.3 | 0.9999999999999972 | [0.9999999999999967, 1.0000000000000087] | False |
| DAY | 0.4 | 1.0000000000000002 | [0.9999999999999964, 1.0000000000000024] | False |

Jenis yang memenuhi aturan: BLOCK24, MCAR. Topeng TND mempunyai 108 baris ringkasan metode–stasiun–bulan:

| Metode | Kasus TND | Tanpa keluaran | Median galat antar sel yang berhingga |
|---|---:|---:|---:|
| M-INT | 420 | 51 (12.1%) | 0.5915 |
| M-EXC | 420 | 420 (100.0%) | tidak terdefinisi |
| M-EM | 420 | 35 (8.3%) | 0.4505 |

Grafik TND ada pada `F3A_figure2_TND.png`, dengan galat dan fraksi tanpa keluaran. Gambar 1 memuat kurva galat dan batas ε. Tidak ada klaim E2/E3 atau judul Fase 3 yang diputuskan pada Tugas A.

## Reproduksi dan batas

Paket `auto_sqpca/` menyediakan loader, LT, tiga metode celah, inti PCA V1 beku, tujuh kandidat, surrogate, bootstrap, abstain, SSB, dan metrik. Titik masuk CLI awal ialah `python -m phase3.auto_sqpca.cli f3a` setelah memasang `phase3/requirements.txt`; skrip menolak menjalankan ulang holdout jika CSV-nya sudah ada. **CLI awal belum memasukkan koreksi GFZ 2018**, sehingga untuk mereproduksi hasil akhir perlu menjalankan skrip `f3_gfz2018.py` dan `f3_e1_2018_correction.py`, lalu evaluator serta finalizer seperti dicatat di log. Ini keterbatasan reproduksi satu perintah akibat kode E1 beku tidak diubah setelah holdout. Versi Python/NumPy inti serta lingkungan gambar tercatat di `F3A_environment.json`. Kasus tanpa keluaran diberi galat ∞ agar batas aman dan perbandingan tidak tampak lebih baik akibat penghapusan kasus gagal. Kebenaran E1 adalah keluaran lengkap bulan yang sama, sehingga E1 mengukur ketahanan terhadap topeng, bukan akurasi Sq alami.
