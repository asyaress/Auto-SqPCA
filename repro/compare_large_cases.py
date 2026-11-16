"""Disk-backed, order-independent E1 comparison against a gzipped case archive.

The finite-number tolerance is fixed before inspection: rel=1e-10, abs=1e-12.
Keep the temporary SQLite file outside the small review package.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import sqlite3
from pathlib import Path

KEYS=("split","station","year","month","component","mask_family",
      "mask_kind","p_nominal","block_length","replicate","method")
RTOL=1e-10
ATOL=1e-12

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()

def reader(path:Path):
    opener=gzip.open if path.suffix==".gz" else Path.open
    with opener(path,"rt",encoding="utf-8",newline="") as f:
        yield from csv.DictReader(f)

def equal(a:str,b:str):
    if a==b:
        try:float(a)
        except ValueError:return True,None
        return True,0.0
    try:x,y=float(a),float(b)
    except ValueError:return False,None
    if math.isnan(x) and math.isnan(y):return True,0.0
    if math.isinf(x) or math.isinf(y):return x==y,None
    return math.isclose(x,y,rel_tol=RTOL,abs_tol=ATOL),abs(x-y)

def main():
    p=argparse.ArgumentParser()
    for name in ("original","rerun","database","output"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    a.database.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(a.database)
    try:
        con.execute("CREATE TABLE IF NOT EXISTS original (k TEXT PRIMARY KEY, row TEXT NOT NULL, seen INTEGER DEFAULT 0)")
        if con.execute("SELECT COUNT(*) FROM original").fetchone()[0]:
            raise RuntimeError("Comparison database is not empty")
        old_count=0
        for row in reader(a.original):
            key=json.dumps([row[k] for k in KEYS],separators=(",",":"))
            con.execute("INSERT INTO original(k,row) VALUES (?,?)",(key,json.dumps(row,separators=(",",":"))))
            old_count+=1
            if old_count%10000==0:con.commit()
        con.commit()
        new_count=0; extra=0; mismatches=[]; mismatch_count=0; numeric_checks=0
        max_abs={}; status_old={}; status_new={}
        for row in reader(a.rerun):
            key=json.dumps([row[k] for k in KEYS],separators=(",",":"))
            found=con.execute("SELECT row,seen FROM original WHERE k=?",(key,)).fetchone()
            new_count+=1
            status_new[row["status"]]=status_new.get(row["status"],0)+1
            if found is None:
                extra+=1
                if len(mismatches)<50:mismatches.append({"key":key,"type":"extra"})
                continue
            if found[1]:raise RuntimeError(f"Duplicate rerun key: {key}")
            old=json.loads(found[0])
            status_old[old["status"]]=status_old.get(old["status"],0)+1
            if old.keys()!=row.keys():raise RuntimeError(f"Field mismatch for {key}")
            for field in old:
                same,diff=equal(old[field],row[field])
                if diff is not None:
                    numeric_checks+=1
                    max_abs[field]=max(max_abs.get(field,0.0),diff)
                if not same:
                    mismatch_count+=1
                    if len(mismatches)<50:mismatches.append({"key":key,"field":field,"old":old[field],"new":row[field],"abs_difference":diff})
            con.execute("UPDATE original SET seen=1 WHERE k=?",(key,))
            if new_count%10000==0:con.commit()
        con.commit()
        missing=con.execute("SELECT COUNT(*) FROM original WHERE seen=0").fetchone()[0]
        result={"original_sha256":sha(a.original),"rerun_sha256":sha(a.rerun),
            "original_rows":old_count,"rerun_rows":new_count,"key_fields":KEYS,
            "missing_keys":missing,"extra_keys":extra,"mismatch_count":mismatch_count,
            "mismatches_first_50":mismatches,"numeric_checks":numeric_checks,
            "max_abs_difference_by_field":max_abs,"status_original":status_old,"status_rerun":status_new,
            "rtol":RTOL,"atol":ATOL,"pass":not(missing or extra or mismatch_count)}
        a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({k:result[k] for k in ("original_rows","rerun_rows","missing_keys","extra_keys","mismatch_count","pass")},indent=2))
        if not result["pass"]:raise SystemExit(1)
    finally:con.close()

if __name__=="__main__":main()
