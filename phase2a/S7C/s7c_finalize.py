"""Finalize registration-3 stop 0a, policy delta, reports, checksums and review ZIP."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import platform
import sys
import zipfile
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

from s7c_prepare import ROOT, OUT, SOURCE, sha, check_g0_manifest
from s7c_acquire_corrected import ARCHIVE


def read_json(name: str) -> dict:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def write_json(name: str, obj: object) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def policy_delta() -> list[dict]:
    prior = read_csv(ROOT / "phase2a/S7B/S7B_benchmark_policy.csv")
    if len(prior) != 684:
        raise RuntimeError("S7B policy no longer has 684 DAT")
    rows = []
    for original in prior:
        if original["family"] != "PCA modes" or original["component"] != "X" or original["month"] not in {"04", "06", "09", "11"}:
            continue
        if original["allowed_use"] != "ORIGINAL_ABSOLUTE":
            raise RuntimeError(f"Unexpected previous use for A5: {original['relative_path']}")
        row = dict(original)
        row["allowed_use"] = "SUSPECT_DIAGNOSTIC"
        row["d3_eligible"] = "false"
        row["validation_limitations"] += "; A5 applies to 2008 series / combined series containing 2008 only; other annual columns retain registration-2 use"
        if original["year_scope"] == "ANNUAL":
            scope = "y.2008 column only"
        elif original["year_scope"] == "ALL_YEARS":
            scope = "y.all combined series contains 2008"
        else:
            scope = "y.2008 column and y.all combined series containing 2008"
        row["target_year"] = "2008"
        row["affected_series_scope"] = scope
        row["prior_allowed_use"] = original["allowed_use"]
        row["reason_reg3"] = f"A5: PCA X 2008-{original['month']} SUSPECT_DIAGNOSTIC because S7-B meanField _y_all X inconsistency; series-level overlay, no change to other years/Y/Z"
        rows.append(row)
    if len(rows) != 72 or len({r["relative_path"] for r in rows}) != 72:
        raise RuntimeError(f"A5 policy delta expected 72 unique X DAT entries, got {len(rows)}")
    if any(r["month"] not in {"04", "06", "09", "11"} or r["component"] != "X" for r in rows):
        raise RuntimeError("A5 delta leaked beyond X four months")
    with (OUT / "S7C_benchmark_policy_delta.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def month_transitions(base_meta: dict) -> dict[str, list[dict]]:
    result = {}
    monthly = base_meta["month_base_sets"]
    for comp in "XYZF":
        ordered = sorted((key[:7], bases) for key, bases in monthly.items() if key.endswith(":" + comp))
        transitions = []
        for i in range(1, len(ordered)):
            if ordered[i][1] != ordered[i-1][1]:
                transitions.append({"year_month": ordered[i][0], "previous_bases": ordered[i-1][1],
                                    "current_bases": ordered[i][1]})
        result[comp] = transitions
    return result


def main() -> None:
    pre = read_json("S7C_preflight.json")
    correction = read_json("S7C_acquisition_correction.json")
    cross = read_json("S7C_wdc_crosscheck_summary.json")
    d2c = read_json("D2c_summary.json")
    previous_g1 = json.loads((ROOT / "phase2a/S7B/S7B_G1_decision.json").read_text(encoding="utf-8"))
    if previous_g1["status"] != "HOLD":
        raise RuntimeError("Historical registration-2 G1 status unexpectedly changed")
    if correction["status"] != "DOWNLOADED_COMPLETE_VALID_ZIP" or sha(ARCHIVE) != correction["archive_sha256"]:
        raise RuntimeError("Corrected WDC archive missing or SHA changed")
    if not cross["crosscheck"]["format_inconsistent"] or d2c["status"] != "NOT_RUN_WDC_FORMAT_INCONSISTENT":
        raise RuntimeError("This finalizer expects mandatory stop 0a; do not force D2c/G1")
    if cross["crosscheck"]["mismatch_gt_0p1_nT_percent_of_paired"] <= .1:
        raise RuntimeError("Crosscheck stop threshold not actually crossed")
    delta = policy_delta()
    transitions = month_transitions(cross["base_meta"])
    old_zip = ROOT / "phase2a/S7B/S7B_review.zip"
    old_zip_sidecar = OUT / "S7B_review.zip.sha256"
    old_zip_sidecar.write_text(f"{sha(old_zip)}  S7B_review.zip\n", encoding="utf-8")
    g1 = {"schema": "Auto-SqPCA-S7C-G1-v1", "protocol": "G0-registration-3 APPROVED",
          "registration2_historical_status": "HOLD", "registration2_decision_sha256": sha(ROOT / "phase2a/S7B/S7B_G1_decision.json"),
          "registration3_status": "HOLD", "triggered_rows": ["0a_WDC_FORMAT_INCONSISTENT"],
          "selected_row": "0a_WDC_FORMAT_INCONSISTENT", "priority_A3": "HOLD > CONDITIONAL PASS with exclusions > CONDITIONAL PASS; no competing evaluated row here",
          "other_rows": {"0b": "NOT_EVALUATED_D2C_STOPPED", "1": "NOT_EVALUATED_D2C_STOPPED",
                         "2": "NOT_EVALUATED_D2C_STOPPED", "3": "NOT_EVALUATED_D2C_STOPPED",
                         "4": "NOT_EVALUATED_D2C_STOPPED"},
          "numeric_evidence": {"paired_valid_component_hours": cross["crosscheck"]["paired_valid_component_hours"],
                               "mismatch_gt_0p1_nT": cross["crosscheck"]["mismatch_gt_0p1_nT_count"],
                               "mismatch_percent": cross["crosscheck"]["mismatch_gt_0p1_nT_percent_of_paired"],
                               "stop_threshold_percent": .1,
                               "XYZ_component_mismatch_counts": {c: cross["crosscheck"]["by_component"][c]["MISMATCH_GT_0P1"] for c in "XYZ"},
                               "D2c_comparison_rows": 0},
          "affected_months_REVISION_LIKE": "NOT_EVALUATED_D2C_STOPPED",
          "excluded_months_registration3": [],
          "excluded_months_reason": "No D2c classification was permitted after stop 0a; do not infer exclusions from historical D2b labels",
          "A5_suspect_year_months": ["2008-04:X", "2008-06:X", "2008-09:X", "2008-11:X"],
          "A5_policy_delta_rows": len(delta),
          "A5_granularity": "72 X PCA DAT entries with target_year=2008 series-level overlay; annual columns for other years and Y/Z unchanged",
          "pilot_months": {"development": ["2017-06", "2017-10"], "holdout": ["2009-01", "2015-03"],
                           "affected_by_D2c": "NOT_EVALUATED_D2C_STOPPED", "replacement": "NOT_SELECTED"},
          "pilot_G2_ready": False,
          "consequence": "Registration-3 row 0a directs transition to K10 documented reimplementation; do not run original G2 pilot or PCA in S7-C",
          "claims": {"R1": "NOT_TARGET", "R2": "PRIOR_SHAPE_EVIDENCE_ONLY_O1_LIMITATION",
                     "R3": "NOT_TESTED", "R4": "NOT_TESTED"},
          "source_sha256": sha(SOURCE), "corrected_WDC_archive_sha256": sha(ARCHIVE),
          "crosscheck_summary_sha256": sha(OUT / "S7C_wdc_crosscheck_summary.json"),
          "D2c_summary_sha256": sha(OUT / "D2c_summary.json"),
          "limitations": ["WDC fixed-width I4 hourly values differ at sub-nT resolution from IAGA hourly decimals; 0.1 nT crosscheck rule fails.",
                          "Maximum difference is larger than sub-nT precision; no further forensic attribution is authorized.",
                          "D2c transformed daily residuals, H-a and affected pilot months were not evaluated after stop 0a.",
                          "D2b and registration-2 G1 HOLD remain unchanged."]}
    write_json("S7C_G1_decision.json", g1)
    ratio = cross["crosscheck"]["mismatch_gt_0p1_nT_percent_of_paired"]
    mismatch = cross["crosscheck"]["mismatch_gt_0p1_nT_count"]
    paired = cross["crosscheck"]["paired_valid_component_hours"]
    base_meta = cross["base_meta"]
    base_lines = []
    for comp in "XYZF":
        shifts = transitions[comp]
        shift_text = ", ".join(f"{r['year_month']} ({r['previous_bases'][0]}→{r['current_bases'][0]})" for r in shifts) if shifts else "tidak ada"
        base_lines.append(f"| {comp} | {', '.join(map(str, base_meta['overall_unique_bases'][comp]))} | {'ya' if base_meta['base_constant_all_2007_2017'][comp] else 'tidak'} | {shift_text} |")
    component_lines = []
    for comp in "XYZF":
        c = cross["crosscheck"]["by_component"][comp]
        n = c.get("WITHIN_0P1", 0) + c.get("MISMATCH_GT_0P1", 0)
        component_lines.append(f"| {comp} | {n} | {c.get('MISMATCH_GT_0P1',0)} | {100*c.get('MISMATCH_GT_0P1',0)/n:.3f}% |")
    d2c_report = f"""# D2c — Validasi kerangka tabular base WDC

