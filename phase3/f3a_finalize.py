"""F3A audit report, checksums, and small review package after E1 holdout."""
from __future__ import annotations
import csv
import datetime as dt
import json
import zipfile
from collections import Counter
from pathlib import Path

from f3_preflight import ROOT, OUT, sha, verify_snapshot


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))


def write(name: str, value: str) -> None:
    (OUT/name).write_text(value,encoding="utf-8")


def main() -> None:
    frozen_count=verify_snapshot()
    protocol_sha=sha(OUT/"F3_protocol_v1.md")
    tests=json.loads((OUT/"F3_synthetic_tests.json").read_text(encoding="utf-8"))
    if set(tests)!={f"T{i}" for i in range(1,9)} or not all(v["passed"] for v in tests.values()):
        raise RuntimeError("F3A synthetic suite incomplete/failing")
    freeze_path=OUT/"F3_E1_frozen.json"
    freeze_hash=sha(freeze_path)
    if freeze_hash!=(OUT/"F3_E1_frozen.json.sha256").read_text().split()[0]:
        raise RuntimeError("Frozen E1 hash mismatch")
    freeze=json.loads(freeze_path.read_text(encoding="utf-8"))
    for name,digest in freeze["code_sha256"].items():
        if sha(OUT/name)!=digest:raise RuntimeError(f"E1 code changed since freeze: {name}")
    plan=json.loads((OUT/"F3_E1_analysis_plan.json").read_text(encoding="utf-8"))
    if sha(OUT/"f3_e1_eval.py")!=plan["evaluation_code_sha256"]:
        raise RuntimeError("Pre-registered E1 evaluation code changed")
    c1=json.loads((OUT/"F3_C1_result.json").read_text(encoding="utf-8"))
    if c1["selected_method"]!=freeze["method"] or sha(OUT/"work/E1_holdout_cases.csv")!=c1["holdout_cases_sha256"]:
        raise RuntimeError("E1 holdout/result does not match frozen method or data")
    recovery=json.loads((OUT/"F3_E1_recovery.json").read_text(encoding="utf-8"))
    correction=json.loads((OUT/"F3_E1_2018_correction.json").read_text(encoding="utf-8"))
    gfz2018=json.loads((OUT/"F3_GFZ2018_source.json").read_text(encoding="utf-8"))
    if recovery.get("final_holdout_sha256")!=correction.get("preliminary_holdout_sha256") or \
       recovery.get("preserved_partial_sha256")!=sha(OUT/"work/E1_holdout_interrupted.csv") or \
       recovery.get("rerun_completed_months") is not False or \
       recovery.get("final_months")!=149:
        raise RuntimeError("E1 interrupted holdout recovery audit mismatch")
    if correction.get("final_holdout_sha256")!=c1["holdout_cases_sha256"] or \
       correction.get("preliminary_rows_preserved_as_prefix") is not True or \
       correction.get("GFZ2018_sha256")!=sha(OUT/gfz2018["path"]) or \
       gfz2018.get("months_validated")!=12:
        raise RuntimeError("GFZ 2018 holdout correction audit mismatch")
    sources=json.loads((OUT/"F3_data_sources.json").read_text(encoding="utf-8"))
    downloaded=[]
    for item in sources:
        if item["status"] in ("WDC_HOURLY","WDC_HOURLY_REUSED"):
            path=OUT/"raw/hourly"/f"{item['station']}_{item['year']}_hour_iaga_XYZF.zip"
            if sha(path)!=item["sha256"]:raise RuntimeError(f"Phase 3 raw hourly changed: {path}")
            downloaded.append(item)
    inventory=read_csv(OUT/"F3_data_inventory.csv")
    if len(inventory)!=276:raise RuntimeError(f"Expected 276 station-month inventory rows, got {len(inventory)}")
    dev_truth=read_csv(OUT/"work/E1_development_truth_status.csv")
    hold_truth=read_csv(OUT/"work/E1_holdout_truth_status.csv")
    pre_gfz_notes=read_csv(OUT/"work/E1_pre_GFZ2018/E1_holdout_truth_status.csv")
    first_gfz_error=next(r["error"] for r in pre_gfz_notes if r["year"]=="2018")
    pstar=read_csv(OUT/"F3_E1_pstar.csv")
    superiority=read_csv(OUT/"F3_E1_superiority.csv")
    tnd=read_csv(OUT/"F3_E1_TND_summary.csv")
    tnd_lines=["| Metode | Kasus TND | Tanpa keluaran | Median galat antar sel yang berhingga |","|---|---:|---:|---:|"]
    for method in ("M-INT","M-EXC","M-EM"):
        cells=[r for r in tnd if r["method"]==method]
        total=sum(int(r["n"]) for r in cells)
        failed=sum(int(r["nonfinite_errors"]) for r in cells)
        finite=sorted(float(r["median_error"]) for r in cells if r["median_error"])
        mid=(finite[len(finite)//2] if len(finite)%2 else (finite[len(finite)//2-1]+finite[len(finite)//2])/2) if finite else None
        tnd_lines.append(f"| {method} | {total} | {failed} ({failed/total:.1%}) | {mid:.4f} |" if mid is not None else f"| {method} | {total} | {failed} ({failed/total:.1%}) | tidak terdefinisi |")
    selected=freeze["method"]
    pstar_sel=[r for r in pstar if r["method"]==selected and r["epsilon"]=="0.05"]
    pstar_lines=["| Topeng | p* (ε=0,05) |","|---|---:|"]
    for r in pstar_sel:pstar_lines.append(f"| {r['mask_kind']} | {r['pstar']} |")
    sup_lines=["| Topeng | p | Rasio | CI 95% | Keunggulan |","|---|---:|---:|---:|:---:|"]
    for r in superiority:
        sup_lines.append(f"| {r['mask_kind']} | {r['p']} | {r['ratio'] or 'NA'} | [{r['ci_lower'] or 'NA'}, {r['ci_upper'] or 'NA'}] | {r['better_real']} |")
    truth_counts_dev=Counter(r["status"] for r in dev_truth)
    truth_counts_hold=Counter(r["status"] for r in hold_truth)
    changes=f"""# F3A — perubahan dan penyimpangan terdokumentasi

- Protokol sumber F3-v1 diberikan sebagai APPROVED, SHA-256 `{protocol_sha}`. Tugas A hanya persiapan dan E1; E2/E3 tidak dijalankan. Fase 1–2 dan G2R V1/G4R tetap beku; G1 HOLD, G2-R S-DEVIATE, G4-R D-AGREE tidak diubah.
- Percobaan preflight awal gagal karena snapshot historis mencakup cache `__pycache__` sedangkan inventaris baru mengecualikannya. Pesan asli: `RuntimeError: Phase 2 pre-G4R hash mismatch: ['phase2a/D1/__pycache__/d1_feb29.cpython-312.pyc', 'phase2a/G0/__pycache__/g0_acquire.cpython-312.pyc', ...]`. Perbandingan diulang pada berkas sumber dan keluaran, dengan jumlah cache yang dikecualikan tercatat di `F3A_preflight.json`.
- Uji T1 pertama pada M-EM sesuai batas berhenti 10⁻⁴ nT gagal: `max_error_nT=0.0006818657071968465`, iterasi 36, perubahan akhir `9.84190525225026e-05` nT. **Deviasi implementasi yang memerlukan perhatian reviewer:** solver M-EM memakai penghalusan sampai perubahan <10⁻⁸ nT (batas 500 iterasi tetap) untuk memenuhi syarat T1 galat <10⁻⁶ nT. Uji ulang memberi {tests['T1']['max_error_nT']:.3g} nT pada {tests['T1']['iterations']} iterasi. Angka ini bukan pelaksanaan persis ambang 10⁻⁴ yang tertulis; protokol sumber tidak ditimpa.
- Uji T3 awal memakai rank-1 tanpa derau dengan amplitudo hari berubah, sehingga pita bootstrap secara sah tidak nol. Rancangan uji diperbaiki menjadi hari rank-1 identik; T3 lulus (`s=1`, `w=0`). T2,T4,T5,T6,T7,T8 juga lulus; T6: noise 200/200 abstain, sinyal kuat 200/200 diterima.
- Inventaris awal berhenti pada GUA karena koordinat metadata berubah sedikit (144,860°→144,867° bujur; 13,590°→13,588° lintang). Pesan asli: `RuntimeError: Station coordinates changed across years: GUA, [144.86, 144.86, 144.867, 144.867, 144.867], [13.59, 13.59, 13.588, 13.588, 13.588]`. Kode kini memakai koordinat per tahun dan memverifikasi bahwa Δ LT tetap +10.
- Pengembangan empat pekerja dihentikan sebelum pembekuan untuk mempercepat eksekusi dengan delapan pekerja. CSV parsial disimpan sebagai `phase3/work/E1_development_aborted_4workers.csv`; hasil final dihitung ulang deterministik, tanpa melihat simulasi holdout sebelum pembekuan.
- Proses holdout awal terputus setelah {recovery['original_complete_months']} bulan lengkap ({recovery['original_partial_rows']} baris) saat giliran pengguna berakhir; tidak ada proses Python tersisa. CSV parsial dipertahankan persis di `phase3/work/E1_holdout_interrupted.csv` (SHA-256 `{recovery['original_partial_sha256']}`). Skrip `f3_e1_resume.py` memeriksa setiap blok bulan dan menghitung **hanya {recovery['remaining_months']} bulan yang belum tertulis**, menggunakan kode dan konfigurasi E1 beku. Pemulihan tidak membuka atau memakai ringkasan holdout sebelum semua bulan selesai. Batas pemulihan dan hash akhir tercatat di `F3_E1_recovery.json`.
- Pemeriksaan pertama pemulihan mengira {recovery['final_months_with_cases']} bulan yang mempunyai baris kasus adalah seluruh 149 bulan. Pesan asli: `{recovery['recovery_precheck_error_original']}`. Sebanyak {len(recovery['zero_case_months'])} bulan 2018 tidak menghasilkan kasus karena berkas IQD GFZ 2018 belum tersedia; pemeriksaan diselesaikan dengan menghitung status target untuk semua 149 bulan, tanpa mengulang kasus bulan yang sudah ada.
- **Koreksi input setelah evaluasi awal:** keenam puluh target komponen 2018 awalnya gagal dengan pesan asli `{first_gfz_error}`. Hasil dan gambar evaluasi awal, termasuk C1 awal `{correction['preliminary_C1_success']}`, dipertahankan di `phase3/work/E1_pre_GFZ2018/`. GFZ 2018 diunduh resmi ke `phase3/raw/gfz/` (HTTP {gfz2018['http_status']}, 12 bulan, SHA-256 `{gfz2018['sha256']}`); panggilan pembaca kalender pada pekerja 2018 diarahkan ke input baru tanpa mengubah kode E1 beku. Hanya 20 bulan 2018 dihitung; {correction['preliminary_holdout_rows']} baris awal identik sebagai prefiks keluaran akhir. Koreksi ini dilakukan **setelah C1 awal dilihat**, sehingga status akhir harus dibaca bersama jejak penyimpangan, bukan disebut holdout sekali jalan tanpa koreksi.
- Upaya unduh GFZ 2018 awal melalui `urllib` gagal dengan pesan asli `urllib.error.URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1000)>`; pengambilan ulang memakai `requests` dengan verifikasi sertifikat bawaan dan berhasil HTTP 200. Tidak ada verifikasi TLS yang dimatikan.
- Aturan analisis keunggulan per jenis topeng dan SHA-256 kode evaluasi dicatat sebelum holdout di `F3_E1_analysis_plan.json`. Kasus `NO_PASS`/`NO_MATRIX` diberi galat ∞ dalam median; status serta hitungan tersedia di hasil rinci, bukan dibuang dari penyebut.
- Topeng TND dibentuk dari 60 menit XYZ valid per jam, digeser ke LT TND, kemudian diselaraskan indeks hari-jam pada target. Perbedaan panjang bulan disiklus dari awal topeng sesuai F3-v1.
"""
    write("F3A_changes.md",changes)
    report=f"""# Fase 3 Tugas A — persiapan dan E1

**Metode terpilih: {selected}. Status C1 numerik: {'BERHASIL' if c1['C1_success'] else 'TIDAK BERHASIL'}; adopsi metode menunggu review penyimpangan.** Ini evaluasi E1 dengan kebenaran internal berupa keluaran pipeline pada bulan tanpa topeng. E2/SSB dan E3 belum dijalankan.

## Integritas dan data

Protokol F3-v1 SHA-256 `{protocol_sha}`; konfigurasi E1 dibekukan dengan SHA-256 `{freeze_hash}` **sebelum** simulasi holdout. Pemeriksaan akhir menemukan {frozen_count} artefak Fase 1–2 cocok hash, 42 ZIP menit beku dan 3.702 entri manifest G0 cocok pada preflight, serta {len(downloaded)} ZIP per jam baru cocok hash setelah dipakai. Akuisisi KDU/GUA 2014–2018 dan PLR/TUN 2017 seluruhnya HTTP 200, tanpa fallback menit. COI menggunakan snapshot G0. Data mentah disimpan di `phase3/raw/` dan tidak ada dalam ZIP review.

Holdout terputus setelah {recovery['original_complete_months']}/149 bulan; berkas parsial disimpan dengan hash dan pemulihan hanya menghitung {recovery['remaining_months']} bulan tersisa. Skrip, batas pemulihan, dan hash keluaran ada di `F3_E1_recovery.json`; rincian ada di `F3A_changes.md`.

**Koreksi input pasca-evaluasi:** GFZ 2018 semula hilang, sehingga evaluasi awal tidak memiliki kasus untuk {len(recovery['zero_case_months'])} bulan KDU/GUA 2018. Hasil awal disimpan di `phase3/work/E1_pre_GFZ2018/`; GFZ 2018 resmi kemudian diperoleh dan hanya bulan terdampak dihitung. {correction['preliminary_holdout_rows']} baris awal tetap identik. Ini penyimpangan urutan holdout yang material dan dicatat terbuka dalam `F3_E1_2018_correction.json`; metode terpilih dan aturan analisis tidak berubah.

Inventaris mempunyai {len(inventory)} bulan stasiun; {sum(r['eligible_E1']=='True' for r in inventory)} memenuhi E1 (≥99% jam XYZ valid, tanpa celah >2 jam) dan {sum(r['eligible_E2']=='True' for r in inventory)} memenuhi ambang E2 (≥95%). Pergeseran LT dihitung dari metadata: COI −1, KDU +9, GUA +10, PLR +7, TUN +7 jam. TND 2017 dipakai hanya sebagai sumber topeng dengan aturan 60 menit XYZ valid.

## Uji sintetis dan deviasi

T1–T8 lulus pada uji ulang; T1 {tests['T1']['max_error_nT']:.3g} nT setelah {tests['T1']['iterations']} iterasi, T3 stabilitas {tests['T3']['stability']} dan w={tests['T3']['relative_width']}. T6 abstain pada {tests['T6']['outcomes']['noise']['abstained']}/200 tanpa sinyal dan menerima {tests['T6']['outcomes']['strong']['accepted']}/200 sinyal kuat. **M-EM menggunakan penghalusan internal 10⁻⁸ nT**, lebih ketat daripada batas 10⁻⁴ di protokol agar T1 terpenuhi. Ini deviasi implementasi yang harus direview sebelum mengadopsi metode sebagai spesifikasi final; log awal dan alasan ada di `F3A_changes.md`.

## E1 pengembangan dan holdout

Set pengembangan: {sum(r['status']=='OK' for r in dev_truth)} komponen-bulan memiliki keluaran lengkap untuk target internal; {truth_counts_dev.get('UNRESOLVED_TRUTH',0)} tidak memiliki target terdefinisi. Skor pemilihan (rerata median galat per jenis topeng × komponen, p≤30%): {', '.join(f'{m}={v:.5g}' for m,v in freeze['selection_score_mean_of_family_component_medians'].items())}. Metode **{selected}** dipilih sebelum holdout. Set holdout setelah koreksi GFZ 2018: {sum(r['status']=='OK' for r in hold_truth)} komponen-bulan bertarget, {truth_counts_hold.get('UNRESOLVED_TRUTH',0)} tanpa target. Rincian kasus dan hash tersedia di `phase3/work/`; CSV ringkasan ada dalam paket review.

Batas aman p* memakai median galat ≤ε dan persentil 90 ≤2ε; ε utama 0,05, sensitivitas 0,03/0,10 ada di `F3_E1_pstar.csv`.

{chr(10).join(pstar_lines)}

Uji keunggulan metode terpilih terhadap M-INT memakai rasio median galat dengan CI 95% bootstrap 2.000 resampling bulan. Jenis topeng dihitung berhasil bila batas atas CI<1 pada sedikitnya dua dari p=20,30,40%; C1 butuh sedikitnya dua dari tiga jenis. M-EM mencapai batas 500 iterasi pada {c1['M_EM_reached_500_iterations']} kasus metode holdout; perubahan akhir per kasus tercatat di CSV rinci.

{chr(10).join(sup_lines)}

Jenis yang memenuhi aturan: {', '.join(c1['improved_mask_kinds']) or 'tidak ada'}. Topeng TND mempunyai {len(tnd)} baris ringkasan metode–stasiun–bulan:

{chr(10).join(tnd_lines)}

Grafik TND ada pada `F3A_figure2_TND.png`, dengan galat dan fraksi tanpa keluaran. Gambar 1 memuat kurva galat dan batas ε. Tidak ada klaim E2/E3 atau judul Fase 3 yang diputuskan pada Tugas A.

## Reproduksi dan batas

Paket `auto_sqpca/` menyediakan loader, LT, tiga metode celah, inti PCA V1 beku, tujuh kandidat, surrogate, bootstrap, abstain, SSB, dan metrik. Titik masuk CLI awal ialah `python -m phase3.auto_sqpca.cli f3a` setelah memasang `phase3/requirements.txt`; skrip menolak menjalankan ulang holdout jika CSV-nya sudah ada. **CLI awal belum memasukkan koreksi GFZ 2018**, sehingga untuk mereproduksi hasil akhir perlu menjalankan skrip `f3_gfz2018.py` dan `f3_e1_2018_correction.py`, lalu evaluator serta finalizer seperti dicatat di log. Ini keterbatasan reproduksi satu perintah akibat kode E1 beku tidak diubah setelah holdout. Versi Python/NumPy inti serta lingkungan gambar tercatat di `F3A_environment.json`. Kasus tanpa keluaran diberi galat ∞ agar batas aman dan perbandingan tidak tampak lebih baik akibat penghapusan kasus gagal. Kebenaran E1 adalah keluaran lengkap bulan yang sama, sehingga E1 mengukur ketahanan terhadap topeng, bukan akurasi Sq alami.
"""
    write("F3A_report.md",report)
    validation={"schema":"Auto-SqPCA-F3A-v1","completed_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "protocol_sha256":protocol_sha,"E1_frozen_sha256":freeze_hash,"E1_method":selected,
        "frozen_phase1_phase2_files_unchanged":frozen_count,"new_hourly_archives_hash_verified":len(downloaded),
        "synthetic_T1_T8_all_pass":True,"M_EM_precision_deviation_nT":1e-8,
        "inventory_station_months":len(inventory),"E1_QC_eligible_months":sum(r['eligible_E1']=='True' for r in inventory),
        "development_truth_counts":dict(truth_counts_dev),"holdout_truth_counts":dict(truth_counts_hold),
        "holdout_recovery":recovery,"GFZ2018_input_correction":correction,
        "GFZ2018_sha256":gfz2018["sha256"],"C1":c1,"G1":"HOLD","G2R":"S-DEVIATE","G4R":"D-AGREE"}
    write("F3A_validation.json",json.dumps(validation,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    with (OUT/"F3A_execution.log").open("a",encoding="utf-8") as f:
        f.write(f"{dt.datetime.now(dt.timezone.utc).isoformat()} F3A finalization: method={selected}, C1={c1['C1_success']}, frozen_hash={freeze_hash}\n")
    exclude_names={"F3A_review.zip","F3A_review.zip.sha256","F3A_checksums.sha256"}
    included=sorted(p for p in OUT.rglob("*") if p.is_file() and p.name not in exclude_names and
                    not any(x in {"raw","work","__pycache__",".pytest_cache","_deps"} for x in p.relative_to(OUT).parts))
    write("F3A_checksums.sha256","".join(f"{sha(p)}  {p.relative_to(OUT).as_posix()}\n" for p in included))
    archive=OUT/"F3A_review.zip"
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in included+[OUT/"F3A_checksums.sha256"]:
            info=zipfile.ZipInfo(p.relative_to(OUT).as_posix(),date_time=(2026,11,14,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(archive) as z:
        bad=z.testzip()
        if bad:raise RuntimeError(f"F3A ZIP CRC failure: {bad}")
        if any("raw/" in n or "work/" in n for n in z.namelist()):raise RuntimeError("F3A ZIP contains raw/work data")
    write("F3A_review.zip.sha256",f"{sha(archive)}  F3A_review.zip\n")
    print(f"F3A_review.zip {archive.stat().st_size} bytes SHA-256 {sha(archive)}")


if __name__=="__main__":main()
