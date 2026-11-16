# Amandemen G0-registration-3 dan Instruksi D2c — Auto-SqPCA

**Tanggal:** 13 November 2026
**Status:** APPROVED (peneliti utama, 13 Nov 2026)
**Menggantikan sebagian:** G0-registration-2 (bagian D2b dan tabel keputusan G1). Semua keputusan K1–K11 di registration-2 tetap berlaku kecuali yang diubah eksplisit di sini.
**Catatan permanen yang tidak diubah:** hasil D2b dan status **G1 HOLD di bawah G0-registration-2**.

---

## 1. Koreksi asumsi D2b

D2b membandingkan `meanField` Mendeley dengan rata-rata harian WDC dengan asumsi keduanya berada di **kerangka acuan level yang sama** (nT absolut). Dokumentasi Mendeley hanya menyebut "daily mean values" tanpa kerangka acuan, dan protokol tidak memeriksa kerangka itu sebelum membandingkan. Ini kekurangan spesifikasi, bukan kesalahan eksekusi.

Cacat kedua: tabel keputusan G1 di registration-2 tidak punya aturan prioritas bila lebih dari satu baris terpenuhi.

**Yang tetap sah dan permanen:**
- D2b dijalankan sesuai aturan; 10.953 selisih mentah disimpan apa adanya.
- G1 HOLD (registration-2) dilaporkan di naskah/lampiran.
- Label `REVISION` di D2b berarti hanya `|d| > 0,5 nT`. Label itu **bukan bukti revisi historis** dan tidak boleh ditulis demikian.

## 2. Hipotesis yang diuji (belum terbukti)

Format data per jam WDC menyimpan setiap baris harian sebagai *tabular base* (kolom 17–20, satuan ratusan nT untuk elemen intensitas) ditambah 24 *tabular value*, dengan `value (nT) = tabular base × 100 + tabular value`. Hipotesisnya: `meanField` dihitung dari tabular value tanpa base.

Konstanta eksploratoris reviewer (+25.000, −1.800, +36.000 nT, setara base 250, −18, 360) **tidak dipakai** sebagai transformasi. Transformasi hanya boleh berasal dari metadata berkas sumber.

## 3. Isi amandemen

| Kode | Ketentuan |
|---|---|
| A1 | **Kerangka acuan dari metadata.** Transformasi = tabular base × 100 per baris harian per elemen, dibaca dari berkas data per jam COI format WDC resmi (`/data/zipped-data/hour/COI`, `file_format=wdc`). Tidak ada konstanta hasil fitting. |
| A2 | **Tiga kategori pembanding terpisah:** (a) level absolut = hasil D2b, tetap FAIL; (b) kesetaraan setelah transformasi kerangka yang terbukti = D2c; (c) ketidakcocokan lokal tersisa, dilaporkan per bulan dan per komponen. |
| A3 | **Aturan prioritas tabel G1:** bila beberapa baris terpenuhi, berlaku baris dengan status paling konservatif (HOLD > CONDITIONAL PASS dengan pengecualian > CONDITIONAL PASS). |
| A4 | **D3, varian V0 dalam dua kerangka:** V0-A (nilai absolut) dan V0-T (tabular value = nilai − base × 100). V1–V3 tidak terpengaruh karena centering menghapus konstanta. Ini didaftarkan sekarang, sebelum D3. |
| A5 | **Inkonsistensi lokal X 2008:** berkas PCA komponen X untuk 2008-04, 2008-06, 2008-09, 2008-11 diberi status `SUSPECT_DIAGNOSTIC`, karena inkonsistensi `meanField _y_all` X di bulan itu sudah tercatat di S7-B sebelum PCA apa pun. Y dan Z bulan itu tidak terdampak oleh ketentuan ini. |
| A6 | **Pengungkapan non-buta:** D2c bukan uji buta, karena hasil eksploratoris reviewer sudah diketahui. Mitigasinya: transformasi dari metadata, ambang dan kategori D2b tidak diubah, tabel G1 tidak diubah (hanya ditambah A3). Kedua status G1 (registration-2 dan registration-3) dilaporkan berdampingan. |
| A7 | **R1 bukan target.** Reproduksi numerik persis dinyatakan tidak menjadi target naskah. Target tetap R2 + R3 + R4. |

