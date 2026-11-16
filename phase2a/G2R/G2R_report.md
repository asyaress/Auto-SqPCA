# G2-R — pilot implementasi ulang PCA, jalur K10

**Hasil: varian V1; holdout S-DEVIATE.** Ini adalah implementasi ulang independen; kesesuaian dengan keluaran publikasi tidak tercapai dalam toleransi yang didaftarkan. G1 registration-2 dan registration-3 tetap **HOLD**. Tidak ada klaim replikasi berhasil.

## Urutan dan integritas

Protokol G2R-v1 (`APPROVED` menurut berkas peneliti), SHA-256 `f38f407fbcad3d14309378b6f2e133b0be38b077fed930970fb064614d6571fd`. Enam uji inti PCA dan dua uji K11 lulus (`G2R_unit_tests.log`: 8 passed). Manifest G0: 3,702 hash cocok; 119 berkas artefak beku dan WDC format yang tercatat sebelum eksekusi cocok hash hingga akhir. Hash konfigurasi beku `25676d831262eef44857d6bd9b14f4aba72909ec4968760d53406f906976a320` dibuat sebelum pembacaan nilai holdout; hasil holdout menunjuk hash yang sama. Kode yang dibekukan juga cocok hash setelah holdout.

## Pengembangan dan pemilihan

Target 9 matriks: **6 eligible, 1 NOT_ELIGIBLE, 2 UNRESOLVED_MISSING**. Yang `NOT_ELIGIBLE` ialah gabungan Juni X karena kebijakan S7-C; gabungan Juni Y/Z tidak dapat dihitung karena masing-masing 14 jam batas bulan kosong. Tidak ada target pengganti. Tidak ada varian yang memenuhi syarat 9/9. Median galat Frobenius di enam matriks yang dapat dihitung: V0-A 2909.69806, V1 0.01511, V2 0.97808, V3 0.50860. Aturan 6.4 memilih **V1**, berlabel `DEVIATION_STRUCTURAL`.

Uji `meanField` kebal offset pada enam matriks tahunan memberi s_daily 0.05236–0.06458 nT dan s_night 1.92993–6.80685 nT; pola mendukung centering rata-rata hari, tetapi uji ini hanya pemutus seri. Norma PC Mendeley bukan satu (lihat `G2R_D4_scale.json`); RMSE EOF dinyatakan `NOT_APPLICABLE`. Pada mode1/2, maksimum |PC × EOF − mode| = 7.11e-13 nT. Mode3 diturunkan dari PC3 × EOF3 karena DAT mode3 tidak ada; galat Frobenius jumlah mode1–3 adalah metrik utama.

## Holdout sekali, sesudah pembekuan

Penyebut: **target_total=9, not_eligible=0, suspect=0, eligible=9, pass=3, fail=6**. Hanya 3/9 memenuhi galat Frobenius ≤1%; PC1 Y/Z lolos di semua matriks holdout yang eligible. Label menurut aturan bagian 7 ialah **S-DEVIATE**.

| Matriks | Frobenius relatif | VF lolos | PC1 lolos | Seluruh metrik |
|---|---:|:---:|:---:|:---:|
| 2009-01 X | 0.02185 | True | True | False |
| 2009-01 Y | 0.03752 | True | True | False |
| 2009-01 Z | 0.05257 | False | True | False |
| 2015-03 X | 0.00856 | True | True | True |
| 2015-03 Y | 0.00819 | True | True | True |
| 2015-03 Z | 0.01047 | True | True | False |
| combined-10 X | 0.01145 | True | True | False |
| combined-10 Y | 0.00840 | True | True | True |
| combined-10 Z | 0.01010 | True | True | False |

## Interpolasi, deviasi, dan K11

Interpolasi dihitung di dalam setiap bulan sebelum matriks. Berkas `G2R_interpolated_hours_by_day.csv` mencatat jumlah jam interpolasi dan bendera >12 per hari; terdapat 12 baris bendera (termasuk pengulangan komponen bila terjadi). Celah batas bulan yang masih kosong tidak diekstrapolasi. Jam HH:00 IAGA diperlakukan sebagai rerata jam dan ditempatkan pada HH:30 UTC; komponen X/Y/Z absolut nT dipakai tanpa konstanta penyesuaian.

Loader K11 menerima ZIP IAGA-2002 XYZF bagi PLR, TUN, KDU, GUA pada 2014–2018 dan membaca bujur dari metadata tiap bulan. Konversi waktu matahari lokal adalah UTC + bujur timur/15 jam. Hanya uji sintetis yang dijalankan; **tidak ada** Sq, PCA, statistik, grafik, atau unduhan untuk stasiun K11.

Deviasi dan temuan S7-C pasca-hasil tercatat di `G2R_changes.md` dengan label eksploratoris. Proyek dapat lanjut ke rancangan G4-R menurut protokol; label struktur saat ini tetap S-DEVIATE.