**Status: D2c TIDAK DIJALANKAN, kondisi henti 0a `WDC_FORMAT_INCONSISTENT`.** Uji prasyarat wajib gagal: {mismatch:,} dari {paired:,} jam–elemen valid berpasangan (**{ratio:.3f}%**) berbeda >0,1 nT antara `base × 100 + tabular value` WDC fixed-width dan data hourly IAGA-2002 yang dipakai D2/D2b. Ambang henti amandemen ialah >0,1% jam. Nilai ini jauh melewatinya; tidak ada `d′`, klasifikasi D2c, atau H-a D2c yang dihitung.

## Sumber dan akuisisi

Sumber resmi WDC Edinburgh: [{correction['corrected_url']}]({correction['corrected_url']}) (`file_format=wdc`, `orientation=XYZF`, 2007-01-01 hingga sebelum 2018-01-01). HTTP {correction['http_status']}, {correction['received_bytes']:,} byte, SHA-256 `{correction['archive_sha256']}`, 11 anggota tahunan; CRC ZIP lulus. Respons pertama dengan `years=2007-2017` hanya mengandung 2007 dan 2017 karena parameter itu diperlakukan sebagai daftar dua tahun. Respons pertama dipertahankan, SHA-256 `{json.loads((OUT/'S7C_acquisition.json').read_text(encoding='utf-8'))['archive_sha256']}`. Koreksi menggunakan batas tanggal eksplisit; kedua URL, waktu, status, dan hash ada di JSON akuisisi. Tidak ada unduhan setelah koreksi.

