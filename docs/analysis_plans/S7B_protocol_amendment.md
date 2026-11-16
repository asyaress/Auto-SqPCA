# Amandemen resmi G0-registration-2 untuk Fase 2A

**Status: APPROVED.** Berlaku 13 November 2026 melalui delegasi peneliti utama yang dinyatakan dalam dokumen keputusan sumber. Protokol G0-registration-1 tetap utuh. Isi keputusan K1–K11 dan tabel di bawah disalin dari dokumen resmi; instruksi operasional untuk Claude Code di akhir sumber tersedia utuh dalam `S7B_decisions_approved.md`.

Sumber: `<LOCAL_PROTOCOL_DOCUMENT>`; SHA-256 DOCX `c722cbcc25b7328c02425d40bd98d54c13fcc1e8aa20fdd9af965858cb67e5f1`; SHA-256 konversi Markdown `6385bdc268e4c8f28dc7f2961a1db2e30c9340bcc487410b3a57b4ebb4282f64`. Dokumen sumber tidak berada di working directory saat preflight; ditemukan di lokasi tersebut.

## Penerapan kebijakan per DAT

Manifest `S7B_benchmark_policy.csv` berisi 684 DAT: ORIGINAL_ABSOLUTE=624, ABSOLUTE_REPORTED_ONLY=36, SUSPECT_DIAGNOSTIC=18, EXCLUDED=6. Pengecualian tetap berada dalam target_total. `development_seen` dicatat pada tingkat DAT bila ada jejak perbandingan dalam D1/D2/S7-A; hal itu tidak membuktikan seluruh seri dalam berkas telah dianalisis. Untuk denominator prospektif, hitung kategori berurutan dan saling eksklusif: EXCLUDED, lalu SUSPECT_DIAGNOSTIC, lalu DEVELOPMENT_SEEN pada sisa, lalu ELIGIBLE_PROSPECTIVE. Laporkan jumlah label development_seen mentah secara terpisah agar tidak terjadi pengurangan ganda.

## Aturan klasifikasi D2b yang tumpang tindih

MATCH dan QUANT pada sumber dapat sama-sama benar untuk |d| di atas 0,02 nT hingga batas MATCH. Kode D2b mencatat semua predikat yang benar, overlap, dan gabungan MATCH∪QUANT tanpa prioritas baru. Jika ambiguitas mengubah baris keputusan G1, keputusan ditandai UNRESOLVED. Ini mencatat masalah logika sumber, bukan mengubah ambang.

## Teks keputusan resmi yang berlaku

# Keputusan S7-B dan Instruksi Eksekusi Claude Code (G0-registration-2)

Nov 13, 2026 · @supriyanto

## Ringkasan keputusan

Amandemen G0-registration-2 disetujui: benchmark dikarantina berdasarkan hash, toleransi ≤0,1 nT tetap berlaku dan semua kegagalannya tetap tercatat, dan satu eksperimen D2b dijalankan sebelum G1 diputuskan dengan aturan yang sudah didaftarkan. Setelah D2b, forensik benchmark ditutup.

- Dasar persetujuan: peneliti utama mendelegasikan finalisasi keputusan pada 13 November 2026; keputusan di dokumen ini berlaku sebagai keputusan peneliti utama. Protokol G0-registration-1 tidak diubah; dokumen ini adalah amandemen yang terpisah.

- Tidak menghubungi penulis asal (keputusan peneliti utama). Persoalan O1 (pemusatan Sq), O3 (berkas Y/Z identik), dan O8 (preprocessing PCA) akan dilaporkan di naskah sebagai pengamatan atas dataset publik, dengan bahasa netral.

- Target klaim naskah: replikasi tingkat R2 + R3 + R4 (lihat bagian klaim), bukan reproduksi numerik persis.

- Langkah sesudahnya: Claude Code mengerjakan S7-B + D2b, menetapkan status G1 sesuai aturan, lalu berhenti dan menyerahkan paket review. Pilot G2 butuh instruksi terpisah.

## Keputusan final

Sebelas keputusan berikut berlaku sejak tanggal dokumen ini; masing-masing punya alasan yang tidak bergantung pada hasil yang belum dilihat.

