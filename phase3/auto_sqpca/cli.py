"""Single command entry point for the Phase 3 Task A workflow.

On a fresh workspace containing frozen Phase 1-2 data and this package:
    python -m phase3.auto_sqpca.cli f3a
Existing E1 outputs are protected against accidental holdout reruns.
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PHASE3 = ROOT / "phase3"


def run(args: list[str], env: dict | None = None) -> None:
    print("RUN", " ".join(map(str,args)), flush=True)
    subprocess.run(args, cwd=ROOT, env=env, check=True)


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("f3a", "verify"):
        raise SystemExit("Usage: python -m auto_sqpca.cli f3a|verify")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join((str(ROOT / "phase2a/G2R/_deps"), str(PHASE3), env.get("PYTHONPATH", "")))
    if sys.argv[1] == "verify":
        run([sys.executable, "-c", "import f3_preflight; print(f3_preflight.verify_snapshot())"], env)
        return
    run([sys.executable, str(PHASE3 / "f3_preflight.py")], env)
    run([sys.executable, "-m", "pytest", str(PHASE3 / "tests"), "-q"], env)
    run([sys.executable, str(PHASE3 / "f3_acquire.py")], env)
    run([sys.executable, str(PHASE3 / "f3_inventory.py")], env)
    run([sys.executable, str(PHASE3 / "f3_e1.py"), "development"], env)
    run([sys.executable, str(PHASE3 / "f3_e1.py"), "holdout"], env)
    run([sys.executable, str(PHASE3 / "f3_e1_eval.py")], env)
    run([sys.executable, str(PHASE3 / "f3a_finalize.py")], env)


if __name__ == "__main__":
    main()
