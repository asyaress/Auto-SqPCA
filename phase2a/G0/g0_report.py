"""Render a Gate G0 report from the read-only inventory and acquisition log."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

G0 = Path(__file__).resolve().parent
ROOT = G0.parents[1]
v = json.loads((G0 / "G0_validation.json").read_text(encoding="utf-8"))
dat = list(csv.DictReader((G0 / "mendeley_dat_inventory.csv").open(encoding="utf-8", newline="")))
manifest = list(csv.DictReader((G0 / "input_manifest.csv").open(encoding="utf-8", newline="")))
source_counts = Counter(x["source"] for x in manifest)
feb = [x for x in dat if x["relative_path"].endswith((
    "COI_X_meanField_m02.dat", "COI_X_EOF1_m02.dat", "COI_X_Sq.SD.S_m02.dat"))]

lines = [
    "# Gate G0 — Persiapan dan verifikasi input Fase 2A",
    "",
    f"**Keputusan: {v['decision']}.** Pemeriksaan dilakukan {v['created_utc']}.",
    "Cakupan hanya akuisisi, pemeriksaan integritas, dan inventaris berkas. Tidak ada D1, D2, PCA, DTW, DIFI, atau klasifikasi PC yang dijalankan.",
    "",
    "## Acuan dan batas data",
    "",
    f"- Protokol lokal: `{v['protocol']['local_version']}`, tanggal dokumen {v['protocol']['document_date']}; SHA-256 DOCX `{v['protocol']['document_sha256']}`. Nomor versi ini didaftarkan pada G0 karena DOCX asal tidak memuat nomor versi eksplisit.",
    "- Semua penulisan G0 berada di `phase2a/G0/`; unduhan mentah berada di `phase2a/raw/`. Berkas audit Fase 1 yang dibekukan hanya dibaca.",
    "- Mendeley: DOI `10.17632/jcmdrm5f5x.1`, versi 1, lisensi CC BY 4.0, rilis 2 Maret 2021. URL arsip stabil: https://data.mendeley.com/public-api/zip/jcmdrm5f5x/download/1 ; halaman: https://data.mendeley.com/datasets/jcmdrm5f5x/1 .",
    "- WDC Edinburgh: `https://wdcapi.bgs.ac.uk/data/zipped-data/hour/COI?years=YYYY&file_format=iaga&orientation=XYZF`; 11 permintaan tahunan 2007–2017. Panduan: https://wdc.bgs.ac.uk/how-to-guide .",
    "- GFZ: `https://datapub.gfz-potsdam.de/download/10.5880.Kp.0001/Quiet_Disturbed_Days/QD_daysYYYY.txt`; DOI `10.5880/Kp.0001`. Indeks: https://datapub.gfz-potsdam.de/download/10.5880.Kp.0001/Quiet_Disturbed_Days/ .",
    "",
    "## Hasil pemeriksaan",
    "",
    "| Pemeriksaan | Bukti | Status |",
    "|---|---|---|",
    f"| Mendeley v1 | ZIP {v['mendeley']['zip_bytes']:,} byte; {v['mendeley']['zip_members']:,} anggota; CRC ZIP dan CRC semua hasil ekstraksi cocok; {v['mendeley']['dat_files']} DAT dan {v['mendeley']['png_files']:,} PNG; nama dan hierarki asli dipertahankan | {'PASS' if v['checks']['mendeley_integrity']['pass'] else 'FAIL'} |",
    f"| WDC COI per jam | 11 ZIP, {v['wdc_hourly']['monthly_hor_files']} HOR bulanan, {v['wdc_hourly']['hourly_rows']:,}/{v['wdc_hourly']['expected_hourly_rows']:,} timestamp unik HH:00; 29 Februari 2008 = {v['wdc_hourly']['leap_day_2008_hours']} jam; CRC dan header IAGA-2002/XYZF cocok | {'PASS' if v['checks']['wdc_hourly_integrity']['pass'] else 'FAIL'} |",
    f"| GFZ IQD/IDD | 11 ASCII tahunan, {v['gfz']['months']} bulan, {v['gfz']['quiet_day_entries']:,} entri Q dan {v['gfz']['disturbed_day_entries']} entri D; tanggal kalender dan 10+5 kolom/bulan valid | {'PASS' if v['checks']['gfz_iqd_integrity']['pass'] else 'FAIL'} |",
    f"| Audit Fase 1 | {v['phase1']['frozen_input_archives_verified']} hash ZIP input cocok dengan `audit_final/dataset_freeze.json`; {v['phase1']['coi_minute_archives_2007_2017']} arsip menit COI 2007–2017 tersedia; hash artefak kode dan output beku yang tercatat juga cocok | {'PASS' if v['checks']['phase1_freeze_unchanged']['pass'] else 'FAIL'} |",
    f"| D1 — kesiapan input | Tiga berkas X Februari yang diperlukan tersedia masing-masing satu; GFZ 132 bulan tersedia | {'PASS' if v['checks']['d1_inputs_available']['pass'] else 'FAIL'} |",
    f"| D2 — kesiapan input | WDC per jam dan 11 ZIP menit COI beku tersedia; belum dibandingkan | {'PASS' if v['checks']['d2_inputs_available']['pass'] else 'FAIL'} |",
    f"| Replikasi Sq IQD — kesiapan input | 36 DAT Sq/SD = 12 bulan × 3 komponen; 11 tahun per komponen/bulan = {v['mendeley']['iqd_series_annual']} seri tahunan; GFZ lengkap | {'PASS' if v['checks']['sq_iqd_inputs_available']['pass'] else 'FAIL'} |",
    "",
    "## Inventaris format, dimensi, satuan, dan missing value",
    "",
    "- Mendeley: 684 DAT bertab. Keluarga `IQD Sq and SD` berisi 36 berkas, masing-masing 24 baris data × 37 kolom (`h`, 11 tahun dan `y.all` untuk masing-masing Sq, SD, dan S). Keluarga `PCA modes` berisi 648 DAT dengan bentuk beragam yang dicatat per berkas di `mendeley_dat_inventory.csv`; 2.952 PNG ikut dipertahankan. Label `h`, `hour`, `day`, dan `y.YYYY` adalah indeks/kolom, bukan timestamp UTC eksplisit.",
    f"- Mendeley: token hilang `NA` berjumlah {v['mendeley']['missing_token_counts'].get('NA', 0)} pada {sum(int(x['missing_cells']) > 0 for x in dat)} DAT PCA modes; tidak ditemukan token bukan numerik lain pada kolom nilai. Rentang angka desimal tercetak di kedua keluarga adalah 0–18 digit (0 berarti bilangan bulat tercetak). Inventaris mencatat minimum dan maksimum per berkas; ini belum menetapkan toleransi numerik. Tidak ada satuan fisik atau zona waktu yang tertanam dalam DAT. Protokol menyebut PC bersatuan sembarang dan EOF dalam nT; ini keterangan sumber, bukan metadata yang diverifikasi dari DAT.",
    "- WDC: tiap HOR mempunyai tujuh kolom `DATE TIME DOY COIX COIY COIZ COIF`. `DATE/TIME` terbaca tiap HH:00:00.000; DOY cocok dengan kalender; stempel diperlakukan UTC menurut konvensi WDC. X/Y/Z/F adalah komponen intensitas nT menurut spesifikasi INTERMAGNET untuk XYZF: https://tech-man.intermagnet.org/latest/appendices/dataformats.html . Header HOR sendiri tidak menuliskan unit secara eksplisit.",
    f"- WDC: sentinel missing `99999.xx`/`88888.xx` terhitung X={v['wdc_hourly']['missing_by_component'].get('X', 0):,}, Y={v['wdc_hourly']['missing_by_component'].get('Y', 0):,}, Z={v['wdc_hourly']['missing_by_component'].get('Z', 0):,}, F={v['wdc_hourly']['missing_by_component'].get('F', 0):,}. Jumlah baris lengkap tidak berarti seluruh pengukuran valid. Detail bulanan ada di `wdc_hourly_inventory.csv`.",
    f"- GFZ: tiap tahun berisi 12 baris bulan dengan Q1–Q10 dan D1–D5. Sufiks hari yang ditemukan: {', '.join((repr(k) + '=' + str(n)) for k, n in v['gfz']['day_suffix_counts'].items())}. Ini penanda katalog, bukan satuan fisik. Detail bulan tersedia di `gfz_day_inventory.csv`.",
    "",
    "### Berkas kunci Februari untuk D1 (hanya dibaca)",
    "",
    "| Berkas | Dimensi data | Desimal tercetak | NA |",
    "|---|---:|---:|---:|",
]
for item in sorted(feb, key=lambda x: x["relative_path"]):
    lines.append(f"| `{Path(item['relative_path']).name}` | {item['data_rows']} × {item['columns']} | {item['printed_decimals_min']}–{item['printed_decimals_max']} | {item['missing_cells']} |")
lines += [
    "",
    "`meanField` dan `EOF1` Februari memiliki 28 baris `day`, sedangkan WDC Februari 2008 mempunyai 29 hari. Perlakuan 29 Februari adalah keputusan analisis D1/D2 kemudian; G0 tidak mengisi atau membuang baris.",
    "",
    "## Provenans dan reproduksibilitas",
    "",
    "- Respons akhir unduhan: HTTP 200 pada 1 ZIP Mendeley, 11 ZIP WDC, dan 11 berkas GFZ; rincian per permintaan ada di `download_events.jsonl`.",
    f"- `input_manifest.csv` mencatat {v['manifest_rows']:,} berkas fisik: " + ", ".join(f"{name}={count}" for name, count in source_counts.items()) + ". Setiap baris memiliki ukuran, SHA-256, URL sumber, versi, dan status. Tanggal unduh dari log HTTP dicatat untuk semua unduhan baru; anggota ekstraksi Mendeley mewarisi waktu unduh ZIP sumbernya.",
    "- Arsip menit Fase 1 telah ada sebelum G0. Waktu **unduh asli** 42 arsip itu tidak tercatat dalam freeze, sehingga `downloaded_utc` sengaja kosong, bukan diisi dengan perkiraan. Waktu pembuatan freeze tercatat dalam `dataset_freeze.json`.",
    f"- Lingkungan: Python `{v['environment']['python'].split()[0]}`, `{v['environment']['platform']}`. Path interpreter dan versi paket disimpan di `python_environment.json`; SHA-256 parser juga direkam.",
    "- Manifest mengarah ke `phase2a/raw/` tanpa menyalin data mentah ke berkas laporan. Untuk mengulang inventaris: `python phase2a/G0/g0_inventory.py`, lalu `python phase2a/G0/g0_report.py`. Keduanya tidak mengubah data mentah atau audit Fase 1.",
    "",
    "## Kegagalan akuisisi yang pulih",
    "",
    "Pada upaya pertama GFZ, server mengirim isi berkompresi gzip. `Content-Length` menghitung byte terkompresi, sedangkan klien menghitung byte setelah dekompresi. Pemeriksaan panjang awal menghasilkan pesan asli berikut; unduhan kemudian diulang dan sebelas berkas ASCII tervalidasi. Log asli tetap ada di `download_events.jsonl` dan `gfz_retry.log`.",
    "",
    "| Tahun | Pesan error asli |",
    "|---:|---|",
]
for failed in v["failed_download_attempts_recovered"]:
    lines.append(f"| {failed['year']} | `{failed['error_original']}` |")
lines += [
    "",
    "## Persoalan sebelum tahap berikutnya",
    "",
    "1. Tetapkan aturan penanganan missing yang mempertahankan gap WDC dan `NA` Mendeley; jangan menafsirkan baris yang ada sebagai data valid. Verifikasi bahwa analisis selanjutnya hanya memakai komponen yang dibutuhkan dan tidak mensyaratkan F lengkap.",
    "2. Saat D1/D2 nanti, tetapkan penanganan 29 Februari 2008 dan konvensi HH:00 versus HH:30 sesuai protokol sebelum perbandingan numerik. G0 tidak memutuskan keduanya.",
    "3. Catat sumber satuan Mendeley dan toleransi berdasarkan resolusi cetak pada berkas yang benar sebelum perbandingan pertama. DAT tidak menyimpan metadata satuan atau zona waktu.",
    "4. Review versi administratif `G0-registration-1` dan hash protokol. Setiap perubahan aturan setelah hasil terlihat memerlukan versi protokol baru sesuai dokumen acuan.",
    "",
    f"**Keputusan akhir: {v['decision']}.** Semua input pokok tersedia dan integritasnya lolos. Status bersyarat mencerminkan gap nilai, keterbatasan metadata berkas Mendeley, serta keputusan pemetaan waktu/hari yang memang ditunda ke tahap berikutnya. Pekerjaan berhenti pada G0 untuk review.",
    "",
]
(G0 / "G0_report.md").write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {G0 / 'G0_report.md'} ({len(lines)} lines)")
