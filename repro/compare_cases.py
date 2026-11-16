"""Compare regenerated case CSVs by stable case identity, not worker completion order.

Predeclared finite-number tolerances: relative 1e-10, absolute 1e-12.
These accommodate double-precision library order effects while remaining far
below manuscript rounding precision; categorical fields must match exactly.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

RTOL=1e-10
ATOL=1e-12

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def read(path: Path, keys: tuple[str,...]) -> tuple[dict[tuple[str,...],dict],list[str]]:
    opener=gzip.open if path.suffix == ".gz" else Path.open
    with opener(path,"rt",newline="",encoding="utf-8") as f:
        reader=csv.DictReader(f)
        fields=reader.fieldnames or []
        rows={}
        for row in reader:
            key=tuple(row[x] for x in keys)
            if key in rows:
                raise RuntimeError(f"Duplicate key {key} in {path}")
            rows[key]=row
    return rows,fields

def equal(a: str,b: str) -> tuple[bool,float|None]:
    if a==b:
        try:float(a)
        except ValueError:return True,None
        return True,0.0
    try:
        x,y=float(a),float(b)
    except ValueError:
        return False,None
    if math.isnan(x) and math.isnan(y):return True,0.0
    if math.isinf(x) or math.isinf(y):return x==y,None
    return math.isclose(x,y,rel_tol=RTOL,abs_tol=ATOL),abs(x-y)

def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--rerun",type=Path,required=True)
    p.add_argument("--key",action="append",required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    keys=tuple(a.key)
    old,old_fields=read(a.original,keys)
    new,new_fields=read(a.rerun,keys)
    missing=sorted(set(old)-set(new))
    extra=sorted(set(new)-set(old))
    field_only_old=sorted(set(old_fields)-set(new_fields))
    field_only_new=sorted(set(new_fields)-set(old_fields))
    common=[f for f in old_fields if f in new_fields]
    mismatches=[]
    max_numeric={}
    numeric_checks=0
    for key in sorted(set(old)&set(new)):
        for field in common:
            same,difference=equal(old[key][field],new[key][field])
            if difference is not None:
                numeric_checks+=1
                max_numeric[field]=max(max_numeric.get(field,0.0),difference)
            if not same:
                mismatches.append({"key":key,"field":field,"original":old[key][field],
                    "rerun":new[key][field],"absolute_difference":difference})
    result={"original":str(a.original),"rerun":str(a.rerun),"keys":keys,
        "original_sha256":sha(a.original),"rerun_sha256":sha(a.rerun),
        "original_rows":len(old),"rerun_rows":len(new),"common_rows":len(set(old)&set(new)),
        "missing_keys":missing[:50],"missing_key_count":len(missing),
        "extra_keys":extra[:50],"extra_key_count":len(extra),
        "fields_only_original":field_only_old,"fields_only_rerun":field_only_new,
        "rtol":RTOL,"atol":ATOL,"numeric_checks":numeric_checks,
        "max_abs_difference_by_field":max_numeric,
        "mismatch_count":len(mismatches),"mismatches_first_50":mismatches[:50],
        "pass":not (missing or extra or field_only_old or field_only_new or mismatches)}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("original_rows","rerun_rows","numeric_checks","mismatch_count","pass")},indent=2))
    if not result["pass"]:raise SystemExit(1)

if __name__=="__main__":main()