## Parser dan hasil validasi silang

Parser membaca 16.072 baris harian (4 elemen ×4.018 hari), masing-masing 120 karakter: COI, tanggal, elemen, abad, base I4 pada kolom 17–20, 24 tabular value I4 pada kolom 21–116, dan rata-rata harian pada 117–120. Token `9999` diperlakukan missing. Semua tanggal/elemen unik dan lengkap. CSV per jam berisi {cross['crosscheck']['total_component_hours']:,} baris; {paired:,} berpasangan valid. Status missing: IAGA saja {cross['crosscheck']['status_counts'].get('IAGA_MISSING_ONLY',0):,}, format WDC saja {cross['crosscheck']['status_counts'].get('WDC_FORMAT_MISSING_ONLY',0):,}, keduanya {cross['crosscheck']['status_counts'].get('BOTH_MISSING',0):,}. Median |selisih| = {cross['crosscheck']['median_abs_difference_nT']:.3f} nT, maksimum = {cross['crosscheck']['max_abs_difference_nT']:.3f} nT. Format I4 mencetak nT bulat, sedangkan IAGA mencetak desimal; hal ini dapat menjelaskan sebagian selisih sub-nT, tetapi **tidak membenarkan mengubah ambang** dan tidak menjelaskan otomatis maksimum tersebut.

| Elemen | Jam valid berpasangan | >0,1 nT | Persentase |
|:---:|---:|---:|---:|
{chr(10).join(component_lines)}

Data silang per jam, termasuk contoh ketidakcocokan awal dan hash sumber, ada di `S7C_wdc_crosscheck.csv` serta `S7C_wdc_crosscheck_summary.json`. Validasi dilakukan pada XYZF; X/Y/Z sendiri masing-masing sekitar 70% di atas 0,1 nT, sehingga F bukan penyebab tunggal keputusan henti.

## Tabular base dari metadata

Base tidak dipasang dari konstanta temuan reviewer. Tabel base per elemen × tahun × bulan × nilai base beserta jumlah hari ada di `S7C_wdc_base_table.csv`. Tidak ada bulan yang memakai lebih dari satu base untuk elemen yang sama, tetapi ada perubahan antarbulan/tahun:

