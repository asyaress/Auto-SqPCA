# Amandemen F3-v1.1 dan Instruksi Tugas B — Auto-SqPCA Fase 3

**Tanggal:** 15 November 2026
**Status:** APPROVED (peneliti utama, 15 Nov 2026)
**Berlaku untuk:** E2 dan E3 (Tugas B). Hasil Tugas A (E1) tidak diubah.
**Dasar:** review paket `F3A_review.zip` (SHA-256 `ece7681a…c1d8`). Amandemen ini dibuat **sebelum** E2/E3 dijalankan; tidak ada hasil E2/E3 yang sudah terlihat.

---

## 1. Keputusan atas Tugas A

| No | Butir | Keputusan | Alasan |
|---|---|---|---|
| K-A1 | Batas berhenti M-EM 10⁻⁸ nT (protokol: 10⁻⁴) | **Diterima.** | Perubahan terjadi di tahap uji sintetis T1, **sebelum** pengembangan dan pembekuan; tercatat di `F3_E1_frozen.json`. Penyebabnya inkonsistensi internal protokol (batas berhenti 10⁻⁴ nT tidak mungkin memenuhi syarat T1 galat < 10⁻⁶ nT). Bagian 10 F3-v1 mengizinkan perbaikan kode setelah uji sintetis gagal. Bukan penyetelan pasca-holdout. |
| K-A2 | Koreksi input GFZ 2018 setelah C1 awal terlihat | **Diterima dengan pengungkapan.** | Ini kelengkapan input (berkas IQD hilang menyebabkan 20 bulan 2018 tanpa kasus), bukan perubahan metode atau aturan. 476.280 baris awal identik; C1 awal (tanpa 2018) dan C1 akhir sama-sama BERHASIL. Naskah melaporkan keduanya. |
| K-A3 | Topeng DAY: rasio M-EM/M-INT = 1,000 | **Dicatat sebagai cacat desain protokol.** | Ketiga metode membuang hari yang hilang utuh dengan cara yang sama, jadi topeng DAY tidak bisa membedakan metode. C1 tetap dinilai menurut aturan terdaftar (2 dari 3 jenis); di naskah, DAY dilaporkan sebagai "setara menurut konstruksi". |
| K-A4 | Status C1 | **BERHASIL** (MCAR dan BLOCK24). | Aturan bagian 7 F3-v1: "quality-aware" boleh dipakai. |
| K-A5 | Holdout terputus dan dilanjutkan | **Diterima.** | Kode dan konfigurasi beku, ringkasan tidak dilihat sebelum selesai, hash dicatat. |

### Temuan E1 untuk naskah (dari ringkasan holdout, M-EM kecuali disebut lain)

- **Blok 24 jam:** M-EM memangkas galat sekitar separuh dibanding interpolasi linear asal (rasio 0,50–0,51, CI 95% atas < 0,53).
- **MCAR:** M-EM lebih baik nyata pada 20–40% (rasio 0,87–0,92).
- **Batas aman (ε = 0,05):** MCAR p* = 10%; untuk semua jenis blok dan hari hilang tidak terdefinisi, karena ekor distribusi galat (persentil 90) sudah melampaui 2ε pada 10%.
- **Topeng nyata TND:** M-EM median galat 0,45 (8,3% tanpa keluaran); M-INT 0,59 (12,1%); M-EXC 100% tanpa keluaran. Aturan eksklusi hari tradisional tidak dapat memproses data seburuk TND sama sekali.
- **Temuan deskriptif (bukan klaim, bukan dasar perubahan):** pada blok 24 dan 72 jam, M-EXC memberi median galat lebih kecil daripada M-EM (mis. blok 24 jam 10%: 0,060 vs 0,072). Tidak ada satu metode yang terbaik untuk semua struktur celah. Ini dibahas di naskah sebagai arah pengembangan (penanganan celah adaptif), **tidak** diadopsi di Fase 3.

---