## 4. Spesifikasi D2c

**Tujuan:** menguji kesetaraan `meanField` dengan data WDC setelah transformasi kerangka yang berasal dari metadata.

**Langkah:**

1. Unduh data per jam COI 2007–2017 format WDC resmi dari API WDC, satu kali. Simpan respons mentah apa adanya, read-only, dengan SHA-256 dan tanggal unduh.
2. Parse kolom 1–3 (kode), 4–5 (tahun), 6–7 (bulan), 8 (elemen), 9–10 (hari), 15–16 (abad), 17–20 (tabular base, I4), 21–116 (24 nilai I4), 117–120 (rata-rata harian). Nilai 9999 = hilang.
3. **Validasi silang wajib sebelum D2c:** untuk setiap jam, `base × 100 + tabular value` harus sama dengan nilai data per jam WDC yang dipakai di D2/D2b. Jika ada ketidakcocokan > 0,1 nT pada > 0,1% jam: catat `WDC_FORMAT_INCONSISTENT` dan berhenti (lihat bagian 5).
4. Catat tabel base per elemen per bulan. Laporkan apakah base konstan sepanjang 2007–2017 atau berubah, dan di bulan mana.
5. Untuk setiap pasangan hari–komponen yang valid di D2b (non-Februari): d' = d_D2b − base_hari × 100, dengan base dari baris hari itu.
6. Klasifikasikan d' dengan kategori dan ambang D2b **tanpa perubahan**: `MATCH` (|d'| ≤ 0,02 nT + setengah resolusi cetak), `QUANT` (0,02–0,08), `SMALL_UNEXPLAINED` (0,08–0,5), `REVISION_LIKE` (> 0,5). Nama kategori terakhir diganti dari `REVISION` agar tidak disalahartikan; batasnya sama.
7. Uji tanda khas kuantisasi (H-a) persis seperti spesifikasi D2b.
8. Laporkan residu > 0,5 nT per bulan dan per komponen, serta apakah harinya termasuk lima IQD bulan itu.

**Batas:** satu kali jalan. Bila kode bermasalah, perbaiki kodenya; ambang, kategori, dan aturan keputusan tidak boleh diubah.

## 5. Aturan keputusan G1 di registration-3

Tabel ini sama dengan registration-2, ditambah aturan prioritas A3 dan dua baris henti di awal.

| Urutan | Kondisi | Status G1 (registration-3) | Akibat |
|---|---|---|---|
| 0a | Berkas format WDC tidak tersedia, atau `WDC_FORMAT_INCONSISTENT` | **HOLD** | Langsung ke K10 (implementasi ulang dengan deviasi terdokumentasi) |
| 0b | Base dari metadata tidak menjelaskan selisih: `REVISION_LIKE` pada > 10% bulan | **HOLD** | K10 |
| 1 | `MATCH` ≥ 99% hari | **CONDITIONAL PASS** | Kegagalan absolut IQD (O1) tetap keterbatasan |
| 2 | `MATCH` + `QUANT` ≥ 99%, dan pola tanda H-a terpenuhi | **CONDITIONAL PASS** dengan batasan kuantisasi | Dinyatakan di muka untuk G3 |
| 3 | `REVISION_LIKE` > 1% hari, bulan terdampak ≤ 10% | **CONDITIONAL PASS** untuk bulan tanpa `REVISION_LIKE`; bulan terdampak `EXCLUDED` | Penyebut G3 dikurangi bulan terdampak, tercatat di tabel penyebut |
| 4 | Selain di atas (banyak `SMALL_UNEXPLAINED`) | **CONDITIONAL PASS** dengan batasan "versi data tidak terverifikasi" | Klaim replikasi turun satu tingkat |

