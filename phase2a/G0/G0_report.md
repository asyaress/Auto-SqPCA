# Gate G0 — Persiapan dan verifikasi input Fase 2A

**Keputusan: G0 CONDITIONAL PASS.** Pemeriksaan dilakukan 2026-11-13T07:11:50.346030+00:00.
Cakupan hanya akuisisi, pemeriksaan integritas, dan inventaris berkas. Tidak ada D1, D2, PCA, DTW, DIFI, atau klasifikasi PC yang dijalankan.

## Acuan dan batas data

- Protokol lokal: `G0-registration-1`, tanggal dokumen 2026-11-13; SHA-256 DOCX `6ea948b94aaa58e5f8d06d0c0a732fd48420fe45f22211bc503ae466681b49dd`. Nomor versi ini didaftarkan pada G0 karena DOCX asal tidak memuat nomor versi eksplisit.
- Semua penulisan G0 berada di `phase2a/G0/`; unduhan mentah berada di `phase2a/raw/`. Berkas audit Fase 1 yang dibekukan hanya dibaca.
- Mendeley: DOI `10.17632/jcmdrm5f5x.1`, versi 1, lisensi CC BY 4.0, rilis 2 Maret 2021. URL arsip stabil: https://data.mendeley.com/public-api/zip/jcmdrm5f5x/download/1 ; halaman: https://data.mendeley.com/datasets/jcmdrm5f5x/1 .
- WDC Edinburgh: `https://wdcapi.bgs.ac.uk/data/zipped-data/hour/COI?years=YYYY&file_format=iaga&orientation=XYZF`; 11 permintaan tahunan 2007–2017. Panduan: https://wdc.bgs.ac.uk/how-to-guide .
- GFZ: `https://datapub.gfz-potsdam.de/download/10.5880.Kp.0001/Quiet_Disturbed_Days/QD_daysYYYY.txt`; DOI `10.5880/Kp.0001`. Indeks: https://datapub.gfz-potsdam.de/download/10.5880.Kp.0001/Quiet_Disturbed_Days/ .

## Hasil pemeriksaan

| Pemeriksaan | Bukti | Status |
|---|---|---|
| Mendeley v1 | ZIP 78,079,630 byte; 3,636 anggota; CRC ZIP dan CRC semua hasil ekstraksi cocok; 684 DAT dan 2,952 PNG; nama dan hierarki asli dipertahankan | PASS |
| WDC COI per jam | 11 ZIP, 132 HOR bulanan, 96,432/96,432 timestamp unik HH:00; 29 Februari 2008 = 24 jam; CRC dan header IAGA-2002/XYZF cocok | PASS |
| GFZ IQD/IDD | 11 ASCII tahunan, 132 bulan, 1,320 entri Q dan 660 entri D; tanggal kalender dan 10+5 kolom/bulan valid | PASS |
| Audit Fase 1 | 42 hash ZIP input cocok dengan `audit_final/dataset_freeze.json`; 11 arsip menit COI 2007–2017 tersedia; hash artefak kode dan output beku yang tercatat juga cocok | PASS |
| D1 — kesiapan input | Tiga berkas X Februari yang diperlukan tersedia masing-masing satu; GFZ 132 bulan tersedia | PASS |
| D2 — kesiapan input | WDC per jam dan 11 ZIP menit COI beku tersedia; belum dibandingkan | PASS |
| Replikasi Sq IQD — kesiapan input | 36 DAT Sq/SD = 12 bulan × 3 komponen; 11 tahun per komponen/bulan = 396 seri tahunan; GFZ lengkap | PASS |

## Inventaris format, dimensi, satuan, dan missing value

- Mendeley: 684 DAT bertab. Keluarga `IQD Sq and SD` berisi 36 berkas, masing-masing 24 baris data × 37 kolom (`h`, 11 tahun dan `y.all` untuk masing-masing Sq, SD, dan S). Keluarga `PCA modes` berisi 648 DAT dengan bentuk beragam yang dicatat per berkas di `mendeley_dat_inventory.csv`; 2.952 PNG ikut dipertahankan. Label `h`, `hour`, `day`, dan `y.YYYY` adalah indeks/kolom, bukan timestamp UTC eksplisit.
- Mendeley: token hilang `NA` berjumlah 693 pada 45 DAT PCA modes; tidak ditemukan token bukan numerik lain pada kolom nilai. Rentang angka desimal tercetak di kedua keluarga adalah 0–18 digit (0 berarti bilangan bulat tercetak). Inventaris mencatat minimum dan maksimum per berkas; ini belum menetapkan toleransi numerik. Tidak ada satuan fisik atau zona waktu yang tertanam dalam DAT. Protokol menyebut PC bersatuan sembarang dan EOF dalam nT; ini keterangan sumber, bukan metadata yang diverifikasi dari DAT.
- WDC: tiap HOR mempunyai tujuh kolom `DATE TIME DOY COIX COIY COIZ COIF`. `DATE/TIME` terbaca tiap HH:00:00.000; DOY cocok dengan kalender; stempel diperlakukan UTC menurut konvensi WDC. X/Y/Z/F adalah komponen intensitas nT menurut spesifikasi INTERMAGNET untuk XYZF: https://tech-man.intermagnet.org/latest/appendices/dataformats.html . Header HOR sendiri tidak menuliskan unit secara eksplisit.
- WDC: sentinel missing `99999.xx`/`88888.xx` terhitung X=1,414, Y=1,414, Z=1,414, F=5,659. Jumlah baris lengkap tidak berarti seluruh pengukuran valid. Detail bulanan ada di `wdc_hourly_inventory.csv`.
- GFZ: tiap tahun berisi 12 baris bulan dengan Q1–Q10 dan D1–D5. Sufiks hari yang ditemukan: ''=1523, '*'=390, 'K'=42, 'A'=25. Ini penanda katalog, bukan satuan fisik. Detail bulan tersedia di `gfz_day_inventory.csv`.