## 2. Perubahan prospektif untuk E2 (sebelum E2 dijalankan)

### 2.1 Masalah: aturan pemilihan θ tidak dapat dipenuhi

Hasil E1 memberi θ_d = 1 − p*_MCAR = **0,90**. Di SSB, separuh kasus diberi topeng MCAR 20%, sehingga fraksi teramati ≈ 0,80 < θ_d. Akibatnya **semua** kasus bertopeng otomatis abstain lewat A3, coverage total maksimum sekitar 50%, dan syarat coverage ≥ 0,80 (bagian 5.3 dan 5.4 F3-v1) **tidak mungkin dipenuhi oleh θ mana pun**. Protokol tidak punya aturan untuk kasus ini. Tanpa perbaikan, C3 gagal karena konstruksi desain, bukan karena metode.

### 2.2 Perbaikan (berlaku untuk E2)

| Kode | Ketentuan |
|---|---|
| A-1 | θ_d tetap **0,90** sesuai aturan F3-v1 (tidak diubah). |
| A-2 | **Strata utama** untuk pemilihan θ_s, θ_w (pengembangan) dan uji C2, C3 (holdout) = kasus SSB **tanpa topeng**. |
| A-3 | **Strata bertopeng (MCAR 20%)** dilaporkan terpisah: tingkat abstain per alasan (A1–A4), dan galat kasus yang tetap diterima bila ada. Harapan yang didaftarkan: hampir semua abstain lewat A3; ini menunjukkan aturan bekerja sesuai batas E1, bukan kegagalan. |
| A-4 | Bila di strata utama tidak ada kombinasi θ yang mencapai coverage ≥ 0,80: pilih coverage terbesar; seri → median galat diterima terkecil. C3 lalu dinilai **gagal** bila coverage holdout < 0,80 (aturan F3-v1 tidak dilonggarkan). |
| A-5 | Grid θ, tujuan pemilihan, ambang C2/C3, pembagian set, dan seed **tidak berubah**. |

### 2.3 E3

θ_d = 0,90 berlaku juga di E3. Bulan nyata dengan fraksi jam teramati < 90% akan abstain lewat A3; ini dilaporkan sebagai hasil, bukan disingkirkan.

---

## 3. Pelaporan tambahan yang sudah terdaftar tetapi belum ada di paket Tugas A

Tanpa menghitung ulang E1 (cukup dari CSV kasus holdout yang sudah ada, SHA-256 `1acbda1a…ceb3`):

1. **Metrik sekunder E1 (F3-v1 bagian 3.4):** galat relatif kandidat tetap, sudut subruang PC1, dan kesepakatan kandidat terpilih, per metode × jenis topeng × p. Tujuannya memisahkan galat PCA dari galat akibat kandidat berganti. [Hipotesis, belum diuji: ekor berat galat utama berasal dari pergantian kandidat.]
2. **Konvergensi M-EM:** distribusi perubahan akhir pada 116.777 kasus yang mencapai batas 500 iterasi; laporkan berapa persen yang perubahan akhirnya < 10⁻⁴ nT (batas protokol asli) dan < 10⁻⁶ nT.
3. Keduanya deskriptif; tidak mengubah status C1, metode terpilih, atau p*.

---

## 4. Reproduksibilitas (C5)

CLI Tugas A tidak memasukkan koreksi GFZ 2018. Tambahkan pembungkus `reproduce_f3a.py` (atau target CLI `f3a-final`) yang menjalankan urutan persis: kode E1 beku → `f3_gfz2018.py` → `f3_e1_2018_correction.py` → evaluator → finalizer, dan memverifikasi hash keluaran akhir sama dengan paket Tugas A. Kode E1 beku tidak diubah.

---

## 5. Instruksi Tugas B untuk Claude Code (menggantikan blok Tugas B di F3-v1)

Simpan dokumen ini sebagai `phase3/F3_amendment_v1.1.md`, catat SHA-256-nya.