| Elemen | Base unik 2007–2017 | Konstan seluruh periode | Bulan saat base berubah dari bulan sebelumnya |
|:---:|---|:---:|---|
{chr(10).join(base_lines)}

## Penghentian

Menurut A1 dan baris 0a G1 registration-3, transformasi tabular base tidak boleh dipakai untuk D2c setelah validasi silang gagal. `D2c_comparison.csv` hanya memiliki header, dan `D2c_summary.json` menyatakan `NOT_RUN_WDC_FORMAT_INCONSISTENT`. Tidak ada bulan `REVISION_LIKE` atau pengecualian D2c yang dapat diputuskan. Hasil D2b (10.953 selisih mentah dan G1 HOLD registration-2) tetap utuh. Audit forensik ditutup di titik henti ini; tidak ada D2d.
"""
    (OUT / "D2c_report.md").write_text(d2c_report, encoding="utf-8")
    changes_path = OUT / "S7C_changes.md"
    with changes_path.open("a", encoding="utf-8") as stream:
        stream.write(f"\n## Eksekusi dan kondisi henti\n\nPermintaan awal `years=2007-2017` menghasilkan hanya dua anggota tahunan; koreksi batas tanggal menghasilkan 11 anggota. Keduanya dicatat dan respons mentah pertama tidak dihapus. Validasi silang final: {mismatch:,}/{paired:,} ({ratio:.3f}%) beda >0,1 nT, melampaui 0,1%; D2c tidak dihitung dan G1 registration-3 HOLD baris 0a. Tidak ada bulan EXCLUDED yang ditetapkan dari D2c. A5 diterapkan sebagai 72 baris delta kebijakan tingkat deret X 2008 pada empat bulan; berkas multiyear untuk tahun lain dan Y/Z tidak diubah.\n")
    s7c_report = f"""# S7-C — Registrasi 3 dan keputusan G1

**G0-registration-3 APPROVED; G1 registration-2 tetap HOLD; G1 registration-3 HOLD (baris 0a).** Perintah henti berlaku sebelum perhitungan D2c karena {mismatch:,}/{paired:,} jam–elemen valid (**{ratio:.3f}%**) tidak setara dalam 0,1 nT; ambang yang disetujui hanya 0,1% jam. Status `WDC_FORMAT_INCONSISTENT` adalah hasil ambang silang format, bukan bukti revisi historis WDC. G2 pilot **belum siap**. Jalur K10 implementasi ulang dengan deviasi terdokumentasi adalah konsekuensi keputusan, bukan eksperimen yang dijalankan di S7-C.

Dokumen keputusan registration-3 disalin utuh dengan SHA-256 `{sha(SOURCE)}`; A1–A7 terdaftar di protokol baru. Respons WDC final 11 tahun berukuran {correction['received_bytes']:,} byte, SHA-256 `{sha(ARCHIVE)}`; respons pertama yang hanya 2007/2017 dipertahankan dan dicatat sebagai koreksi permintaan. Parser memeriksa 16.072 baris fixed-width dan 385.728 jam–elemen; tabel base serta CSV silang per jam tersedia. Base berubah pada X, Y, F; Z tetap 312. `d′` dan H-a D2c **tidak dievaluasi**.

Delta A5 berisi {len(delta)} baris DAT PCA X sebagai **overlay tingkat seri 2008** untuk April, Juni, September, dan November. Tidak ada bulan `EXCLUDED` dari D2c karena klasifikasi pascatransformasi dihentikan sebelum dijalankan. Status 18 kontrol Sq FAIL absolut, D1-IQD provisional, dan semua keluaran S7-B tidak diubah. D2d, D3/D4, PCA/SVD, DTW, DIFI, classifier, dan G2–G4 tidak dijalankan.