### Berkas kunci Februari untuk D1 (hanya dibaca)

| Berkas | Dimensi data | Desimal tercetak | NA |
|---|---:|---:|---:|
| `COI_X_Sq.SD.S_m02.dat` | 24 × 37 | 0–16 | 0 |
| `COI_X_meanField_m02.dat` | 28 × 12 | 0–2 | 0 |
| `COI_X_EOF1_m02.dat` | 28 × 12 | 13–18 | 0 |

`meanField` dan `EOF1` Februari memiliki 28 baris `day`, sedangkan WDC Februari 2008 mempunyai 29 hari. Perlakuan 29 Februari adalah keputusan analisis D1/D2 kemudian; G0 tidak mengisi atau membuang baris.

## Provenans dan reproduksibilitas

- Respons akhir unduhan: HTTP 200 pada 1 ZIP Mendeley, 11 ZIP WDC, dan 11 berkas GFZ; rincian per permintaan ada di `download_events.jsonl`.
- `input_manifest.csv` mencatat 3,702 berkas fisik: Phase2A_protocol=1, Mendeley_archive=1, Mendeley_extracted=3636, WDC_COI_hourly_archive=11, GFZ_IQD_IDD=11, Phase1_frozen_minute_archive=42. Setiap baris memiliki ukuran, SHA-256, URL sumber, versi, dan status. Tanggal unduh dari log HTTP dicatat untuk semua unduhan baru; anggota ekstraksi Mendeley mewarisi waktu unduh ZIP sumbernya.
- Arsip menit Fase 1 telah ada sebelum G0. Waktu **unduh asli** 42 arsip itu tidak tercatat dalam freeze, sehingga `downloaded_utc` sengaja kosong, bukan diisi dengan perkiraan. Waktu pembuatan freeze tercatat dalam `dataset_freeze.json`.
- Lingkungan: Python `3.12.6`, `Windows-11-10.0.26200-SP0`. Path interpreter dan versi paket disimpan di `python_environment.json`; SHA-256 parser juga direkam.
- Manifest mengarah ke `phase2a/raw/` tanpa menyalin data mentah ke berkas laporan. Untuk mengulang inventaris: `python phase2a/G0/g0_inventory.py`, lalu `python phase2a/G0/g0_report.py`. Keduanya tidak mengubah data mentah atau audit Fase 1.

## Kegagalan akuisisi yang pulih

Pada upaya pertama GFZ, server mengirim isi berkompresi gzip. `Content-Length` menghitung byte terkompresi, sedangkan klien menghitung byte setelah dekompresi. Pemeriksaan panjang awal menghasilkan pesan asli berikut; unduhan kemudian diulang dan sebelas berkas ASCII tervalidasi. Log asli tetap ada di `download_events.jsonl` dan `gfz_retry.log`.

| Tahun | Pesan error asli |
|---:|---|
| 2007 | `OSError: Content-Length 803, diterima 1658 byte` |
| 2008 | `OSError: Content-Length 810, diterima 1658 byte` |
| 2009 | `OSError: Content-Length 810, diterima 1658 byte` |
| 2010 | `OSError: Content-Length 799, diterima 1658 byte` |
| 2011 | `OSError: Content-Length 803, diterima 1658 byte` |
| 2012 | `OSError: Content-Length 807, diterima 1658 byte` |
| 2013 | `OSError: Content-Length 803, diterima 1658 byte` |
| 2014 | `OSError: Content-Length 824, diterima 1658 byte` |
| 2015 | `OSError: Content-Length 804, diterima 1658 byte` |
| 2016 | `OSError: Content-Length 799, diterima 1658 byte` |
| 2017 | `OSError: Content-Length 803, diterima 1658 byte` |

## Persoalan sebelum tahap berikutnya

1. Tetapkan aturan penanganan missing yang mempertahankan gap WDC dan `NA` Mendeley; jangan menafsirkan baris yang ada sebagai data valid. Verifikasi bahwa analisis selanjutnya hanya memakai komponen yang dibutuhkan dan tidak mensyaratkan F lengkap.
2. Saat D1/D2 nanti, tetapkan penanganan 29 Februari 2008 dan konvensi HH:00 versus HH:30 sesuai protokol sebelum perbandingan numerik. G0 tidak memutuskan keduanya.
3. Catat sumber satuan Mendeley dan toleransi berdasarkan resolusi cetak pada berkas yang benar sebelum perbandingan pertama. DAT tidak menyimpan metadata satuan atau zona waktu.
4. Review versi administratif `G0-registration-1` dan hash protokol. Setiap perubahan aturan setelah hasil terlihat memerlukan versi protokol baru sesuai dokumen acuan.

**Keputusan akhir: G0 CONDITIONAL PASS.** Semua input pokok tersedia dan integritasnya lolos. Status bersyarat mencerminkan gap nilai, keterbatasan metadata berkas Mendeley, serta keputusan pemetaan waktu/hari yang memang ditunda ke tahap berikutnya. Pekerjaan berhenti pada G0 untuk review.