- **Prioritas:** bila beberapa baris terpenuhi, berlaku status paling konservatif (A3).
- **Bulan terdampak** = bulan dengan setidaknya satu hari `REVISION_LIKE` di komponen mana pun (definisi registration-2, tidak diubah).
- **Bulan pilot D3** (Juni dan Oktober 2017; holdout Januari 2009 dan Maret 2015) dipakai hanya bila tidak termasuk bulan terdampak. Bila salah satu terdampak, pilot itu diganti dengan bulan non-Februari terdekat dari musim yang sama yang tidak terdampak, dipilih **sebelum** PCA apa pun.

**Yang tidak dikatakan oleh CONDITIONAL PASS:** bahwa Sq IQD tereproduksi, bahwa versi data penulis identik di semua hari, atau bahwa G2–G4 akan lulus.

**Kriteria berhenti:** setelah D2c, forensik benchmark ditutup (K9 tetap berlaku). Tidak ada D2d.

## 6. Rekonsiliasi provenans ZIP

Diagnosis: berkas `S7B_review.sha256` di dalam ZIP mengklaim hash ZIP itu sendiri. Ini mustahil benar, karena menambahkan berkas hash ke dalam ZIP mengubah ZIP. Selisih 190 byte (393.887 − 393.697) sesuai dengan ukuran satu entri teks kecil beserta header ZIP. Ke-20 checksum internal cocok, jadi isi paket utuh.

Aturan mulai sekarang:
1. Hash ZIP disimpan sebagai berkas pendamping **di luar** ZIP: `<nama>.zip.sha256`.
2. Hash dihitung **setelah** ZIP final selesai dibuat.
3. Di dalam ZIP hanya boleh ada checksum untuk berkas-berkas isinya, bukan untuk ZIP itu sendiri.
4. Peneliti mencocokkan hash di komputer lokal dan setelah transfer.
5. Untuk S7-B: buat ulang `S7B_review.zip.sha256` dari ZIP yang benar-benar dikirim (393.887 byte, SHA-256 `f1f43d99…5464` menurut reviewer, setelah dicek ulang lokal). Catat di changelog bahwa hash tertanam sebelumnya bersifat merujuk ke dirinya sendiri.

## 7. Risiko terhadap klaim

| Klaim | Status setelah registration-3 |
|---|---|
| R1 | Bukan target (A7) |
| R2 | Tidak berubah; tabular base hilang saat baseline dikurangkan. Masalah Sq rata-rata nol (O1) tetap keterbatasan |
| R3 | Aman untuk V1–V3; V0 diuji dalam dua kerangka (A4); penyebut X berkurang sesuai A5 |
| R4 | Tidak terpengaruh; \|r\| dan DTW terstandardisasi kebal offset |

---

## 8. Instruksi untuk Claude Code

Simpan dokumen ini sebagai `phase2a/S7C/G0-registration-3_D2c.md`, catat SHA-256-nya, lalu jalankan instruksi berikut.

