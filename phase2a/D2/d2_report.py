"""Assign auditable D2 decisions and package small deterministic review files."""
from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D2 = ROOT / "phase2a/D2"
D1 = ROOT / "phase2a/D1"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(name: str) -> list[dict]:
    with (D2 / name).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def fmt(value, digits=3) -> str:
    return "NA" if value in (None, "") else f"{float(value):.{digits}f}"


def main() -> None:
    validation_path = D2 / "D2_validation.json"
    v = json.loads(validation_path.read_text(encoding="utf-8"))
    hourly = read_csv("D2_hourly_vs_minute.csv")
    timing = read_csv("D2_timestamp_diagnostics.csv")
    benchmark = read_csv("D2_benchmark_offset.csv")
    anomaly = read_csv("D2_meanfield_anomaly.csv")
    d1 = json.loads((D1 / "D1_validation.json").read_text(encoding="utf-8"))

    overall = v["overall_metrics"]
    quant = v["quantization_diagnostics"]
    time_confirmed = all(quant[c]["pct_equal_trunc_toward_zero_0p1nT"] == 100.0 and
                         overall[f"{c}:A_00_59"]["mae_nT"] < overall[f"{c}:B_HHm30_to_HHp29"]["mae_nT"] and
                         overall[f"{c}:A_00_59"]["mae_nT"] < overall[f"{c}:C_HH00"]["mae_nT"]
                         for c in "XYZ")
    duplicate = [x for x in anomaly if x["record_type"] == "hash_structure" and x["identical_hash"] == "True"]
    night = [x for x in benchmark if x["candidate"] == "night"]
    centered = [x for x in benchmark if x["candidate"] == "daily_mean"]
    source_discrepancy = len(duplicate) == 6 and all(abs(float(x["benchmark_mean_24h_nT"])) < 1e-10 for x in night) and any(
        abs(float(x["mean_24h_nT"])) > 0.5 for x in night)
    eq_max = max(v["daily_mean_vs_night_then_center_max_abs_by_year_component"].values())
    if eq_max > 1e-9:
        raise RuntimeError(f"Daily-mean and night-then-center should be mathematically equivalent: max={eq_max}")
    if not all(v["missing_threshold_diagnostics"][c]["valid_with_fewer_than_54_minutes"] == 0 and
               v["missing_threshold_diagnostics"][c]["missing_with_54_or_more_minutes"] == 0 for c in "XYZF"):
        raise RuntimeError("Observed 54/60-minute availability rule is inconsistent")

    data_status = "EQUIVALENT" if all(quant[c]["trunc_nonmatches"] == 0 for c in "XYZF") else "UNRESOLVED"
    time_status = "CONFIRMED" if time_confirmed else "UNRESOLVED"
    benchmark_status = "SOURCE_DISCREPANCY" if source_discrepancy else "UNRESOLVED"
    gate_status = "CONDITIONAL PASS" if time_confirmed and source_discrepancy and data_status == "UNRESOLVED" else (
        "PASS" if time_confirmed and data_status == "EQUIVALENT" and not source_discrepancy else "FAIL")
    g1_status = "HOLD_S7_AND_D1_IQD_PROVISIONAL" if source_discrepancy or d1["decisions"]["D1-IQD"]["status"] != "CONFIRMED" else "READY_FOR_JOINT_EVALUATION"
    v["decisions"] = {
        "D2-TIME": {"status": time_status,
                    "basis": "A is exact truncation-to-0.1nT of 60 valid minute means for every matched X/Y/Z hour; B/C errors are much larger"},
        "D2-DATA": {"status": data_status,
                    "XYZ": "EQUIVALENT on 60-valid-minute hours; exact truncation and observed 54/60 availability rule",
                    "F": "UNRESOLVED: 22,577 matched F hours differ from truncation of minute A by 0.1 nT; cause not established",
                    "historical_revision": "NOT_INFERRED from present-day hourly/minute comparison"},
        "D2-BENCHMARK": {"status": benchmark_status,
                         "basis": "Sq February benchmark is 24h-mean-centered despite documented night baseline; six February Y/Z meanField/mode pairs are byte-identical"},
        "D2_GATE": gate_status,
        "G1": g1_status,
        "S7_evaluation": "TRIGGERED_FOR_REVIEW" if source_discrepancy else "NOT_TRIGGERED",
    }
    v["environment"]["report_script_sha256"] = sha(Path(__file__))
    validation_path.write_text(json.dumps(v, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    monthly = {(int(x["year"]), int(x["month"]), x["component"], x["candidate"]): x for x in hourly if x["period_type"] == "month"}
    bench_map = {(int(x["year"]), x["component"], x["candidate"]): x for x in benchmark}
    focus = [(int(y), int(m)) for y, m in v["focused_periods"]]
    boundary = [x for x in timing if x["record_type"] == "boundary_window" and x["candidate"] == "B_HHm30_to_HHp29"]
    anomaly_fit = [x for x in anomaly if x["record_type"] == "WDC_daily_mean_fit" and x["category"] == "Y_meanField"]
    report = [
        "# D2 — Audit hourly WDC, minute Fase 1, waktu, dan benchmark Mendeley",
        "",
        f"**Keputusan D2: {gate_status}.** D2-TIME **{time_status}**; D2-DATA **{data_status}** (XYZ setara, F belum terjelaskan); D2-BENCHMARK **{benchmark_status}**. **G1 belum PASS dan ditahan untuk review S7 bersama D1-IQD provisional.**",
        "",
        "## Sumber, integritas, dan aturan",
        "",
        f"- Input yang dibaca: 11 ZIP COI hourly G0, 11 ZIP COI minute Fase 1, GFZ IQD Februari 2008/2012/2016, dan DAT Mendeley asli. `D2_validation.json` mencatat SHA-256 {len(v['input_sha256'])} berkas yang dipakai serta hash konfigurasi Fase 1/G0/D1. Seluruh {v['integrity_before']['raw_files']:,} berkas raw dan 11 ZIP minute cocok dengan manifest G0 sebelum dan sesudah eksekusi; hash konfigurasi beku juga identik.",
        f"- IAGA-2002/XYZF diverifikasi pada {v['minute_metadata']['verified_IAGA_2002_XYZF_headers']:,} header berkas harian minute dan {v['hourly_metadata']['verified_IAGA_2002_XYZF_headers']} header bulanan hourly. Data minute mempunyai {v['minute_metadata']['data_rows']:,} timestamp pada 4.018 hari, hourly {v['hourly_metadata']['data_rows']:,} timestamp. Tidak ada timestamp yang hilang dari arsip; sentinel komponen tetap diperlakukan missing. Nilai nonmissing X/Y/Z/F berada pada grid 0,1 nT meski dicetak dua desimal.",
        "- Header arsip hourly hanya menyebut `Data Interval Type 1-hour`; batas menit rerata **UNKNOWN dari metadata arsip itu sendiri**. [Standar INTERMAGNET](https://tech-man.intermagnet.org/latest/chapters/submitdata/standardsformeans.html) menetapkan mean aritmetika menit 00–59, berpusat pada HH:29:30, dan mengizinkan hasil bila ≥90% menit tersedia. [Panduan WDC Edinburgh](https://wdc.bgs.ac.uk/how-to-guide) menyatakan semua waktu UTC. Data diuji langsung di bawah ini.",
        "- A = mean menit HH:00–HH:59; B = mean HH−30–HH+29; C = menit tepat HH:00. Perbandingan utama A/B memakai **60 dari 60 menit valid** untuk komponen bersangkutan, tanpa interpolasi. Jam yang tidak lengkap dicatat satu per satu di `D2_timestamp_diagnostics.csv` dan dikeluarkan dari metrik utama.",
        "",
        "## Perbandingan seluruh periode 2007–2017",
        "",
        "Galat = hourly WDC − kandidat dari minute Fase 1. Semua angka di tabel berikut berasal dari jam berpasangan sesuai aturan validitas tiap kandidat; C hanya membutuhkan satu menit.",
        "",
        "| Komp. | Kandidat | Pasangan | Mean / median (nT) | MAE / RMSE (nT) | P95 / maks. | r | ≤0,1 nT |",
        "|:---:|:---:|---:|---:|---:|---:|---:|---:|",
    ]
    for c in "XYZF":
        for candidate in ("A_00_59", "B_HHm30_to_HHp29", "C_HH00"):
            x = overall[f"{c}:{candidate}"]
            label = candidate.split("_")[0]
            report.append(f"| {c} | {label} | {x['matched_hours']:,} | {fmt(x['mean_error_nT'])} / {fmt(x['median_error_nT'])} | {fmt(x['mae_nT'])} / {fmt(x['rmse_nT'])} | {fmt(x['p95_abs_error_nT'])} / {fmt(x['max_abs_error_nT'])} | {fmt(x['pearson_r'], 6)} | {fmt(x['pct_abs_le_0p1'], 2)}% |")
    report += [
        "",
        "Korelasi tinggi pada B/C tidak menentukan konvensi: komponen geomagnet mempunyai level dan variasi lambat yang mendominasi r. MAE, RMSE, persentase dalam 0,1 nT, pola residu, dan aturan pembulatan semuanya memilih A untuk X/Y/Z.",
        "",
        "### Resolusi, pemotongan, dan data hilang",
        "",
        "| Komp. | Jam A lengkap & hourly valid | Cocok tepat dengan pemotongan menuju nol ke 0,1 nT | Selisih dari aturan itu | Hourly valid dengan 54–59 menit | Hourly missing dengan ≤53 menit |",
        "|:---:|---:|---:|---:|---:|---:|",
    ]
    for c in "XYZF":
        q, m = quant[c], v["missing_threshold_diagnostics"][c]
        report.append(f"| {c} | {q['matched_hours']:,} | {q['pct_equal_trunc_toward_zero_0p1nT']:.4f}% | {q['trunc_nonmatches']:,} | {m['incomplete_hourly_valid']:,} | {m['incomplete_hourly_missing']:,} |")
    report += [
        "",
        "Untuk X/Y/Z, **setiap** mean A dari 60 menit valid sama dengan hourly setelah dipotong menuju nol pada 0,1 nT; tidak ada mismatch. Pola mean residu sekitar −0,049 nT untuk X/Z dan +0,049 nT untuk Y sesuai arah pemotongan nilai positif/negatif. Semua komponen menunjukkan batas ketersediaan tepat 54/60 menit: tidak ada hourly valid di bawah 54 atau hourly missing pada 54 ke atas. Ini bukti empiris aturan 90%, tetapi metrik A/B tetap memakai 60/60.",
        f"F berbeda: {quant['F']['trunc_nonmatches']:,}/{quant['F']['matched_hours']:,} jam A lengkap tidak cocok dengan pemotongan serupa, dengan selisih tambahan maksimum {fmt(quant['F']['trunc_max_abs_residual_nT'], 3)} nT. Penyebabnya tidak dapat dipastikan dari arsip ini; F tidak dipakai untuk menjustifikasi kesetaraan X/Y/Z atau keputusan PCA. Perbedaan F tidak disebut revisi historis tanpa arsip versi lama.",
        "",
        "## Bulan fokus dan batas waktu",
        "",
        "Tabel bulanan penuh untuk semua tahun dan komponen ada di `D2_hourly_vs_minute.csv`. Berikut bulan yang diwajibkan, memakai MAE X/Y/Z (nT); `A pasangan X` dan `A tidak lengkap X` memperlihatkan dampak missing.",
        "",
        "| Bulan | A MAE X/Y/Z | B MAE X/Y/Z | C MAE X/Y/Z | A pasangan X | A tidak lengkap X |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for year, month in focus:
        def three(candidate: str) -> str:
            return "/".join(fmt(monthly[year, month, c, candidate]["mae_nT"], 3) for c in "XYZ")
        a = monthly[year, month, "X", "A_00_59"]
        report.append(f"| {year}-{month:02d} | {three('A_00_59')} | {three('B_HHm30_to_HHp29')} | {three('C_HH00')} | {a['matched_hours']} | {a['minute_window_incomplete']} |")
    report += [
        "",
        "Pada bulan fokus, korelasi residu B terhadap kemiringan hourly X berkisar kuat positif (rinci di `D2_timestamp_diagnostics.csv`), sesuai salah letak jendela sekitar setengah jam. Residu A setelah median per hari dihilangkan mempunyai RMSE bentuk sekitar 0,03 nT pada X; pola ini konsisten dengan kuantisasi, bukan bukti revisi yang mengubah bentuk. Tidak ada klaim mengenai versi hourly yang dipakai penulis sekitar 2020.",
        "",
        "Contoh B di batas periode menunjukkan indeks UTC benar dan tidak terpotong pada arsip tahunan:",
        "",
        "| Timestamp hourly | Jendela B | Menit valid X/Y/Z/F |",
        "|---|---|---|",
    ]
    for x in boundary:
        report.append(f"| {x['timestamp_utc']} | {x['window_start_utc']} – {x['window_end_utc']} | {x['minute_count'].replace('|', '/')} |")
    report += [
        "",
        "Jam 2008-03-01 00:00 memiliki 59/60 menit valid pada B: ini missing nyata pada satu menit lintas batas, bukan kesalahan timestamp. Contoh 2012-01-01 dan 2013-01-01 melintasi tahun dengan 60/60 menit.",
        "",
        "## Offset Sq Mendeley: Februari 2008, 2012, 2016",
        "",
        "Tiga formulasi diuji pada lima IQD GFZ resmi: (1) baseline rerata lima jam malam per hari, (2) rerata 24 jam per hari, (3) baseline malam lalu pusatkan kurva rata-rata ke mean 24 jam nol. Formulasi 2 dan 3 ekuivalen secara aljabar untuk rata-rata linear; maksimum selisih numeriknya " + f"{eq_max:.3g} nT, sehingga bukan dua bukti independen. Februari 2016 memakai 29 Februari sesuai hipotesis D1-IQD yang masih provisional.",
        "",
        "| Tahun | Komp. | RMSE malam absolut | RMSE mean harian absolut | RMSE malam setelah offset dihilangkan | Mean residu malam | Mean malam acuan Mendeley |",
        "|---:|:---:|---:|---:|---:|---:|---:|",
    ]
    for year in (2008, 2012, 2016):
        for c in "XYZ":
            n = bench_map[year, c, "night"]
            d = bench_map[year, c, "daily_mean"]
            report.append(f"| {year} | {c} | {fmt(n['rmse_absolute_nT'], 4)} | {fmt(d['rmse_absolute_nT'], 4)} | {fmt(n['rmse_offset_removed_nT'], 4)} | {fmt(n['mean_residual_nT'], 4)} | {fmt(n['benchmark_night_mean_nT'], 4)} |")
    report += [
        "",
        "Semua kurva Sq Mendeley yang diuji mempunyai mean 24 jam ≈0, tetapi mean lima jam malamnya tidak nol. Kurva baseline malam sebaliknya mempunyai mean lima jam malam ≈0. Selisih utama bersifat offset aditif: mean harian mengurangi RMSE absolut dari 1–6 nT menjadi sekitar 0,11–0,16 nT, sama dengan RMSE setelah offset dihilangkan. Korelasi dan beda amplitudo untuk ketiga formulasi tersedia per kasus di `D2_benchmark_offset.csv`. Nilai sekitar 0,11–0,16 nT masih **di atas** ambang Sq 0,1 nT protokol, sehingga D2 tidak mengklaim reproduksi IQD numerik berhasil atau mengganti baseline malam secara diam-diam. Konvensi waktu kini mendukung A, tetapi versi data penulis dan langkah ekspor/pemusatan Mendeley belum diketahui.",
        "",
        "## Duplikasi meanField dan mode Y/Z",
        "",
        "Semua 180 pasangan DAT PCA Y/Z yang sejenis diperiksa lewat struktur dan SHA-256. Tepat enam pasangan identik, seluruhnya **Februari**:",
        "",
    ]
    for x in duplicate:
        report.append(f"- `{Path(x['Y_file']).name}` = `{Path(x['Z_file']).name}` (SHA-256 `{x['Y_sha256']}`).")
    report += [
        "",
        "EOF1–EOF3, PC1–PC3, serta berkas serupa pada bulan lain mempunyai hash Y/Z berbeda. Jadi anomali meluas dari `meanField` ke `mode1` dan `mode2` Februari, tetapi pemeriksaan ini tidak menjalankan PCA atau membuktikan isi EOF/PC benar.",
        "",
        "Pencocokan `COI_Y_meanField_m02.dat` terhadap rerata 24 jam WDC setelah satu offset konstan:",
        "",
        "| Tahun | WDC Y: RMSE (nT) | WDC Z: RMSE (nT) |",
        "|---:|---:|---:|",
    ]
    for year in (2008, 2012, 2016):
        y = next(x for x in anomaly_fit if int(x["year"]) == year and x["WDC_component"] == "Y")
        z = next(x for x in anomaly_fit if int(x["year"]) == year and x["WDC_component"] == "Z")
        report.append(f"| {year} | {fmt(y['rmse_nT'], 4)} | {fmt(z['rmse_nT'], 4)} |")
    report += [
        "",
        "Isi `meanField Y` lebih cocok dengan komponen WDC **Z**. Ini diskrepansi sumber yang nyata, bukan izin mengedit DAT asli. Usulan untuk tahap berikutnya ialah lapisan pembacaan terpisah yang memberi flag/karantina pada enam berkas Februari dengan provenance SHA-256; koreksi atau rekonstruksi Y tidak diaktifkan tanpa review dan versi protokol baru bila mengubah aturan benchmark.",
        "",
        "## Keputusan D2 dan kesiapan G1",
        "",
        f"- **D2-TIME — {time_status}:** A sesuai seluruh 92.963/92.964/92.967 jam X/Y/Z berpasangan setelah pemotongan 0,1 nT; B/C jauh lebih buruk. Arsip sendiri tidak menyebut interval rinci, tetapi standar dan bukti empiris konsisten dengan menit 00–59 dan label artikel HH:30.",
        f"- **D2-DATA — {data_status}:** X/Y/Z ekuivalen pada jendela 60 menit penuh, termasuk aturan ketersediaan 54/60 yang teramati. F menyisakan 22.577 mismatch kuantisasi kecil yang belum dijelaskan. Jam tidak lengkap dan sentinel ditandai; penyebab historis tidak disimpulkan.",
        f"- **D2-BENCHMARK — {benchmark_status}:** dokumentasi baseline malam dan berkas Sq terpusat 24 jam tidak sepenuhnya sejalan; enam duplikasi Y/Z Februari mencakup meanField dan mode. Evaluasi kondisi berhenti **S7 terpicu** untuk review sumber.",
        f"- **Keputusan akhir D2 — {gate_status}.** Diagnostik waktu selesai, namun status data penuh dan benchmark bersyarat. **Rekomendasi G1: HOLD**, nilai D1-IQD provisional dan S7 bersama sebelum G1 dapat dinyatakan lolos. D3/D4, PCA penuh, DTW, DIFI, dan classifier tidak dijalankan.",
        "",
        "## Reproduksibilitas",
        "",
        "Jalankan `python -B phase2a/D2/d2_compute.py` lalu `python -B phase2a/D2/d2_report.py`. `D2_execution.log` mencatat setiap tahap. CSV bulanan, fokus, jendela tidak lengkap, dan anomali berisi angka serta path/hash sumber; JSON memuat parameter dan versi Python/NumPy. `D2_review.zip` hanya berisi kode, laporan, JSON, CSV, checksum, dan log; ZIP raw tidak disertakan.",
        "",
    ]
    (D2 / "D2_report.md").write_text("\n".join(report), encoding="utf-8")

    log_path = D2 / "D2_execution.log"
    base_log = log_path.read_text(encoding="utf-8").split("INFO D2 final decisions:")[0]
    log_path.write_text(base_log + f"INFO D2 final decisions: TIME={time_status}; DATA={data_status}; BENCHMARK={benchmark_status}; GATE={gate_status}; G1={g1_status}\n", encoding="utf-8")
    included = ["D2_report.md", "D2_hourly_vs_minute.csv", "D2_timestamp_diagnostics.csv",
                "D2_benchmark_offset.csv", "D2_meanfield_anomaly.csv", "D2_validation.json",
                "D2_execution.log", "d2_compute.py", "d2_report.py"]
    checksum = D2 / "D2_checksums.sha256"
    checksum.write_text("".join(f"{sha(D2 / name)}  {name}\n" for name in included), encoding="ascii")
    included.append(checksum.name)
    archive_path = D2 / "D2_review.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in included:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (D2 / name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None or sorted(archive.namelist()) != sorted(included):
            raise RuntimeError("D2_review.zip CRC or member mismatch")
    (D2 / "D2_review.sha256").write_text(f"{sha(archive_path)}  D2_review.zip\n", encoding="ascii")
    print(f"D2 {gate_status}; TIME={time_status}; DATA={data_status}; BENCHMARK={benchmark_status}; ZIP={archive_path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
