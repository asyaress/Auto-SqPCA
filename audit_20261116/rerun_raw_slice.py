"""Rebuild GUA January 2014 monthly matrix from authenticated raw WDC hourly ZIP."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO.parents[1]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "phase3"))
from auto_sqpca.io import load_hourly_zip  # noqa: E402
from auto_sqpca.localtime import month_matrix  # noqa: E402
from auto_sqpca.gaps import apply  # noqa: E402


def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()


def main() -> None:
    with (REPO / "phase3/F3_data_inventory.csv").open(newline="",encoding="utf-8") as f:
        row=next(r for r in csv.DictReader(f) if r["station"]=="GUA" and r["year"]=="2014" and r["month"]=="1")
    raw=PROJECT / row["source_path"]
    assert sha(raw)==row["source_sha256"]
    loaded=load_hourly_zip(raw,"GUA",2014)
    matrix=month_matrix(loaded["values"],dt.datetime(2014,1,1),loaded["longitude"],2014,1)
    cache=PROJECT / row["matrix_cache"]
    assert sha(cache)==row["matrix_cache_sha256"]
    archived=np.load(cache,allow_pickle=False)["XYZ_nT"]
    same=bool(np.array_equal(matrix,archived,equal_nan=True))
    filled=np.empty_like(matrix)
    iterations=[]
    for c in range(3):
        v,keep,info=apply(matrix[:,:,c],"M-EM")
        assert keep.all() and v.shape==(24,31)
        filled[:,:,c]=v
        iterations.append(info["iterations"])
    centered=filled-filled.mean(axis=0,keepdims=True)
    residual=centered-centered.mean(axis=1,keepdims=True)
    ssb_cache=PROJECT / "phase3/work/ssb_months/GUA_2014_01.npz"
    z=np.load(ssb_cache,allow_pickle=False)
    filled_same=bool(np.array_equal(filled,z["filled_observation_nT"]))
    residual_same=bool(np.array_equal(residual,z["residual_nT"]))
    result={"verification_level":"TARGETED_RAW_WDC_TO_MATRIX_RERUN", "station":"GUA",
        "year":2014,"month":1,"raw_zip_project_relative_path":raw.relative_to(PROJECT).as_posix(),"raw_zip_sha256":sha(raw),
        "archived_matrix_sha256":sha(cache),"shape":matrix.shape,
        "finite_xyz_hours":int(np.isfinite(matrix).all(axis=2).sum()),
        "matrix_equal_including_nan":same,"SSB_cache_sha256":sha(ssb_cache),
        "M_EM_iterations_XYZ":iterations,"SSB_filled_equal":filled_same,
        "SSB_residual_equal":residual_same}
    (OUT / "rerun_raw_slice.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
    assert same and filled_same and residual_same


if __name__=="__main__":main()
