# U6 — pemeriksaan fakta

Label: **EXPLORATORY_POST_HOC**.

## 29 Februari

**Tidak dibuang.** `auto_sqpca/localtime.py:20–35` fungsi `month_matrix` memakai `calendar.monthrange(year, month)[1]` lalu membentuk matriks `(24, N, 3)` tanpa pengecualian 29 Februari. `f3_inventory.py:67` dan `f3b_e3b_prep.py:50` memanggil fungsi tersebut; `f3_e1.py:104`, `f3b_ssb.py:73–94`, dan `f3b_e3.py:84` membaca cache hasilnya tanpa membuang kolom terakhir Februari. Ini bertentangan dengan pernyataan di naskah MethodsX yang menyebut 29 Februari dibuang dari matriks.

| Stasiun | Tahun | Dimensi cache Februari |
|---|---:|---|
| COI | 2008 | (24, 29, 3) |
| COI | 2012 | (24, 29, 3) |
| COI | 2016 | (24, 29, 3) |
| GUA | 2016 | (24, 29, 3) |
| HUA | 2016 | (24, 29, 3) |
| KDU | 2016 | (24, 29, 3) |
| MBO | 2016 | (24, 29, 3) |
| TTB | 2016 | (24, 29, 3) |

Cache E2 **holdout** Februari kabisat (`residual_nT`):

| Stasiun | Tahun | Dimensi cache E2 |
|---|---:|---|
| COI | 2016 | (24, 29, 3) |
| GUA | 2016 | (24, 29, 3) |

GFZ Februari 2016 Q1–Q5 yang dibaca dari `phase2a/raw/gfz/QD_days2016.txt`: **[22, 28, 27, 21, 29]**. Karena `auto_sqpca/selection.py` fungsi `sq_iqd` memakai indeks `quiet_days − 1` pada matriks 29 kolom, hari 29 juga dapat dipakai dalam referensi IQD Fase 3.

## Jam tepi deret UTC

Deret tahunan disambung per stasiun sebelum pembentukan bulan lokal (`f3_inventory.py`, `f3b_e3b_prep.py`). Karena itu jam yang berada di luar deret yang dimuat hanya muncul pada tepi awal/akhir keseluruhan rentang tahun stasiun, bukan pada setiap bulan. Angka berikut adalah jam yang hilang *karena batas deret*, terpisah dari missing value observasi.

| Stasiun | Rentang tahun dimuat | Pergeseran LT (jam) | Awal bulan lokal: kisaran jam di luar deret | Akhir bulan lokal: kisaran jam di luar deret | Tumpang tindih hari GFZ UTC vs hari lokal (jam/hari) |
|---|---|---:|---:|---:|---:|
| COI | 2007–2017 | -1 | 0–0 | 0–1 | 23 |
| GUA | 2014–2018 | +10 | 0–10 | 0–0 | 14 |
| HUA | 2014–2018 | -5 | 0–0 | 0–5 | 19 |
| KDU | 2014–2018 | +9 | 0–9 | 0–0 | 15 |
| MBO | 2014–2018 | -1 | 0–0 | 0–1 | 23 |
| PLR | 2017–2017 | +7 | 0–7 | 0–0 | 17 |
| TTB | 2014–2018 | -3 | 0–0 | 0–3 | 21 |
| TUN | 2017–2017 | +7 | 0–7 | 0–0 | 17 |

Tumpang tindih dihitung sebagai panjang irisan satu hari UTC GFZ (00:00–24:00 UTC) dengan hari lokal bertanggal sama setelah pergeseran integer `round(longitude/15)`; rumusnya `24 − |ΔLT|` jam. Ini kesesuaian waktu, bukan bukti kelengkapan data pada jam tersebut.
