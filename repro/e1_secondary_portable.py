"""Run frozen E1 secondary metrics after order-independent case verification.

The original secondary script pins a byte hash from worker-dependent CSV row
order. This adapter changes that guard to the verified rerun hash; the metric
code, inputs, thresholds and seeds are otherwise unmodified.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

REPO=Path.cwd().parent
SCRIPTS=Path(__file__).resolve().parent
ARCHIVE=REPO/"results/phase3/F3_E1_holdout_cases.csv.gz"
RERUN=REPO/"phase3/work/E1_holdout_cases.csv"
LOGS=REPO/"reproduction_logs"
LOGS.mkdir(exist_ok=True)
COMPARISON=LOGS/"E1_comparison.json"
DATABASE=LOGS/"E1_comparison.sqlite"

if DATABASE.exists():
    raise RuntimeError(f"Previous comparison database exists: {DATABASE}")
command=[sys.executable,str(SCRIPTS/"compare_large_cases.py"),
         "--original",str(ARCHIVE),"--rerun",str(RERUN),
         "--database",str(DATABASE),"--output",str(COMPARISON)]
subprocess.run(command,check=True)
result=json.loads(COMPARISON.read_text(encoding="utf-8"))
if not result["pass"]:raise RuntimeError("E1 case comparison did not pass")
DATABASE.unlink()

sys.path.insert(0,str(REPO/"phase3"))
import f3b_e1_secondary as original  # noqa: E402
original.EXPECTED=result["rerun_sha256"]
original.main()
record={"level":"VERIFIED_ORDER_ADAPTER","original_script":"phase3/f3b_e1_secondary.py",
        "comparison_sha256":original.sha(COMPARISON),
        "rerun_cases_sha256":result["rerun_sha256"],
        "original_archived_cases_sha256":result["original_sha256"],
        "original_script_sha256":original.sha(REPO/"phase3/f3b_e1_secondary.py"),
        "adapter_script_sha256":original.sha(Path(__file__)),
        "scope":"Only the byte-hash guard is replaced after matching every case by identity; numeric metric code is unchanged."}
(LOGS/"E1_secondary_adapter.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
print(json.dumps(record,indent=2))