| Kode | Keputusan | Alasan |
| --- | --- | --- |
| K1 | Toleransi ABSOLUTE ≤0,1 nT untuk Sq IQD tetap berlaku. Hasil 0/18 kontrol dicatat FAIL dan tidak diubah | Mencegah pelonggaran ambang setelah hasil terlihat |
| K2 | Untuk IQD, metrik kebal offset (korelasi, RMSE dan selisih maksimum setelah rata-rata 24 jam dihapus) dilaporkan deskriptif, tanpa ambang lulus baru. Kecukupan IQD sebagai acuan dinilai di G4 lewat kesepakatan keputusan: klasifikasi PC dijalankan dua kali, dengan IQD kita dan IQD Mendeley; keputusan yang sama berarti selisih kurva tidak material | Klasifikasi asal memakai \|r\| dan DTW pada deret terstandardisasi, yang kebal offset. Kesepakatan keputusan tidak membutuhkan ambang baru yang dipilih setelah melihat data |
| K3 | Semua deret yang sudah dibandingkan di D1, D2, atau S7-A diberi label DEVELOPMENT_SEEN, dilaporkan terpisah, dan tidak dihitung di penyebut evaluasi prospektif | Deret yang sudah dilihat tidak bisa menjadi uji yang jujur |
| K4 | Seluruh Februari (X, Y, Z; per tahun dan gabungan) dikeluarkan dari pemilihan varian D3. Februari hanya dievaluasi di G3, dengan bendera | Mencegah anomali Y/Z dan Z 2014 bocor ke pemilihan V0–V3 |
| K5 | Enam DAT Februari Y yang identik dengan Z: EXCLUDED dari target numerik Y, tetap tercatat di penyebut sebagai dikecualikan | Terbukti bukan keluaran Y |
| K6 | Isu F ditangguhkan sebagai DEFERRED_FOR_XYZ_PCA. Dibuka kembali bila: (a) F dipakai di analisis mana pun; (b) jam F yang tidak cocok berkorelasi dengan residu XYZ di G2/G3; (c) QC pengembangan memakai F | PCA dan klasifikasi asal hanya memakai X, Y, Z |
| K7 | Sq IQD Februari 2016 memakai Q1–Q5 resmi GFZ (termasuk 29 Februari), berlabel PROVISIONAL di semua laporan | Sesuai daftar resmi dan paling cocok bentuknya di D1 |
| K8 | D2b (perbandingan meanField vs rata-rata harian WDC) adalah satu-satunya eksperimen sebelum G1 | Satu-satunya jejak data masukan penulis; menguji versi data tanpa kode penulis |
| K9 | Setelah D2b, forensik offset dan benchmark ditutup. Residu yang belum terjelaskan ditulis sebagai keterbatasan | Mencegah audit tanpa akhir |
| K10 | Bila pilot G2 non-Februari tidak menemukan varian V0–V3 yang lolos toleransi struktural PCA, replikasi ketat dihentikan dan proyek lanjut dengan "implementasi ulang dengan deviasi terdokumentasi" sebagai baseline Auto-SqPCA | Kebaruan Auto-SqPCA tidak bergantung pada reproduksi persis |
| K11 | Jalur paralel tanpa analisis diizinkan: loader data per jam PLR, TUN, KDU, GUA dan konversi baseline malam ke waktu matahari lokal. Tanpa PCA, tanpa Sq, tanpa statistik hasil | Memangkas waktu Fase 3 tanpa melanggar Strategi B |

## Kebijakan benchmark

Setiap DAT Mendeley mendapat satu status penggunaan; tidak ada berkas yang dihapus dari penyebut atau ditimpa.

| Kategori (status S7-A) | Jumlah | Penggunaan yang diizinkan | Dilarang |
| --- | --- | --- | --- |
| PCA non-Februari, VERIFIED | sebagian besar dari 624 | ORIGINAL_ABSOLUTE untuk D3 (pilot) dan G3; target utama replikasi PCA | — |
| PCA Februari X/Z, VERIFIED | sisa dari 624 | G3 saja, berbendera FEBRUARY | Pemilihan varian D3 |
| 36 DAT IQD Sq/SD/S, SUSPECT | 36 | ABSOLUTE dilaporkan dengan ambang beku; metrik kebal offset deskriptif; acuan untuk uji kesepakatan keputusan di G4 | Dipakai sebagai bukti lulus absolut; ambang bentuk baru |
| 12 DAT PCA Februari Y (PC/EOF/VF/mode3), SUSPECT | 12 | Dilaporkan di G3 sebagai SUSPECT_DIAGNOSTIC | D3; dihitung sebagai lulus/gagal utama |
| 6 DAT PCA Februari Z terkait 2014, SUSPECT | 6 | Dilaporkan di G3 sebagai SUSPECT_DIAGNOSTIC | D3 |
| 6 DAT Februari Y identik Z, UNUSABLE | 6 | Tercatat sebagai EXCLUDED dengan alasan | Target numerik Y apa pun |

