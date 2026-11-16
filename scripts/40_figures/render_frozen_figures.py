"""Run the archived F3B renderer against byte-identical frozen CSV/JSON copies.

The renderer's own output path is tied to its script location. Working in a
temporary directory keeps the checked-in figures and results untouched.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "phase3"
INPUTS = ("F3_E2_risk_coverage.csv", "F3_E2_result.json", "F3_E2_C3.json",
          "F3_E3_cases.csv", "F3_E3_examples.json")
E1_INPUTS = ("F3_E1_holdout_summary.csv", "F3_E1_TND_summary.csv", "F3_E1_pstar.csv")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "output")
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for name in INPUTS:
        assert sha(SOURCE / name) == sha(ROOT / "results/phase3" / name)
    for name in E1_INPUTS:
        assert sha(SOURCE / name) == sha(ROOT / "results/phase3" / name)
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        shutil.copyfile(SOURCE / "f3b_figures.py", work / "f3b_figures.py")
        for name in INPUTS:
            shutil.copyfile(ROOT / "results/phase3" / name, work / name)
        subprocess.run([sys.executable, str(work / "f3b_figures.py")], cwd=work, check=True)
        for name in ("F3B_figure3_risk_coverage.png", "F3B_figure4_E3_latitude.png", "F3B_figure5_examples.png"):
            shutil.copyfile(work / name, args.output / name)
            print(f"{name}: {sha(args.output / name)}")
    with tempfile.TemporaryDirectory() as td:
        work = Path(td) / "phase3"
        work.mkdir()
        for name in ("f3_e1_eval.py", "f3_preflight.py"):
            shutil.copyfile(SOURCE / name, work / name)
        for name in E1_INPUTS:
            shutil.copyfile(ROOT / "results/phase3" / name, work / name)
        code = (
            "import csv, pathlib, f3_e1_eval as e; p=pathlib.Path('.'); "
            "rows=lambda n:list(csv.DictReader((p/n).open(encoding='utf-8',newline=''))); "
            "s=rows('F3_E1_holdout_summary.csv'); t=rows('F3_E1_TND_summary.csv'); "
            "s=[{**r,'p':float(r['p']),'median_error':float(r['median_error']) if r['median_error'] else None} for r in s]; "
            "t=[{**r,'month':int(r['month']),'n':int(r['n']),'nonfinite_errors':int(r['nonfinite_errors']),'median_error':float(r['median_error']) if r['median_error'] else None} for r in t]; "
            "e.figures(s,t,'M-EM')"
        )
        subprocess.run([sys.executable, "-c", code], cwd=work, check=True)
        for name in ("F3A_figure1_error_curves.png", "F3A_figure2_TND.png"):
            shutil.copyfile(work / name, args.output / name)
            print(f"{name}: {sha(args.output / name)}")
    with (ROOT / "results/phase3/F3_E2_risk_coverage.csv").open(encoding="utf-8", newline="") as f:
        print(f"risk-coverage rows: {len(list(csv.DictReader(f)))}")
    with (ROOT / "results/phase3/F3_E3_cases.csv").open(encoding="utf-8", newline="") as f:
        print(f"E3 cases: {len(list(csv.DictReader(f)))}")
    with (ROOT / "results/phase3/F3_E1_holdout_summary.csv").open(encoding="utf-8", newline="") as f:
        print(f"E1 summary rows: {len(list(csv.DictReader(f)))}")


if __name__ == "__main__":
    main()

