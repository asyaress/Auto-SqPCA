"""Compare rendered figure pixels while retaining distinct file hashes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original-dir",type=Path,required=True)
    p.add_argument("--rerun-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("names",nargs="+")
    a=p.parse_args()
    rows=[]
    for name in a.names:
        old=a.original_dir/name;new=a.rerun_dir/name
        x=np.asarray(Image.open(old).convert("RGBA"))
        y=np.asarray(Image.open(new).convert("RGBA"))
        rows.append({"name":name,"original_sha256":sha(old),"rerun_sha256":sha(new),
                     "shape_original":x.shape,"shape_rerun":y.shape,
                     "pixel_equal":bool(np.array_equal(x,y))})
    a.output.write_text(json.dumps(rows,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(rows,indent=2))
    if not all(r["pixel_equal"] for r in rows):raise SystemExit(1)

if __name__=="__main__":main()
