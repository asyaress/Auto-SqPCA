# S7-C — Registrasi 3 dan keputusan G1

**G0-registration-3 APPROVED; G1 registration-2 tetap HOLD; G1 registration-3 HOLD (baris 0a).** Perintah henti berlaku sebelum perhitungan D2c karena 267,475/375,824 jam–elemen valid (**71.170%**) tidak setara dalam 0,1 nT; ambang yang disetujui hanya 0,1% jam. Status `WDC_FORMAT_INCONSISTENT` adalah hasil ambang silang format, bukan bukti revisi historis WDC. G2 pilot **belum siap**. Jalur K10 implementasi ulang dengan deviasi terdokumentasi adalah konsekuensi keputusan, bukan eksperimen yang dijalankan di S7-C.

Dokumen keputusan registration-3 disalin utuh dengan SHA-256 `cb5fdd487d460d986ec568916979bac0e7b6c0bb6d4891f3d423e770c2889573`; A1–A7 terdaftar di protokol baru. Respons WDC final 11 tahun berukuran 568,166 byte, SHA-256 `5fa0161e935fa759d133f733ba769dda9f000ce1e45bc1e3a49ec565a0d0c9d3`; respons pertama yang hanya 2007/2017 dipertahankan dan dicatat sebagai koreksi permintaan. Parser memeriksa 16.072 baris fixed-width dan 385.728 jam–elemen; tabel base serta CSV silang per jam tersedia. Base berubah pada X, Y, F; Z tetap 312. `d′` dan H-a D2c **tidak dievaluasi**.

Delta A5 berisi 72 baris DAT PCA X sebagai **overlay tingkat seri 2008** untuk April, Juni, September, dan November. Tidak ada bulan `EXCLUDED` dari D2c karena klasifikasi pascatransformasi dihentikan sebelum dijalankan. Status 18 kontrol Sq FAIL absolut, D1-IQD provisional, dan semua keluaran S7-B tidak diubah. D2d, D3/D4, PCA/SVD, DTW, DIFI, classifier, dan G2–G4 tidak dijalankan.

Paket review memuat laporan, kode, CSV hasil silang, JSON, log, serta checksum berkas isi. ZIP mentah WDC/Mendeley tidak disertakan. Hash ZIP review dan koreksi sidecar ZIP S7-B berada di berkas `.sha256` **di luar** masing-masing ZIP.