Paket review memuat laporan, kode, CSV hasil silang, JSON, log, serta checksum berkas isi. ZIP mentah WDC/Mendeley tidak disertakan. Hash ZIP review dan koreksi sidecar ZIP S7-B berada di berkas `.sha256` **di luar** masing-masing ZIP.
"""
    (OUT / "S7C_report.md").write_text(s7c_report, encoding="utf-8")
    frozen_bad = []
    for path, digest in pre["frozen_outputs_sha256_before"].items():
        if sha(ROOT / path) != digest:
            frozen_bad.append(path)
    if frozen_bad:
        raise RuntimeError(f"Frozen G0/D1/D2/S7/S7B outputs changed: {frozen_bad[:5]}")
    g0 = check_g0_manifest()
    if sha(ARCHIVE) != correction["archive_sha256"]:
        raise RuntimeError("New WDC format raw ZIP changed after analysis")
    first = read_json("S7C_acquisition.json")
    if sha(Path(first["raw_path"])) != first["archive_sha256"]:
        raise RuntimeError("First WDC format raw ZIP changed")
    now = dt.datetime.now(dt.timezone.utc)
    validation = {"schema": "Auto-SqPCA-S7C-validation-v1", "completed_utc": now.isoformat(),
                  "completed_local_Asia_Makassar": now.astimezone(ZoneInfo("Asia/Makassar")).isoformat(),
                  "registration3_source_sha256": sha(SOURCE), "registration3_copy_sha256": sha(OUT / SOURCE.name),
                  "G0_manifest": g0, "frozen_output_files_checked": len(pre["frozen_outputs_sha256_before"]),
                  "frozen_output_sha256_mismatches": 0,
                  "raw_WDC_format_zip_sha256": {"first_partial": first["archive_sha256"], "complete": correction["archive_sha256"]},
                  "raw_zip_sha256_unchanged_after": True,
                  "crosscheck_component_hours": cross["crosscheck"]["total_component_hours"],
                  "crosscheck_paired_valid": paired, "crosscheck_mismatch_count": mismatch,
                  "crosscheck_mismatch_percent": ratio, "crosscheck_stop_threshold_percent": .1,
                  "D2c_status": d2c["status"], "G1_registration2": "HOLD", "G1_registration3": "HOLD",
                  "A5_policy_delta_rows": len(delta), "excluded_months_registration3": [],
                  "environment": {"python": sys.version, "platform": platform.platform()},
                  "errors": [], "acquisition_correction": "Initial years parameter selected two endpoint years; corrected start/end request selected 11 years"}
    write_json("S7C_validation.json", validation)
    with (OUT / "S7C_execution.log").open("a", encoding="utf-8") as stream:
        stream.write(f"INFO {now.isoformat()} G1 reg2=HOLD reg3=HOLD row=0a; D2c stopped; {len(delta)} A5 delta rows; 3702 G0 inputs + {len(pre['frozen_outputs_sha256_before'])} frozen outputs unchanged\n")
    files = ["G0-registration-3_D2c.md", "S7C_protocol_registration3.md", "S7C_changes.md",
             "S7C_preflight.json", "S7C_acquisition.json", "S7C_acquisition_correction.json",
             "S7C_wdc_base_table.csv", "S7C_wdc_crosscheck.csv", "S7C_wdc_crosscheck_summary.json",
             "D2c_comparison.csv", "D2c_summary.json", "D2c_report.md", "d2c.py", "d2c_test.py",
             "s7c_prepare.py", "s7c_acquire.py", "s7c_acquire_corrected.py", "s7c_finalize.py",
             "S7C_benchmark_policy_delta.csv", "S7C_G1_decision.json", "S7C_report.md",
             "S7C_execution.log", "S7C_validation.json"]
    checksums = "".join(f"{sha(OUT / name)}  {name}\n" for name in files)
    (OUT / "S7C_checksums.sha256").write_text(checksums, encoding="utf-8")
    files.append("S7C_checksums.sha256")
    archive_path = OUT / "S7C_review.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 13, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, (OUT / name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED,
                             compresslevel=9)
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None or sorted(archive.namelist()) != sorted(files):
            raise RuntimeError("S7C review ZIP CRC/member list failed")
        for name in files:
            if archive.read(name) != (OUT / name).read_bytes():
                raise RuntimeError(f"S7C ZIP member differs: {name}")
    (OUT / "S7C_review.zip.sha256").write_text(f"{sha(archive_path)}  S7C_review.zip\n", encoding="utf-8")
    print(f"G1 reg2 HOLD; G1 reg3 HOLD row 0a; D2c stopped; S7C ZIP {archive_path.stat().st_size} bytes SHA-256 {sha(archive_path)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        with (OUT / "S7C_execution.log").open("a", encoding="utf-8") as stream:
            stream.write(f"ERROR {type(error).__name__}: {error}\n")
        raise