Jumlah per baris diambil dari S7_benchmark_manifest.csv; Claude Code harus mengisi angka pastinya dan memastikan totalnya 684.

### Format tabel penyebut (wajib di setiap laporan G2/G3/G4)

| Kolom | Isi |
| --- | --- |
| target_total | Semua target dalam cakupan gate, sebelum pengecualian |
| excluded | Jumlah + alasan (UNUSABLE, NO_DATA) |
| suspect_diagnostic | Dilaporkan, tidak dihitung di penyebut utama |
| development_seen | Sudah dilihat sebelum amandemen; dilaporkan terpisah |
| eligible_prospective | Penyebut utama = total − excluded − suspect − development_seen |
| pass_absolute / fail_absolute | Terhadap toleransi beku |
| pass_structural / fail_structural | Untuk PCA: VF, subruang, rekonstruksi mode (toleransi protokol) |
| decision_agreement | Untuk G4: jumlah keputusan yang sama / total |

Persentase keberhasilan selalu ditulis bersama target_total dan eligible_prospective, sehingga pembaca melihat berapa banyak yang dikecualikan.

## Spesifikasi D2b

D2b menguji apakah data masukan penulis sama dengan data WDC sekarang, dengan membandingkan rata-rata harian di berkas meanField terhadap rata-rata harian yang dihitung dari data per jam WDC. Tidak ada PCA, SVD, fitting, atau pemilihan varian.

Dasar: artikel data 2021 menyebut berkas meanField berisi nilai rata-rata harian komponen terpilih untuk bulan tertentu.

Cakupan: berkas COI_{X,Y,Z}_meanField_mMM.dat per tahun, bulan Januari dan Maret–Desember, 2007–2017. Februari dikeluarkan (K4). Berkas _y_all hanya dicek konsistensinya terhadap berkas per tahun, bukan dianalisis.

Langkah:

- Catat resolusi cetak (jumlah desimal) berkas meanField sebelum perbandingan apa pun.

- Hitung rata-rata 24 jam per hari dari data per jam WDC, dengan celah diinterpolasi linear di dalam bulan (seperti metode asal). Catat jumlah jam yang diinterpolasi per hari.

- Pasangkan dengan meanField per hari. Bila jumlah atau urutan hari tidak cocok, catat ALIGNMENT_FAIL dan jangan menebak pemetaan.

- Hitung d = rata-rata WDC − meanField per hari dan komponen.

- Klasifikasikan setiap hari:

- MATCH: |d| ≤ 0,02 nT + setengah resolusi cetak;

- QUANT: 0,02 < |d| ≤ 0,08 nT;

- SMALL_UNEXPLAINED: 0,08 < |d| ≤ 0,5 nT;

- REVISION: |d| > 0,5 nT.

- Uji tanda khas kuantisasi: median d per komponen. Hipotesis kuantisasi (H-a) didukung bila median X dan Z berada di −0,08 sampai −0,02 nT dan median Y di +0,02 sampai +0,08 nT, atau sebaliknya (tanda berlawanan antara komponen positif dan Y yang negatif di COI).

- Untuk hari REVISION, catat apakah hari itu termasuk lima IQD bulannya; ini menghubungkan D2b dengan kegagalan 18 kontrol tanpa analisis tambahan.

Batas: satu kali jalan. Bila kode bermasalah, perbaiki kodenya; aturan klasifikasi dan ambang di atas tidak boleh diubah.

## Aturan keputusan G1

Status G1 ditentukan secara mekanis dari hasil D2b menurut tabel ini, yang didaftarkan sebelum D2b dijalankan. Prasyarat yang sudah terpenuhi: waktu XYZ terkonfirmasi (D2), kalender PCA terkonfirmasi (D1), amandemen disetujui (dokumen ini).

