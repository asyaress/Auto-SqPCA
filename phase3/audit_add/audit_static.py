"""Post-hoc descriptive audits U2, U4 and U6; writes only audit_add/."""
from __future__ import annotations

import calendar
import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PHASE3 = HERE.parent
ROOT = PHASE3.parent
TAG = "EXPLORATORY_POST_HOC"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rows(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


def write_csv(name: str, data: list[dict], fields: list[str]) -> None:
    with (HERE / name).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(data)


def number(s: str, default=float("inf")) -> float:
    try:
        x = float(s)
        return x if not math.isnan(x) else default
    except (ValueError, TypeError):
        return default


def q90(a: np.ndarray) -> float:
    return float(np.quantile(a, .9, method="higher"))


def ratio(a: float, b: float) -> float:
    return a / b if math.isfinite(a) and math.isfinite(b) and b > 0 else float("nan")


def u2() -> None:
    # The requested gzip is absent. This uncompressed E1 output is authenticated
    # by the frozen F3_C1_result.json, itself covered by F3B_checksums.sha256.
    source = PHASE3 / "work/E1_holdout_cases.csv"
    c1_path = PHASE3 / "F3_C1_result.json"
    c1 = json.loads(c1_path.read_text(encoding="utf-8"))
    assert sha(source) == c1["holdout_cases_sha256"]
    expected = next(line.split()[0] for line in (PHASE3 / "F3B_checksums.sha256").read_text().splitlines()
                    if line.endswith("  F3_C1_result.json"))
    assert sha(c1_path) == expected
    settings = {("MCAR", .05), ("MCAR", .10), ("BLOCK6", .10),
                ("BLOCK24", .10), ("BLOCK72", .10), ("DAY", .10)}
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for r in rows(source):
        if r["split"] != "holdout":
            continue
        setting = (r["mask_kind"], number(r["p_nominal"]))
        if setting not in settings:
            continue
        key = (r["station"], r["year"], r["month"])
        data[setting][key][r["method"]].append(number(r["error_relative_l2"]))
    output = []
    for setting in sorted(settings):
        clusters = data[setting]
        keys = sorted(clusters)
        for comparator in ("M-INT", "M-EXC"):
            em = [np.array(clusters[k]["M-EM"], float) for k in keys]
            co = [np.array(clusters[k][comparator], float) for k in keys]
            if any(len(x) != len(y) or not len(x) for x, y in zip(em, co)):
                raise RuntimeError(f"U2 paired cluster mismatch {setting} {comparator}")
            ae, ac = np.concatenate(em), np.concatenate(co)
            med = ratio(float(np.median(ae)), float(np.median(ac)))
            p90 = ratio(q90(ae), q90(ac))
            rng = np.random.default_rng(20261115)
            boots_med, boots_p90 = [], []
            for _ in range(2000):
                ids = rng.integers(0, len(keys), size=len(keys))
                be = np.concatenate([em[i] for i in ids])
                bc = np.concatenate([co[i] for i in ids])
                boots_med.append(ratio(float(np.median(be)), float(np.median(bc))))
                boots_p90.append(ratio(q90(be), q90(bc)))
            def ci(x):
                a = np.array(x)
                return tuple(float(v) for v in np.quantile(a, [.025, .975])) if np.isfinite(a).all() else (float("nan"), float("nan"))
            cm = ci(boots_med)
            cp = ci(boots_p90)
            output.append({"audit_label": TAG, "mask_kind": setting[0], "p_nominal": setting[1],
                           "comparison": f"M-EM/{comparator}", "n_station_months": len(keys),
                           "n_cases_per_method": len(ae), "median_error_ratio": med,
                           "median_ratio_ci95_low": cm[0], "median_ratio_ci95_high": cm[1],
                           "p90_error_ratio": p90, "p90_ratio_ci95_low": cp[0],
                           "p90_ratio_ci95_high": cp[1],
                           "M_EM_no_output_fraction": float(np.isinf(ae).mean()),
                           "comparator_no_output_fraction": float(np.isinf(ac).mean()),
                           "source": "work/E1_holdout_cases.csv (authenticated alternate; requested F3_E1_holdout_cases.csv.gz missing)"})
    write_csv("U2_operating_range_ratios.csv", output, list(output[0]))


def u4() -> None:
    groups = defaultdict(list)
    counts = defaultdict(lambda: [0, 0])
    case_output = []
    for r in rows(PHASE3 / "F3_E3_cases.csv"):
        key = (r["station"], r["component"])
        counts[key][0] += 1
        if r["abstained"] == "True" or r["status"] != "OK":
            counts[key][1] += 1
            continue
        path = ROOT / r["curve_cache_path"]
        if sha(path) != r["curve_cache_sha256"]:
            raise RuntimeError(f"U4 curve cache SHA-256 mismatch: {path}")
        with np.load(path, allow_pickle=False) as z:
            auto, difi, iqd = z["AUTO"], z["DIFI8"], z["IQD"]
        if any(x.shape != (24,) or not np.isfinite(x).all() for x in (auto, difi, iqd)):
            raise RuntimeError(f"U4 invalid curve: {path}")
        rmse = float(np.sqrt(np.mean((auto - difi) ** 2)))
        amp = float(np.ptp(difi))
        ra = float(np.corrcoef(auto, iqd)[0, 1])
        rd = float(np.corrcoef(auto, difi)[0, 1])
        if abs(ra - float(r["r_AUTO_IQD_nonindependent"])) > 1e-10 or abs(rd - float(r["r_AUTO_DIFI"])) > 1e-10:
            raise RuntimeError(f"U4 correlation mismatch: {path}")
        groups[key].append((rmse, rmse / amp if amp > 0 else float("nan"), ra, rd))
        case_output.append({"audit_label": TAG, "scope": r["scope"], "station": r["station"],
                            "year": r["year"], "month": r["month"], "component": r["component"],
                            "rmse_nT": rmse, "normalized_rmse": rmse / amp if amp > 0 else float("nan"),
                            "DIFI_amplitude_nT": amp, "r_AUTO_IQD_signed": ra,
                            "r_AUTO_DIFI_signed": rd, "curve_cache_path": r["curve_cache_path"],
                            "curve_cache_sha256": r["curve_cache_sha256"]})
    output = []
    for key, (total, abstained) in sorted(counts.items()):
        a = np.array(groups[key], float)
        if len(a):
            lo, hi = np.quantile(a[:, 0], [.25, .75])
            output.append({"audit_label": TAG, "station": key[0], "component": key[1],
                           "n_cases": total, "n_accepted": len(a), "abstain_fraction": abstained / total,
                           "rmse_nT_median": float(np.median(a[:, 0])), "rmse_nT_q25": float(lo),
                           "rmse_nT_q75": float(hi), "normalized_rmse_median": float(np.median(a[:, 1])),
                           "n_r_AUTO_IQD_negative": int((a[:, 2] < 0).sum()),
                           "r_AUTO_IQD_median": float(np.median(a[:, 2])),
                           "r_AUTO_DIFI_median": float(np.median(a[:, 3]))})
        else:
            output.append({"audit_label": TAG, "station": key[0], "component": key[1],
                           "n_cases": total, "n_accepted": 0, "abstain_fraction": abstained / total,
                           "rmse_nT_median": "", "rmse_nT_q25": "", "rmse_nT_q75": "",
                           "normalized_rmse_median": "", "n_r_AUTO_IQD_negative": 0,
                           "r_AUTO_IQD_median": "", "r_AUTO_DIFI_median": ""})
    write_csv("U4_rmse_by_station_component.csv", output, list(output[0]))
    write_csv("U4_rmse_cases.csv", case_output, list(case_output[0]))


def u6() -> None:
    inv = list(rows(PHASE3 / "F3_data_inventory.csv")) + list(rows(PHASE3 / "F3_E3b_inventory.csv"))
    leap = []
    for r in inv:
        y, m = int(r["year"]), int(r["month"])
        if m == 2 and calendar.isleap(y):
            path = ROOT / r["matrix_cache"]
            if sha(path) != r["matrix_cache_sha256"]:
                raise RuntimeError(f"U6 matrix cache SHA-256 mismatch: {path}")
            with np.load(path, allow_pickle=False) as z:
                shape = z["XYZ_nT"].shape
            leap.append((r["station"], y, shape))
    ssb_leap = []
    seen_ssb = set()
    for r in rows(PHASE3 / "F3_ssb_manifest.csv"):
        if r["split"] != "holdout" or int(r["month"]) != 2 or not calendar.isleap(int(r["year"])):
            continue
        key = (r["station"], int(r["year"]), r["cache_path"])
        if key in seen_ssb:
            continue
        seen_ssb.add(key)
        path = ROOT / r["cache_path"]
        if sha(path) != r["cache_sha256"]:
            raise RuntimeError(f"U6 SSB cache SHA-256 mismatch: {path}")
        with np.load(path, allow_pickle=False) as z:
            shape = z["residual_nT"].shape
        ssb_leap.append((r["station"], int(r["year"]), shape))
    gfz_2016 = ROOT / "phase2a/raw/gfz/QD_days2016.txt"
    gfz_record = next(r for r in rows(ROOT / "phase2a/G0/input_manifest.csv")
                      if r["relative_path"] == "phase2a/raw/gfz/QD_days2016.txt")
    if sha(gfz_2016) != gfz_record["sha256"]:
        raise RuntimeError(f"U6 GFZ 2016 SHA-256 mismatch: {gfz_2016}")
    feb_line = next(x for x in gfz_2016.read_text(encoding="utf-8").splitlines()
                    if re.match(r"^\s*Feb\s+2016\s", x))
    feb_iqd = [int(re.match(r"^\d+", x).group()) for x in feb_line.split()[2:7]]
    by_station = defaultdict(list)
    for r in inv:
        by_station[r["station"]].append(r)
    lines = ["# U6 — pemeriksaan fakta", "", f"Label: **{TAG}**.", "",
             "## 29 Februari", "",
             "**Tidak dibuang.** `auto_sqpca/localtime.py:20–35` fungsi `month_matrix` memakai `calendar.monthrange(year, month)[1]` lalu membentuk matriks `(24, N, 3)` tanpa pengecualian 29 Februari. `f3_inventory.py:67` dan `f3b_e3b_prep.py:50` memanggil fungsi tersebut; `f3_e1.py:104`, `f3b_ssb.py:73–94`, dan `f3b_e3.py:84` membaca cache hasilnya tanpa membuang kolom terakhir Februari. Ini bertentangan dengan pernyataan di naskah MethodsX yang menyebut 29 Februari dibuang dari matriks.", "",
             "| Stasiun | Tahun | Dimensi cache Februari |", "|---|---:|---|"]
    lines += [f"| {s} | {y} | {shape} |" for s, y, shape in sorted(leap)]
    lines += ["", "Cache E2 **holdout** Februari kabisat (`residual_nT`):", "",
              "| Stasiun | Tahun | Dimensi cache E2 |", "|---|---:|---|"]
    lines += [f"| {s} | {y} | {shape} |" for s, y, shape in sorted(ssb_leap)]
    lines += ["", f"GFZ Februari 2016 Q1–Q5 yang dibaca dari `phase2a/raw/gfz/QD_days2016.txt`: **{feb_iqd}**. Karena `auto_sqpca/selection.py` fungsi `sq_iqd` memakai indeks `quiet_days − 1` pada matriks 29 kolom, hari 29 juga dapat dipakai dalam referensi IQD Fase 3."]
    lines += ["", "## Jam tepi deret UTC", "",
              "Deret tahunan disambung per stasiun sebelum pembentukan bulan lokal (`f3_inventory.py`, `f3b_e3b_prep.py`). Karena itu jam yang berada di luar deret yang dimuat hanya muncul pada tepi awal/akhir keseluruhan rentang tahun stasiun, bukan pada setiap bulan. Angka berikut adalah jam yang hilang *karena batas deret*, terpisah dari missing value observasi.", "",
              "| Stasiun | Rentang tahun dimuat | Pergeseran LT (jam) | Awal bulan lokal: kisaran jam di luar deret | Akhir bulan lokal: kisaran jam di luar deret | Tumpang tindih hari GFZ UTC vs hari lokal (jam/hari) |",
              "|---|---|---:|---:|---:|---:|"]
    for station, rr in sorted(by_station.items()):
        years = sorted({int(x["year"]) for x in rr})
        shifts = {int(x["delta_LT_hours"]) for x in rr}
        if len(shifts) != 1:
            raise RuntimeError(f"U6 multiple local shifts {station}: {shifts}")
        shift = shifts.pop()
        start, end = max(shift, 0), max(-shift, 0)
        lines.append(f"| {station} | {years[0]}–{years[-1]} | {shift:+d} | 0–{start} | 0–{end} | {24-abs(shift)} |")
    lines += ["", "Tumpang tindih dihitung sebagai panjang irisan satu hari UTC GFZ (00:00–24:00 UTC) dengan hari lokal bertanggal sama setelah pergeseran integer `round(longitude/15)`; rumusnya `24 − |ΔLT|` jam. Ini kesesuaian waktu, bukan bukti kelengkapan data pada jam tersebut.", ""]
    (HERE / "U6_facts.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    u2()
    u4()
    u6()