```text
PERAN: Scientific Python developer + reproducibility auditor.
PROYEK: Auto-SqPCA, Fase 2A. Akar: <REPOSITORY_ROOT>
CAKUPAN: Registrasi G0-registration-3 + D2c + penetapan status G1 (reg-3).
TIDAK ADA D3/D4/PCA/SVD/DTW/DIFI/classifier.

DASAR: phase2a/S7C/G0-registration-3_D2c.md = keputusan peneliti utama yang
SUDAH DISETUJUI (13 Nov 2026). Ketentuan A1-A7 dan bagian 4-6 berlaku persis.

LANGKAH 0 - Verifikasi
- Verifikasi SHA-256 artefak beku G0/D1/D2/S7-A/S7-B sebelum menulis apa pun.
- Jangan mengubah hasil D2b, S7B_G1_decision.json, atau berkas apa pun di
  phase2a/S7B/. Semua keluaran baru masuk ke phase2a/S7C/.

LANGKAH 1 - Registrasi
- S7C_protocol_registration3.md: salin ketentuan A1-A7, spesifikasi D2c,
  tabel keputusan G1 reg-3, aturan provenans ZIP. Status APPROVED.
- S7C_changes.md: diff terhadap G0-registration-2, alasan (kerangka acuan
  tidak diperiksa; tabel G1 tanpa prioritas), risiko, rollback, SHA-256
  protokol reg-2 dan reg-3, pengungkapan non-buta (A6).

LANGKAH 2 - Akuisisi format WDC (satu kali)
- Unduh /data/zipped-data/hour/COI dengan file_format=wdc untuk 2007-2017.
- Simpan mentah di phase2a/raw/wdc_format_hourly/ (read-only), SHA-256,
  tanggal unduh, URL persis.
- Jika gagal atau kosong: tulis status 0a (HOLD) dan lompat ke LANGKAH 5.

LANGKAH 3 - Parse dan validasi silang
- Parse kolom tetap sesuai bagian 4 langkah 2. 9999 = hilang.
- Validasi: base*100 + tabular value vs nilai hourly WDC yang dipakai D2/D2b.
  Jika ketidakcocokan > 0,1 nT pada > 0,1% jam: WDC_FORMAT_INCONSISTENT,
  status 0a (HOLD), lompat ke LANGKAH 5.
- Keluaran: S7C_wdc_base_table.csv (elemen x tahun x bulan: base unik,
  jumlah hari per base), S7C_wdc_crosscheck.csv.

LANGKAH 4 - D2c
- Untuk setiap baris valid non-Februari di D2b_meanfield_comparison.csv:
  d_prime = d_wdc_minus_mendeley_nT - base_hari*100 (base dari baris hari
  dan elemen yang sama). Jangan memakai konstanta.
- Klasifikasi dengan ambang D2b TANPA perubahan: MATCH / QUANT /
  SMALL_UNEXPLAINED / REVISION_LIKE.
- Uji tanda H-a sesuai spesifikasi D2b.
- Residu > 0,5 nT: per bulan x komponen; tandai apakah hari IQD.
- Keluaran: D2c_comparison.csv, D2c_summary.json, D2c_report.md, d2c.py.

LANGKAH 5 - Keputusan G1 (reg-3)
- Terapkan tabel bagian 5 secara mekanis, dengan prioritas paling
  konservatif (A3). Catat semua baris yang terpenuhi dan baris yang dipakai.
- S7C_G1_decision.json: status reg-3, status reg-2 (HOLD, tidak diubah),
  angka pendukung, bulan EXCLUDED, berkas X 2008 yang menjadi
  SUSPECT_DIAGNOSTIC (A5), apakah bulan pilot D3 terdampak dan penggantinya
  bila ada (pilih sebelum PCA, aturan bagian 5).
- S7C_benchmark_policy_delta.csv: hanya baris yang statusnya berubah karena
  A5 atau bulan EXCLUDED; kolom sama dengan S7B_benchmark_policy.csv +
  kolom reason_reg3. Jangan menimpa S7B_benchmark_policy.csv.

LANGKAH 6 - Paket dan provenans
- S7C_report.md (ringkas), S7C_execution.log, S7C_checksums.sha256 (hanya
  berkas isi, BUKAN ZIP).
- Buat S7C_review.zip tanpa data mentah. SETELAH ZIP final selesai, hitung
  SHA-256-nya dan simpan di S7C_review.zip.sha256 DI LUAR ZIP.
- Buat juga S7B_review.zip.sha256 (di luar ZIP) dari S7B_review.zip yang
  ada, tanpa mengubah ZIP tersebut; catat di S7C_changes.md bahwa hash
  tertanam sebelumnya bersifat self-referential.

LARANGAN: tidak ada PCA/SVD/DTW/DIFI/classifier; tidak memakai konstanta
+25000/-1800/+36000; tidak mengubah ambang, kategori, atau tabel keputusan;
tidak mengubah hasil D2b atau status G1 reg-2; tidak menulis "revisi
historis"; tidak membuka investigasi selain D2c; tidak menimpa berkas sumber.

JIKA RAGU: tulis UNRESOLVED dengan bukti spesifik; jangan menebak.

SELESAI: setelah S7C_review.zip dan berkas .sha256 pendampingnya dibuat,
BERHENTI dan laporkan dalam satu paragraf: status G1 reg-2, status G1 reg-3,
baris tabel yang dipakai, bulan EXCLUDED, dan apakah pilot G2 siap.
```
