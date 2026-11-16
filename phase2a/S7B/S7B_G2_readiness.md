# Kesiapan pilot G2 setelah S7-B

**Status saat ini: TERTAHAN oleh G1 HOLD.** Dokumen ini merancang pilot saja; tidak ada PCA, SVD, D3, D4, atau klasifikasi dijalankan. Mulai G2 hanya dengan instruksi baru dan setelah keputusan G1 berubah melalui prosedur yang terdokumentasi.

## Target dan pemisahan pengembangan

- Bulan pemilihan varian preprocessing V0–V3: **Juni 2017** dan **Oktober 2017**, X/Y/Z. Gunakan hanya DAT `ORIGINAL_ABSOLUTE` dengan `d3_eligible=true` dari kebijakan S7-B. `DEVELOPMENT_SEEN` dilaporkan dan tidak masuk penyebut evaluasi prospektif; tetap dapat dipakai sebagai data pengembangan dengan label jelas.
- Holdout tetap: **Januari 2009** dan **Maret 2015**. Varian yang dipilih pada dua bulan pengembangan diterapkan sekali pada holdout tanpa pemilihan ulang. Semua Februari dilarang untuk pemilihan V0–V3, termasuk X/Z yang VERIFIED; Februari hanya dievaluasi di G3 berbendera sesuai K4.
- Pemeriksaan sebelum pilot: hash sumber, missing/interpolasi, metadata jam, dan konsistensi input. F tetap `DEFERRED_FOR_XYZ_PCA`, dengan tiga pemicu pembukaan kembali K6.

## Metrik dan aturan beku

Untuk tiap komponen/bulan/varian, hitung VF₁–VF₃ (selisih absolut ≤0,005), PC nondegenerat (|r| ≥0,999), EOF (RMSE ≤0,1 nT), sudut utama subruang bila pasangan singular hampir degenerat (≤5°), dan galat Frobenius relatif jumlah mode 1–3 (≤1%). Terapkan aturan resolusi cetak G0-registration-1 sebelum perbandingan, tanpa mengubah ambang berdasarkan hasil. Bandingkan `meanField` menurut uji D3 yang telah ditetapkan; jangan gunakan berkas yang `EXCLUDED` sebagai validator. Untuk pasangan hampir degenerat, gunakan kriteria North dari protokol dan nilai subruang/jumlah mode, bukan memaksakan PC individual.

Jika tidak ada V0–V3 yang lolos toleransi struktural pada pilot non-Februari, hentikan replikasi ketat menurut S3/K10 dan lanjutkan hanya sebagai implementasi ulang dengan deviasi terdokumentasi setelah keputusan peneliti. S4: kegagalan PC1 Y/Z nondegenerat (|r| <0,999) ialah tanda kegagalan implementasi. S5: kegagalan Tingkat 1 pada pengolahan penuh; belum dapat diuji. Jangan menjalankan K10 hanya dari G1 HOLD. R4 tetap bersyarat bila DIFI3 asli tidak tersedia; jangan merekonstruksinya.

## Denominator wajib pada laporan G2/G3/G4

Pada tingkat **DAT** untuk manifest awal, partisi saling eksklusif menggunakan urutan EXCLUDED → SUSPECT_DIAGNOSTIC → DEVELOPMENT_SEEN yang tersisa → ELIGIBLE_PROSPECTIVE. Label DEVELOPMENT_SEEN mentah dapat tumpang tindih, maka dilaporkan terpisah dan tidak dikurangkan dua kali. Untuk evaluasi deret G2/G3/G4, hitung ulang pada target deret sebenarnya beserta alasan setiap pengecualian. Contoh inventaris DAT saat ini (bukan hasil G2):

| target_total | excluded | suspect_diagnostic | development_seen | eligible_prospective | pass_absolute | fail_absolute | pass_structural | fail_structural | decision_agreement |
|---:|---:|---:|---:|---:|---|---|---|---|---|
| 684 | 6 | 18 | 381 | 279 | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |

Jumlah label `development_seen=true` mentah ialah 403 DAT; 22 di antaranya sudah masuk excluded/suspect. Setiap laporan kelak wajib menampilkan `target_total` bersama `eligible_prospective`, `pass_absolute/fail_absolute`, `pass_structural/fail_structural`, dan `decision_agreement` untuk G4. Enam Y Februari tetap tercatat sebagai excluded; 36 DAT IQD melaporkan hasil absolut beku dan metrik bentuk deskriptif, tanpa ambang bentuk baru. Keputusan G4 membandingkan klasifikasi dengan IQD kita dan Mendeley menurut K2, bila tahap itu kelak diizinkan.

## Dampak G1 saat ini

D2b memberi 121/121 bulan terdampak REVISION menurut ambang langsung. Tidak ada bulan non-Februari yang bersih untuk denominator utama G3 sesuai R4. Pilot G2 menunggu review dan instruksi baru; tidak ada klaim R3/R4.
