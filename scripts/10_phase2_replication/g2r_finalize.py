"""Package audited G2-R outputs after the one-time holdout run."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import zipfile
from pathlib import Path

import g2r

OUT = Path(__file__).resolve().parent


def rows(name: str) -> list[dict]:
    with (OUT / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write(name: str, text: str) -> None:
    (OUT / name).write_text(text, encoding="utf-8")


def main() -> None:
    g0 = g2r.verify_frozen("finalization")
    config = json.loads((OUT / "G2R_frozen_config.json").read_text(encoding="utf-8"))
    config_hash = g2r.sha(OUT / "G2R_frozen_config.json")
    if config_hash != (OUT / "G2R_frozen_config.json.sha256").read_text().split()[0]:
        raise RuntimeError("Frozen configuration SHA-256 mismatch")
    for name, expected in config["code_sha256"].items():
        if g2r.sha(OUT / name) != expected:
            raise RuntimeError(f"Frozen code changed: {name}")
    selection = json.loads((OUT / "G2R_variant_selection.json").read_text(encoding="utf-8"))
    result = json.loads((OUT / "G2R_result.json").read_text(encoding="utf-8"))
    if result["config_sha256"] != config_hash:
        raise RuntimeError("Holdout result points to different frozen configuration")
    inv, dev, hold, mean, days = (rows(n) for n in ("G2R_matrix_inventory.csv", "G2R_dev_metrics.csv",
                                                  "G2R_holdout_metrics.csv", "G2R_meanfield_test.csv",
                                                  "G2R_interpolated_hours_by_day.csv"))
    dev_inv = [r for r in inv if r["set"] == "development"]
    hold_inv = [r for r in inv if r["set"] == "holdout"]
    dev_denom = {s: sum(r["status"] == s for r in dev_inv) for s in ("ELIGIBLE", "NOT_ELIGIBLE", "UNRESOLVED_MISSING")}
    if len(dev_inv) != 9 or len(hold_inv) != 9 or len(dev) != 24 or len(hold) != 9:
        raise RuntimeError(f"Unexpected matrix/metric counts: {len(dev_inv)}, {len(hold_inv)}, {len(dev)}, {len(hold)}")
    # Expose the individual source digests, not just the digest of the mapping.
    g0_manifest = {r["relative_path"]: r["sha256"] for r in g2r.read_csv(g2r.ROOT / "phase2a/G0/input_manifest.csv")}
    for target in inv:
        paths = json.loads(target["benchmark_files"])
        digests = {role: g2r.sha(g2r.ROOT / path) for role, path in paths.items()}
        if any(g0_manifest.get(paths[role]) != digest for role, digest in digests.items()):
            raise RuntimeError(f"Mendeley benchmark SHA mismatch: {target['year']}-{target['month']}:{target['component']}")
        target["benchmark_file_sha256"] = json.dumps(digests, sort_keys=True)
    g2r.table("G2R_matrix_inventory.csv", inv, g2r.INV_FIELDS + ["benchmark_file_sha256"])
    k11_ok = "8 passed" in (OUT / "G2R_unit_tests.log").read_text(encoding="utf-8")
    if not k11_ok:
        raise RuntimeError("PCA and K11 tests not recorded as 8 passed")
    protocol_hash = g2r.sha(OUT / "G2R_protocol_v1.md")
    changes = f"""# G2-R — perubahan dan batas klaim

