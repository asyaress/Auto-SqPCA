"""Portable commands for a source clone.

Historical F3 scripts and results stay under phase3/. Rebuilding them requires
separately acquired raw data and is not an implicit side effect of these checks.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("demo", "verify"))
    parser.add_argument("--output", type=Path, help="demo output directory")
    args = parser.parse_args()
    if args.command == "demo":
        command = [sys.executable, str(ROOT / "demo/synthetic_month.py")]
        if args.output is not None:
            command += ["--output", str(args.output)]
    else:
        command = [sys.executable, "-m", "pytest", "-q", str(ROOT / "tests")]
    subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
