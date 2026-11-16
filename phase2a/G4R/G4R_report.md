# G4-R — kesesuaian keputusan pemilihan PC

**Label D-agreement: D-AGREE.** P-own dan P-pub memberi keputusan sama pada 2661/2667 kandidat dari 381 matriks eligible. Enam ketidaksepakatan berada di zona sensitif; **nol** di luar zona. Sebanyak 376/381 matriks sepakat pada ketujuh kandidat. Ini kesesuaian keputusan aturan yang didaftarkan dalam G4R-v1, bukan replikasi tabel klasifikasi X berbasis DIFI3 + DTW. Label struktur G2-R **S-DEVIATE** dan G1 registration-2/3 **HOLD** tetap.

## Integritas dan aturan

Protokol SHA-256 `423e27bb28c326f0ef56d92e89f6b7764523b3d619352f8c98d0296f346f415e`. Preflight memverifikasi 3,702 entri manifest G0, 119 hash historis G0–S7-C, konfigurasi V1 G2-R SHA-256 `25676d831262eef44857d6bd9b14f4aba72909ec4968760d53406f906976a320`, kode PCA beku, dan paket G2-R. 146 hash artefak beku cocok hingga akhir G4-R. Tidak ada sumber atau artefak lama ditimpa.

Aturan: |r| Pearson ≥0,45 dan p<0,05; 1.000 surrogate acak-fase acuan dengan seed 20261113, DC/Nyquist tetap, p=(1+jumlah surrogate ≥|r| observasi)/1.001. Zona sensitif ialah |r| dalam ±0,02 dari 0,45 atau p dalam ±0,01 dari 0,05 pada salah satu pipeline. Kombinasi PC memakai bobot rata-rata EOF dari masing-masing pipeline. Enam uji aturan lulus sebelum data nyata; uji konsistensi sintetis 200/200 di luar zona (100.0%).

## G3-R deskriptif

V1 beku dijalankan pada 432 target: 396 tahunan dan 36 gabungan. Status eksklusif: 381 eligible, 6 suspect yang dapat dihitung, 12 excluded, 33 unresolved missing. Pada 381 eligible, 62 memenuhi galat Frobenius ≤1% dan 56 memenuhi seluruh metrik struktur G2-R. Angka ini **deskriptif tanpa label struktur baru**. Detail setiap matriks ada di `G3R_structure_metrics.csv`; target yang tidak dapat dihitung tidak diganti.

## Acuan Sq IQD dan keputusan

Semua 432 acuan Sq_IQD sendiri tersedia. Untuk setiap IQD, rata-rata jam malam indeks 0,1,2,3,23 UTC dikurangkan dari 24 nilai per jam, lalu lima hari Q1–Q5 GFZ dirata-ratakan. Acuan gabungan merata-ratakan 11 kurva tahunan (55 IQD). Februari 2016 memakai Q1–Q5 **22,28,27,21,29**; status D1-IQD tetap **PROVISIONAL**. Offset antara acuan sendiri dan Mendeley tidak mengubah |r|.

Penyebut target: 432; excluded 12; suspect dihitung terpisah 6; unresolved 33; eligible 381. Bendera DEVELOPMENT_SEEN ada pada 303 target dan tumpang tindih kategori status; 266 di antaranya eligible. Strata eligible yang belum terlihat berisi 115 matriks dengan 799 keputusan kandidat sama dan 6 selisih dalam zona; ini pemeriksaan diagnostik, bukan klaim prospektif baru. Kasus suspect dan Februari dilaporkan terpisah dalam `G4R_result.json`.

| Komponen | PC1 κ | PC2 κ | PC3 κ |
|:---:|---:|---:|---:|
| X | 1.0000 | 0.9544 | 1.0000 |
| Y | tidak terdefinisi† | tidak terdefinisi† | tidak terdefinisi† |
| Z | tidak terdefinisi† | tidak terdefinisi† | tidak terdefinisi† |

† κ tidak terdefinisi bila kedua marginal keputusan konstan (P_o=P_e=1), meskipun kesepakatan observasi 100%; tidak diberi nilai 1 secara artifisial. Rincian n dan P_o/P_e ada di `G4R_result.json`.

Sanity CR4 pada penyebut eligible:

| Komponen | P-own ≥0,88 | P-pub ≥0,88 |
|:---:|---:|---:|
| Y | 120/121 (99.17%) | 120/121 (99.17%) |
| Z | 128/131 (97.71%) | 128/131 (97.71%) |

Keduanya melewati batas berhenti 90%; angka lokal bukan 100% yang dilaporkan artikel. `G4R_agreement.csv` memuat keputusan, r, p, dan zona untuk seluruh kandidat empat pipeline. Perbandingan diagnostik mempunyai 6 selisih P-own/P-mixA, 2 P-pub/P-mixA, dan 6 P-pub/P-mixB pada penyebut eligible. Daftar ketidaksepakatan utama di luar zona kosong (`G4R_disagreements_outside_zone.csv`).

## Batas klaim

Penyebut utama bersifat retrospektif dan memuat seri DEVELOPMENT_SEEN yang ditandai; hasil tidak diklaim prospektif. Enam ketidaksepakatan terletak di dekat ambang, dan hasil p bergantung pada pilihan 1.000 surrogate/seed yang dibekukan di protokol. Y Februari tetap excluded; beberapa matriks dengan jam batas bulan kosong tidak dihitung; keluaran X tidak menyamai kategori DIFI3 + DTW artikel. Hipotesis review bahwa Sq lemah menjelaskan galat relatif tidak diuji. Langkah berikutnya adalah Fase 3 menurut protokol terpisah.