- Protokol: `G2R-v1`, APPROVED menurut berkas yang diberikan peneliti, SHA-256 `{protocol_hash}`. Jalur K10 berarti implementasi ulang independen dengan deviasi terdokumentasi. Status resmi G1 registration-2 dan registration-3 tetap **HOLD**. Tidak ada artefak G0–S7-C yang diubah.
- E1–E4 dalam bagian 0 protokol dicatat sebagai **EXPLORATORY_POST_HOC**. E1 menyatakan nilai WDC format merupakan pembulatan half-to-even dari IAGA per jam pada seluruh pasangan X/Y/Z yang ditinjau; E2 menyatakan tabular base sekarang tidak menjelaskan level Mendeley; E3 menyatakan koreksi base hipotetis tetap menghasilkan selisih ribuan nT; E4 menyatakan konsistensi X/Y/Z lintas format. Keempatnya adalah temuan yang *dinyatakan protokol*, bukan validasi baru G2-R; tidak mengubah G1 HOLD atau benchmark.
- DV1–DV6 diterapkan sesuai protokol. Input PCA = COI hourly nT absolut; interpolasi linear hanya di dalam bulan; 29 Februari dihapus; SVD float64; orientasi mode `outer(PC_hour, EOF_day)`; pembalikan tanda PC dan EOF bersamaan.
- Tidak tersedia DAT `mode3` Mendeley. Mode ketiga benchmark dihitung dari PC3 × EOF3 asli. Pada mode1/2 yang tersedia, identitas PC × EOF = mode diuji numerik. Ini adalah penurunan dari berkas sumber, bukan edit atau rekonstruksi benchmark yang diklaim asli.
- Gabungan Juni X `NOT_ELIGIBLE` karena overlay `SUSPECT_DIAGNOSTIC` pada seri 2008 menurut S7-C. Gabungan Juni Y/Z memiliki 14 jam kosong di batas bulan yang tidak dapat diinterpolasi tanpa ekstrapolasi; masing-masing `UNRESOLVED_MISSING`. Tidak ada penggantian target.
- Kegagalan awal pembacaan pengembangan: `RuntimeError: Mendeley DAT uniqueness COI_X_mode3_m06.dat: 0 matches`. Setelah inventaris memastikan mode3 DAT memang tidak ada, kode membaca PC3/EOF3 dan mencatat mode3 turunan. Tidak ada metrik pengembangan atau holdout yang terbit dari upaya gagal itu.
- Protokol bagian 12 meminta inventaris 18 matriks sebelum pengembangan sekaligus melarang membaca matriks holdout sebelum pembekuan. Untuk memenuhi blinding, nilai holdout baru dibaca dan inventaris holdout diselesaikan setelah `G2R_frozen_config.json` dibekukan. Kebijakan/hash file dapat diperiksa lebih awal tanpa membaca nilai holdout.
- Konfigurasi dibekukan sebelum holdout, SHA-256 `{config_hash}`. Varian {config['variant']} dipilih dengan aturan {selection['selection_rule']}. Holdout dieksekusi sekali dengan kode dan konfigurasi beku.
- K11: loader umum untuk PLR/TUN/KDU/GUA 2014–2018 dan konversi UTC → waktu matahari lokal berdasarkan bujur tersedia. Dua uji unit sintetis K11 lulus; belum ada unduhan atau analisis data keempat stasiun.
"""
    write("G2R_changes.md", changes)
    hlines = ["| Matriks | Frobenius relatif | VF lolos | PC1 lolos | Seluruh metrik |",
              "|---|---:|:---:|:---:|:---:|"]
    for r in hold:
        hlines.append(f"| {r['year']}-{int(r['month']):02d} {r['component']} | {float(r['frob_relative']):.5f} | {r['vf_pass']} | {r['pc1_pass']} | {r['overall_pass']} |")
    d4 = json.loads((OUT / "G2R_D4_scale.json").read_text(encoding="utf-8"))
    d4_h = json.loads((OUT / "G2R_D4_holdout_scale.json").read_text(encoding="utf-8"))
    max_mode_identity = max(max(r["pc_eof_mode_max_abs_error"][:2]) for r in d4 + d4_h)
    day_flags = [r for r in days if r["flag_gt12"] == "True"]
    report = f"""# G2-R — pilot implementasi ulang PCA, jalur K10

**Hasil: varian {config['variant']}; holdout {result['label']}.** Ini adalah implementasi ulang independen; kesesuaian dengan keluaran publikasi tidak tercapai dalam toleransi yang didaftarkan. G1 registration-2 dan registration-3 tetap **HOLD**. Tidak ada klaim replikasi berhasil.

## Urutan dan integritas

Protokol G2R-v1 (`APPROVED` menurut berkas peneliti), SHA-256 `{protocol_hash}`. Enam uji inti PCA dan dua uji K11 lulus (`G2R_unit_tests.log`: 8 passed). Manifest G0: {g0['rows']:,} hash cocok; 119 berkas artefak beku dan WDC format yang tercatat sebelum eksekusi cocok hash hingga akhir. Hash konfigurasi beku `{config_hash}` dibuat sebelum pembacaan nilai holdout; hasil holdout menunjuk hash yang sama. Kode yang dibekukan juga cocok hash setelah holdout.

## Pengembangan dan pemilihan

Target 9 matriks: **{dev_denom['ELIGIBLE']} eligible, {dev_denom['NOT_ELIGIBLE']} NOT_ELIGIBLE, {dev_denom['UNRESOLVED_MISSING']} UNRESOLVED_MISSING**. Yang `NOT_ELIGIBLE` ialah gabungan Juni X karena kebijakan S7-C; gabungan Juni Y/Z tidak dapat dihitung karena masing-masing 14 jam batas bulan kosong. Tidak ada target pengganti. Tidak ada varian yang memenuhi syarat 9/9. Median galat Frobenius di enam matriks yang dapat dihitung: V0-A {selection['variants']['V0-A']['frob_median']:.5f}, V1 {selection['variants']['V1']['frob_median']:.5f}, V2 {selection['variants']['V2']['frob_median']:.5f}, V3 {selection['variants']['V3']['frob_median']:.5f}. Aturan 6.4 memilih **V1**, berlabel `DEVIATION_STRUCTURAL`.