| Hasil D2b (hari non-Februari, X/Y/Z) | Arti | Status G1 | Akibat untuk G3 |
| --- | --- | --- | --- |
| MATCH ≥ 99% hari | Data masukan identik dengan versi penulis | CONDITIONAL PASS | Kegagalan absolut IQD berasal dari perhitungan atau ekspor; dicatat sebagai keterbatasan |
| MATCH + QUANT ≥ 99%, dan pola tanda H-a terpenuhi | Produk per jam berbeda kuantisasinya | CONDITIONAL PASS dengan batasan tertulis | Kegagalan absolut IQD dinyatakan di muka sebagai akibat kuantisasi |
| REVISION > 1% hari, tetapi bulan terdampak ≤ 10% | Revisi data terlokalisasi | CONDITIONAL PASS untuk bulan tanpa REVISION; bulan terdampak EXCLUDED dengan alasan | Penyebut G3 dikurangi bulan terdampak, tercatat di tabel penyebut |
| Bulan terdampak REVISION > 10% | Revisi luas | HOLD | Lanjut ke K10: implementasi ulang dengan deviasi terdokumentasi |
| ALIGNMENT_FAIL, atau isi berkas bukan rata-rata harian | Bertentangan dengan dokumentasi | HOLD | Lanjut ke K10 |
| Selain kasus di atas (banyak SMALL_UNEXPLAINED) | Penyebab tidak terbatasi | CONDITIONAL PASS dengan batasan "versi data tidak terverifikasi" | Klaim replikasi turun satu tingkat |

Bulan terdampak = bulan dengan setidaknya satu hari REVISION di komponen mana pun.

Apa yang tidak dikatakan oleh CONDITIONAL PASS: bahwa Sq IQD tereproduksi, bahwa versi data penulis identik di semua hari, atau bahwa G2–G4 akan lulus. CONDITIONAL PASS hanya berarti aturan data dan waktu cukup jelas untuk memulai pilot G2.

## Klaim replikasi dan kriteria berhenti

Naskah menargetkan klaim R2 + R3 + R4. Bila R3 gagal, proyek tidak berhenti; ia beralih ke baseline implementasi ulang (K10).

| Tingkat | Klaim di naskah | Syarat | Perkiraan |
| --- | --- | --- | --- |
| R1 | Reproduksi numerik persis | Semua toleransi absolut lolos | Kemungkinan tidak tercapai untuk IQD (0/18 kontrol) |
| R2 | Kurva Sq IQD tereproduksi sampai satu konstanta per deret, konsisten dengan pemusatan rata-rata nol yang tidak terdokumentasi di dataset publik | Metrik kebal offset dilaporkan; selisih absolut dilaporkan; uji kesepakatan keputusan di G4 | Didukung bentuk (r ≥ 0,9986 di 18 kontrol, sudah dilihat) |
| R3 | Struktur PCA tereproduksi (VF, subruang, rekonstruksi mode) | Toleransi struktural protokol lolos di target eligible_prospective | Belum diuji |
| R4 | Keputusan klasifikasi PC tereproduksi | Kriteria Tingkat 2 protokol + kesepakatan keputusan IQD (K2) | Belum diuji |

Kriteria berhenti yang objektif:

- Forensik benchmark: berhenti setelah D2b (K9), apa pun hasilnya.

- Replikasi PCA: bila tidak ada varian V0–V3 yang lolos toleransi struktural di pilot non-Februari, berhenti (K10).

- Replikasi klasifikasi: bila versi DIFI3 asli tidak tersedia, klaim R4 paling tinggi CONDITIONAL, dan tidak ada upaya merekonstruksi DIFI3.

- Batas waktu: S7-B + D2b dalam satu sesi kerja; pilot G2 dalam satu sesi berikutnya. Bila terlampaui karena investigasi baru, berhenti dan laporkan.

Penulisan temuan dataset: duplikasi Y/Z dan pemusatan yang tidak terdokumentasi ditulis sebagai pengamatan atas dataset Mendeley v1, dengan hash berkas, tanpa menduga penyebab atau menyalahkan penulis.

## Larangan

Sampai pilot G2 diizinkan dengan instruksi terpisah, hal-hal berikut dilarang:

- PCA atau SVD apa pun pada data WDC, termasuk "sekadar mencoba" V0–V3.

- DTW, DIFI, uji surrogate, classifier, ICA, NMF, autoencoder.

- Investigasi offset, mode, atau benchmark di luar D2b.

- Mengubah status 18 kontrol yang tercatat FAIL, atau memakai metrik kebal offset untuk menyatakan lulus.

- Menetapkan ambang baru setelah melihat hasil D2b.

- Memakai berkas Februari (komponen apa pun) untuk keputusan preprocessing.

- Menimpa, menyalin ulang, atau "membetulkan" berkas Mendeley, WDC, GFZ, atau artefak beku Fase 1/G0/D1/D2/S7-A.

- Menghitung Sq, statistik, atau gambar hasil untuk PLR, TUN, KDU, GUA di jalur paralel K11.

- Mengubah G0-registration-1. Semua perubahan masuk ke G0-registration-2 dengan hash dan changelog.
