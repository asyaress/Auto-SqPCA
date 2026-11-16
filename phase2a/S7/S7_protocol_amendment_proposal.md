# Proposal amandemen protokol Fase 2A — S7-A (belum berlaku)

**Status: PROPOSED FOR REVIEW.** Protokol `G0-registration-1` dan semua artefak Fase 1/G0/D1/D2 tetap beku. Versi usulan: `G0-registration-2-S7-draft`, 13 November 2026. Proposal ini belum mengubah keputusan historis ataupun mengaktifkan perhitungan D3/D4.

## Perubahan yang diusulkan

1. Tambahkan daftar karantina berbasis SHA-256 dari `S7_benchmark_manifest.csv`. Enam `COI_Y_{meanField,mode1,mode2}_m02[ _y_all].dat` (nama tepat tercatat dalam manifest) dikeluarkan hanya dari benchmark numerik **Y Februari**. Tetap tersedia baca saja sebagai bukti sumber. Y PC/EOF/VF Februari diklasifikasikan SUSPECT dan diuji independen terhadap WDC di tahap yang memang mengizinkannya; jangan gunakan mode Y yang salah label sebagai validator. Enam berkas Z Februari per tahun terkait PC/EOF/mode 1/2 tetap SUSPECT sampai anomali 2014 dilokalisasi. Semua pengecualian harus dicatat dalam metrik cakupan dan tidak boleh dianggap PASS otomatis.
2. Pertahankan rumus Sq IQD protokol: baseline malam lima jam per hari pada lima IQD GFZ, termasuk 29 Februari 2016 secara **provisional**. Tambahkan perbandingan sekunder kurva setelah offset rerata 24 jam dihilangkan, diberi label `SHAPE_ONLY` atau `RECONSTRUCTED` bila disimpan. Tidak boleh menggantikan seri ORIGINAL Mendeley atau mengubah ambang Tingkat 1 selisih maksimum absolut ≤0,1 nT. Perbandingan `daily_mean` dan `night_then_center` dilaporkan sebagai satu kelas ekuivalen, bukan dua hipotesis independen.
3. Untuk jalur PCA yang hanya memakai X/Y/Z, izinkan F dinyatakan `DEFERRED_FOR_XYZ_PCA` setelah review. Status D2-DATA F tetap UNRESOLVED pada laporan beku dan harus kembali diperiksa jika tahap lain memakai F.
4. Pertahankan G1 HOLD sampai ruang lingkup benchmark, perlakuan seri SUSPECT, dan kriteria lulus bersyarat ditetapkan **sebelum** D3/D4. Jika paket amandemen diterima, nilai ulang G1 sebagai CONDITIONAL PASS hanya setelah reviewer memastikan gate dapat menilai D1/D2 tanpa memakai target tidak sah. Jangan menandai G1 PASS atau menyatakan Tingkat 1 Sq tercapai dari kecocokan bentuk.

## Dampak dan jejak perubahan

- G1: membutuhkan keputusan review eksplisit tentang karantina dan D1-IQD; status saat ini HOLD.
- G2/G3 serta replikasi penuh: denominator cakupan, komponen/bulan yang dikecualikan, dan metrik absolut vs bentuk harus dibedakan. Kegagalan Tingkat 1 pada seri lain tetap kegagalan.
- Data asli, SHA-256, nama/path, dan protokol asal tidak berubah. Implementasi hanya boleh memakai lapisan baca yang memeriksa hash dan mengeluarkan flag; referensi turunan harus bernama `RECONSTRUCTED`.
- Setiap adopsi harus mendapat nomor versi baru, tanggal, alasan berbasis S7, dan pencatatan pengaruh terhadap ambang serta cakupan sebelum eksperimen selanjutnya. Pembatalan dilakukan dengan kembali ke aturan `G0-registration-1` dan menjaga artefak S7 sebagai bukti.

## Bukti dasar

Enam hash Y/Z identik ada di `S7_decision.json`. Februari Y mode cocok dengan produk PC×EOF Z pada 10/11 tahun untuk masing-masing mode; Z 2014 menyisakan inkonsistensi. Semua 432 kolom Sq memiliki mean 24 jam ≤1,95×10⁻¹² nT; 18 kontrol luar Februari memiliki maksimum selisih sesudah pemusatan 0,1725–0,3425 nT, sehingga 0/18 memenuhi ambang 0,1 nT. Detail, hash, dan keterbatasan ada di laporan dan CSV.
