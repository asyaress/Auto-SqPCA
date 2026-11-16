"""Stage and execute the frozen Phase 3 workflow at explicit filesystem roots.

This wrapper changes paths and records execution only.  Scientific scripts,
thresholds, seeds and frozen configurations are copied without modification.
Third-party data are supplied by the caller and never put in a Git archive.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

SOURCE = Path(__file__).resolve().parents[1]
DATA_DIRS = ("phase2a", "phase3/raw", "audit_sq_wdc/cache", "audit_final")
REGENERATED = {Path("phase3/F3_E3_cases.csv")}
STAGES = {
    "inventory": ["f3_inventory.py"],
    "ssb": ["f3b_ssb.py"],
    "e1_holdout": ["f3_e1.py", "holdout"],
    "e1_evaluate": ["f3_e1_eval.py"],
    "e1_secondary": ["../repro/e1_secondary_portable.py"],
    "e2_development": ["f3b_e2_cases.py", "development"],
    "e2_holdout": ["f3b_e2_cases.py", "holdout"],
    "e2_evaluate": ["f3b_e2_eval.py"],
    "e3b_prepare": ["f3b_e3b_prep.py"],
    "e3": ["f3b_e3.py"],
    "e3_summary": ["f3b_e3_summary.py"],
    "figures": ["f3b_figures.py"],
}


def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def copy_verified(source: Path, target: Path) -> str:
    source_sha=sha(source)
    if target.exists():
        if source_sha != sha(target):
            raise RuntimeError(f"Existing staged file differs: {target}")
        return source_sha
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    if source_sha != sha(target):
        raise RuntimeError(f"Stage copy SHA-256 mismatch: {source} -> {target}")
    return source_sha


def prepare(input_root: Path, output_root: Path) -> None:
    input_root=input_root.resolve()
    output_root=output_root.resolve()
    if output_root.is_relative_to(SOURCE.resolve()) or output_root.is_relative_to(input_root):
        raise ValueError("Output root must lie outside source and input roots")
    output_root.mkdir(parents=True,exist_ok=True)
    tracked=subprocess.check_output(["git","ls-files","-z"],cwd=SOURCE).split(b"\0")
    count=0
    for item in tracked:
        if not item: continue
        rel=Path(os.fsdecode(item))
        if rel in REGENERATED:
            continue
        src=SOURCE/rel
        if not src.is_file():
            raise FileNotFoundError(src)
        copy_verified(src,output_root/rel)
        count+=1
    input_count=0
    input_manifest=[]
    for rel in DATA_DIRS:
        base=input_root/rel
        if not base.is_dir():
            raise FileNotFoundError(f"Required input directory absent: {base}")
        for src in sorted(base.rglob("*")):
            if src.is_file() and not any(part in {"__pycache__","_deps",".pytest_cache"} for part in src.relative_to(base).parts):
                digest=copy_verified(src,output_root/src.relative_to(input_root))
                input_manifest.append({"relative_path":src.relative_to(input_root).as_posix(),
                                       "sha256":digest,"size_bytes":src.stat().st_size})
                input_count+=1
    # The frozen E1 reader expects all GFZ years under phase2a/raw/gfz, while
    # the later authenticated 2018 acquisition lives under phase3/raw/gfz.
    # Supply the same bytes at that legacy lookup path only in the output root.
    gfz_source=output_root/"phase3/raw/gfz/QD_days2018.txt"
    gfz_lookup=output_root/"phase2a/raw/gfz/QD_days2018.txt"
    source_record=json.loads((output_root/"phase3/F3_GFZ2018_source.json").read_text(encoding="utf-8"))
    if source_record["sha256"] != sha(gfz_source) or source_record["months_validated"] != 12:
        raise RuntimeError("GFZ 2018 source hash/validation mismatch")
    gfz_digest=copy_verified(gfz_source,gfz_lookup)
    with (output_root/"reproduction_input_manifest.csv").open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=("relative_path","sha256","size_bytes"))
        writer.writeheader();writer.writerows(input_manifest)
    # The original preflight, still unmodified, verifies 161 frozen files and
    # the hashes of the Phase 1 minute archives.
    check=subprocess.run([sys.executable,"-c","from f3_preflight import verify_snapshot; print(verify_snapshot())"],
        cwd=output_root/"phase3",text=True,capture_output=True)
    if check.returncode:
        raise RuntimeError(f"Frozen preflight failed: {check.stderr.strip()}")
    meta={"prepared_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
          "source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=SOURCE,text=True).strip(),
          "source_dirty":bool(subprocess.check_output(["git","status","--porcelain"],cwd=SOURCE)),
          "wrapper_sha256":sha(Path(__file__)),
          "source_root":str(SOURCE),"input_root":str(input_root),"output_root":str(output_root),
          "python":sys.version,"tracked_files":count,"input_files":input_count,
          "input_manifest_sha256":sha(output_root/"reproduction_input_manifest.csv"),
          "gfz2018_legacy_lookup_path":str(gfz_lookup.relative_to(output_root)),
          "gfz2018_legacy_lookup_sha256":gfz_digest,
          "gfz2018_adapter_note":"Byte-identical copy of authenticated GFZ 2018 file to the frozen E1 reader's legacy lookup path in the output root only.",
          "frozen_preflight_files":int(check.stdout.strip())}
    (output_root/"reproduction_setup.json").write_text(json.dumps(meta,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(meta,indent=2))


def run(output_root: Path, names: list[str], workers: int) -> None:
    output_root=output_root.resolve()
    if not (output_root/"reproduction_setup.json").is_file():
        raise FileNotFoundError("Run prepare first; reproduction_setup.json absent")
    logs=output_root/"reproduction_logs"
    logs.mkdir(exist_ok=True)
    environment=os.environ.copy()
    environment["F3_WORKERS"]=str(workers)
    seen=Counter()
    for name in names:
        if name not in STAGES:
            raise ValueError(f"Unknown stage {name}; choose from {list(STAGES)}")
        command=[sys.executable,*STAGES[name]]
        start=time.perf_counter()
        seen[name]+=1
        log_name=f"{name}{'_'+str(seen[name]) if seen[name]>1 else ''}"
        log_path=logs/f"{log_name}.log"
        if log_path.exists():raise FileExistsError(f"Stage log already exists: {log_path}")
        with log_path.open("w",encoding="utf-8") as f:
            f.write(f"command={command!r}\nworkers={workers}\n")
            f.flush()
            process=subprocess.run(command,cwd=output_root/"phase3",env=environment,
                stdout=f,stderr=subprocess.STDOUT)
        record={"stage":name,"occurrence":seen[name],"command":command,"workers":workers,"exit_code":process.returncode,
                "elapsed_seconds":round(time.perf_counter()-start,3),
                "log_sha256":sha(log_path)}
        (logs/f"{log_name}.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(record),flush=True)
        if process.returncode:
            raise RuntimeError(f"Stage {name} failed; original output: {log_path}")


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="action",required=True)
    p=sub.add_parser("prepare")
    p.add_argument("--input-root",type=Path,required=True)
    p.add_argument("--output-root",type=Path,required=True)
    p=sub.add_parser("run")
    p.add_argument("--output-root",type=Path,required=True)
    p.add_argument("--stages",required=True,help="Comma-separated stage names in execution order")
    p.add_argument("--workers",type=int,default=4)
    args=parser.parse_args()
    if args.action=="prepare": prepare(args.input_root,args.output_root)
    else: run(args.output_root,[x.strip() for x in args.stages.split(",")],args.workers)

if __name__=="__main__": main()