Uji `meanField` kebal offset pada enam matriks tahunan memberi s_daily {min(float(r['s_daily']) for r in mean):.5f}–{max(float(r['s_daily']) for r in mean):.5f} nT dan s_night {min(float(r['s_night']) for r in mean):.5f}–{max(float(r['s_night']) for r in mean):.5f} nT; pola mendukung centering rata-rata hari, tetapi uji ini hanya pemutus seri. Norma PC Mendeley bukan satu (lihat `G2R_D4_scale.json`); RMSE EOF dinyatakan `NOT_APPLICABLE`. Pada mode1/2, maksimum |PC × EOF − mode| = {max_mode_identity:.3g} nT. Mode3 diturunkan dari PC3 × EOF3 karena DAT mode3 tidak ada; galat Frobenius jumlah mode1–3 adalah metrik utama.

## Holdout sekali, sesudah pembekuan

Penyebut: **target_total={result['denominator']['target_total']}, not_eligible={result['denominator']['not_eligible']}, suspect={result['denominator']['suspect']}, eligible={result['denominator']['eligible']}, pass={result['denominator']['pass']}, fail={result['denominator']['fail']}**. Hanya {result['frob_pass']}/9 memenuhi galat Frobenius ≤1%; PC1 Y/Z lolos di semua matriks holdout yang eligible. Label menurut aturan bagian 7 ialah **{result['label']}**.

{chr(10).join(hlines)}

## Interpolasi, deviasi, dan K11

Interpolasi dihitung di dalam setiap bulan sebelum matriks. Berkas `G2R_interpolated_hours_by_day.csv` mencatat jumlah jam interpolasi dan bendera >12 per hari; terdapat {len(day_flags)} baris bendera (termasuk pengulangan komponen bila terjadi). Celah batas bulan yang masih kosong tidak diekstrapolasi. Jam HH:00 IAGA diperlakukan sebagai rerata jam dan ditempatkan pada HH:30 UTC; komponen X/Y/Z absolut nT dipakai tanpa konstanta penyesuaian.

Loader K11 menerima ZIP IAGA-2002 XYZF bagi PLR, TUN, KDU, GUA pada 2014–2018 dan membaca bujur dari metadata tiap bulan. Konversi waktu matahari lokal adalah UTC + bujur timur/15 jam. Hanya uji sintetis yang dijalankan; **tidak ada** Sq, PCA, statistik, grafik, atau unduhan untuk stasiun K11.

Deviasi dan temuan S7-C pasca-hasil tercatat di `G2R_changes.md` dengan label eksploratoris. Proyek dapat lanjut ke rancangan G4-R menurut protokol; label struktur saat ini tetap {result['label']}.
"""
    write("G2R_report.md", report)
    validation = {"schema": "Auto-SqPCA-G2R-v1", "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "protocol_sha256": protocol_hash, "frozen_config_sha256": config_hash,
                  "G0_manifest": g0, "frozen_files_unchanged": 119,
                  "pca_unit_tests_passed": 6, "k11_unit_tests_passed": 2,
                  "development_denominator": {"target_total": 9, **dev_denom},
                  "holdout_denominator": result["denominator"],
                  "variant": config["variant"], "selection_label": selection["label"],
                  "holdout_label": result["label"], "G1_registration2": "HOLD", "G1_registration3": "HOLD",
                  "K11": "INFRASTRUCTURE_ONLY_SYNTHETIC_TESTS"}
    g2r.dump("G2R_validation.json", validation)
    g2r.log(f"finalized report; variant={config['variant']}; holdout={result['label']}; K11 infrastructure only")
    included = sorted(p for p in OUT.rglob("*") if p.is_file() and
                      not any(part in {"_deps", "__pycache__", ".pytest_cache"} for part in p.relative_to(OUT).parts) and
                      p.name not in {"G2R_review.zip", "G2R_review.zip.sha256", "G2R_checksums.sha256"})
    checks = "".join(f"{g2r.sha(p)}  {p.relative_to(OUT).as_posix()}\n" for p in included)
    write("G2R_checksums.sha256", checks)
    zip_path = OUT / "G2R_review.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in included + [OUT / "G2R_checksums.sha256"]:
            info = zipfile.ZipInfo(p.relative_to(OUT).as_posix(), date_time=(2026, 11, 13, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(zip_path) as z:
        bad = z.testzip()
        if bad: raise RuntimeError(f"Review ZIP CRC failure: {bad}")
        if sorted(z.namelist()) != sorted([p.relative_to(OUT).as_posix() for p in included] + ["G2R_checksums.sha256"]):
            raise RuntimeError("Review ZIP member inventory mismatch")
    write("G2R_review.zip.sha256", f"{g2r.sha(zip_path)}  G2R_review.zip\n")
    print(f"G2R_review.zip {zip_path.stat().st_size} bytes sha256={g2r.sha(zip_path)}")


if __name__ == "__main__":
    main()