```text
PERAN: Scientific Python developer + reproducibility auditor.
PROYEK: Auto-SqPCA Fase 3. Akar: <REPOSITORY_ROOT>
DASAR: phase3/F3_protocol_v1.md + phase3/F3_amendment_v1.1.md (keduanya
APPROVED). Bila bertentangan, amandemen v1.1 yang berlaku untuk E2/E3.
CAKUPAN: pelaporan tambahan E1, pembungkus reproduksi, E2, E3.
E1 sudah beku; jangan diubah atau dihitung ulang.

LANGKAH 0 - Verifikasi
- Hash F3_protocol_v1.md, F3_amendment_v1.1.md, F3_E1_frozen.json, paket
  kode auto_sqpca, CSV kasus holdout E1 (1acbda1a...ceb3).

LANGKAH 1 - Pelaporan tambahan E1 (amandemen bagian 3), dari CSV yang ada
- F3_E1_secondary_metrics.csv; F3_E1_convergence.json. Tanpa simulasi baru.

LANGKAH 2 - Pembungkus reproduksi (amandemen bagian 4)
- reproduce_f3a.py; jalankan dalam mode verifikasi hash (boleh memakai
  cache kasus bila hash cocok); catat hasil di F3_reproduce_check.json.

LANGKAH 3 - SSB (F3-v1 bagian 4)
- Bangun SSB pengembangan dan holdout; DIFI-8 via pyDIFI (catat versi).
  pyDIFI gagal -> TRUTH_FALLBACK (F3-v1 bagian 10).
- F3_ssb_manifest.csv.

LANGKAH 4 - E2 pengembangan (strata utama = tanpa topeng; amandemen A-2)
- ASAL, AUTO-NA, AUTO; theta_d = 0,90 (A-1); grid theta_s, theta_w;
  tujuan F3-v1 5.3; bila tidak layak terapkan A-4.
- Bekukan F3_E2_frozen.json + SHA-256 SEBELUM holdout.

LANGKAH 5 - E2 holdout (satu kali)
- Strata utama: uji C2 dan C3 (F3-v1 5.4), kurva risk-coverage, uji
  alpha = 0.
- Strata bertopeng: laporan A-3.
- Label C2, C3 sesuai F3-v1 bagian 7.

LANGKAH 6 - E3 (F3-v1 bagian 6; amandemen 2.3)
- Pipeline beku tanpa perubahan pada COI, KDU, GUA, PLR, TUN (+ E3b bila
  syarat Fase 1 terpenuhi). Evaluasi utama terhadap DIFI; IQD ditandai
  tidak independen. Lintang geomagnet dipol IGRF-13 2015 (catat pustaka).

LANGKAH 7 - Klaim
- F3_claims.json: status C1 (BERHASIL, dengan catatan K-A2, K-A3), C2, C3,
  C4; judul yang diizinkan menurut F3-v1 bagian 7; kalimat klaim yang boleh
  dipakai, termasuk temuan E1 di amandemen bagian 1.

LANGKAH 8 - Gambar dan tabel untuk naskah (F3-v1 bagian 11, butir 3-7)

LANGKAH 9 - Paket
- F3B_report.md, F3B_execution.log, F3B_checksums.sha256 (berkas isi).
- F3B_review.zip tanpa data mentah; SETELAH ZIP final, SHA-256 ke
  F3B_review.zip.sha256 DI LUAR ZIP.

LARANGAN: F3-v1 bagian 9. Tambahan: tidak mengganti metode celah (M-EM
beku), tidak mengubah theta_d, tidak memakai temuan M-EXC-pada-blok untuk
mengubah pipeline.
KONDISI BERHENTI: F3-v1 bagian 10.
JIKA RAGU: UNRESOLVED dengan bukti; jangan menebak.
SELESAI: BERHENTI dan laporkan satu paragraf: theta beku, C2, C3,
coverage holdout strata utama, abstain strata bertopeng, ringkasan E3 per
stasiun, judul yang diizinkan.
```
