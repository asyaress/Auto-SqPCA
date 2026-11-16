# D2c — Validasi kerangka tabular base WDC

**Status: D2c TIDAK DIJALANKAN, kondisi henti 0a `WDC_FORMAT_INCONSISTENT`.** Uji prasyarat wajib gagal: 267,475 dari 375,824 jam–elemen valid berpasangan (**71.170%**) berbeda >0,1 nT antara `base × 100 + tabular value` WDC fixed-width dan data hourly IAGA-2002 yang dipakai D2/D2b. Ambang henti amandemen ialah >0,1% jam. Nilai ini jauh melewatinya; tidak ada `d′`, klasifikasi D2c, atau H-a D2c yang dihitung.

## Sumber dan akuisisi

Sumber resmi WDC Edinburgh: [https://wdcapi.bgs.ac.uk/data/zipped-data/hour/COI?start_dt=2007-01-01&end_dt=2018-01-01&file_format=wdc&orientation=XYZF](https://wdcapi.bgs.ac.uk/data/zipped-data/hour/COI?start_dt=2007-01-01&end_dt=2018-01-01&file_format=wdc&orientation=XYZF) (`file_format=wdc`, `orientation=XYZF`, 2007-01-01 hingga sebelum 2018-01-01). HTTP 200, 568,166 byte, SHA-256 `5fa0161e935fa759d133f733ba769dda9f000ce1e45bc1e3a49ec565a0d0c9d3`, 11 anggota tahunan; CRC ZIP lulus. Respons pertama dengan `years=2007-2017` hanya mengandung 2007 dan 2017 karena parameter itu diperlakukan sebagai daftar dua tahun. Respons pertama dipertahankan, SHA-256 `b7549f1f7de7f32a3105c7337440f0ab38c6f0ef95c4d140894acdfb2fcd7861`. Koreksi menggunakan batas tanggal eksplisit; kedua URL, waktu, status, dan hash ada di JSON akuisisi. Tidak ada unduhan setelah koreksi.

## Parser dan hasil validasi silang

Parser membaca 16.072 baris harian (4 elemen ×4.018 hari), masing-masing 120 karakter: COI, tanggal, elemen, abad, base I4 pada kolom 17–20, 24 tabular value I4 pada kolom 21–116, dan rata-rata harian pada 117–120. Token `9999` diperlakukan missing. Semua tanggal/elemen unik dan lengkap. CSV per jam berisi 385,728 baris; 375,824 berpasangan valid. Status missing: IAGA saja 4,248, format WDC saja 3, keduanya 5,653. Median |selisih| = 0.300 nT, maksimum = 820.400 nT. Format I4 mencetak nT bulat, sedangkan IAGA mencetak desimal; hal ini dapat menjelaskan sebagian selisih sub-nT, tetapi **tidak membenarkan mengubah ambang** dan tidak menjelaskan otomatis maksimum tersebut.

| Elemen | Jam valid berpasangan | >0,1 nT | Persentase |
|:---:|---:|---:|---:|
| X | 95018 | 66644 | 70.138% |
| Y | 95018 | 66388 | 69.869% |
| Z | 95018 | 66603 | 70.095% |
| F | 90770 | 67840 | 74.738% |

Data silang per jam, termasuk contoh ketidakcocokan awal dan hash sumber, ada di `S7C_wdc_crosscheck.csv` serta `S7C_wdc_crosscheck_summary.json`. Validasi dilakukan pada XYZF; X/Y/Z sendiri masing-masing sekitar 70% di atas 0,1 nT, sehingga F bukan penyebab tunggal keputusan henti.

## Tabular base dari metadata

Base tidak dipasang dari konstanta temuan reviewer. Tabel base per elemen × tahun × bulan × nilai base beserta jumlah hari ada di `S7C_wdc_base_table.csv`. Tidak ada bulan yang memakai lebih dari satu base untuk elemen yang sama, tetapi ada perubahan antarbulan/tahun:

| Elemen | Base unik 2007–2017 | Konstan seluruh periode | Bulan saat base berubah dari bulan sebelumnya |
|:---:|---|:---:|---|
| X | 203, 204, 205, 206 | tidak | 2008-01 (203→204), 2011-01 (204→205), 2015-01 (205→206) |
| Y | -66, -65, -64, -63, -62, -61, -60 | tidak | 2009-01 (-66→-65), 2011-01 (-65→-64), 2012-01 (-64→-63), 2014-01 (-63→-62), 2015-01 (-62→-61), 2017-01 (-61→-60) |
| Z | 312 | ya | tidak ada |
| F | 393, 394 | tidak | 2016-01 (393→394) |

## Penghentian

Menurut A1 dan baris 0a G1 registration-3, transformasi tabular base tidak boleh dipakai untuk D2c setelah validasi silang gagal. `D2c_comparison.csv` hanya memiliki header, dan `D2c_summary.json` menyatakan `NOT_RUN_WDC_FORMAT_INCONSISTENT`. Tidak ada bulan `REVISION_LIKE` atau pengecualian D2c yang dapat diputuskan. Hasil D2b (10.953 selisih mentah dan G1 HOLD registration-2) tetap utuh. Audit forensik ditutup di titik henti ini; tidak ada D2d.
