"""F3-v1 Task A E1: deterministic masks, development selection, frozen holdout."""
from __future__ import annotations
import csv
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import numpy as np

from auto_sqpca import gaps, pca, candidates, selection, metrics
from f3_preflight import ROOT, OUT, sha, verify_snapshot

SEED = 20261114
WORK = OUT / "work"
METHODS = ("M-INT","M-EXC","M-EM")
CASE_FIELDS = ["split","station","year","month","component","mask_family","mask_kind","p_nominal","p_actual","block_length","replicate","mask_seed","method","status","error_original","error_relative_l2","fixed_candidate_error","pc1_angle_deg","candidate_agree","selected_candidate","truth_candidate","days_kept","observed_fraction","em_iterations","em_final_change_nT"]
SETTINGS = [("MCAR","MCAR",p,None,20) for p in (.05,.10,.20,.30,.40,.50)] + \
           [("BLOCK",f"BLOCK{length}",p,length,20) for length in (6,24,72) for p in (.10,.20,.30,.40)] + \
           [("DAY","DAY",p,None,20) for p in (.10,.20,.30,.40)] + [("TND","TND",None,None,1)]


def csv_read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8",newline="") as f: return list(csv.DictReader(f))


def csv_write(path: Path, data: list[dict], fields: list[str]) -> None:
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(data)


def jwrite(path: Path, data: object) -> None:
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")


def log(s: str) -> None:
    import datetime as dt
    line=f"{dt.datetime.now(dt.timezone.utc).isoformat()} {s}"
    print(line,flush=True)
    with (OUT/"F3A_execution.log").open("a",encoding="utf-8") as f:f.write(line+"\n")


def gfz_days(year: int, month: int) -> list[int]:
    import re
    names=("Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec")
    path=ROOT/"phase2a/raw/gfz"/f"QD_days{year}.txt"
    line=next((x for x in path.read_text(encoding="utf-8").splitlines()
               if re.match(rf"^\s*{names[month-1]}\s+{year}\s",x)),None)
    if line is None: raise RuntimeError(f"GFZ QD missing {year}-{month:02d}")
    days=[int(re.match(r"^\d+",v).group()) for v in line.split()[2:7]]
    if len(days)!=5 or len(set(days))!=5: raise RuntimeError(f"GFZ Q1-Q5 invalid {year}-{month:02d}: {days}")
    return days


def stable_seed(*parts: object) -> int:
    digest=hashlib.sha256("|".join(map(str,(SEED,*parts))).encode()).hexdigest()
    return int(digest[:8],16)


def make_mask(kind: str,p: float|None,length: int|None,n_days: int,rep: int,
              station: str,year: int,month: int,tnd: np.ndarray|None) -> tuple[np.ndarray,int]:
    seed=stable_seed(station,year,month,kind,p,length,rep)
    rng=np.random.default_rng(seed)
    n=n_days*24
    if kind=="TND":
        assert tnd is not None
        observed=np.resize(tnd.T.reshape(-1),n)
        return observed.reshape(n_days,24).T.astype(bool),seed
    if kind=="MCAR": return (rng.random((24,n_days))>=p),seed
    if kind=="DAY":
        keep=np.ones(n_days,dtype=bool)
        keep[rng.choice(n_days,size=round(p*n_days),replace=False)]=False
        return np.broadcast_to(keep,(24,n_days)).copy(),seed
    if kind.startswith("BLOCK"):
        keep=np.ones(n,dtype=bool)
        target=math.ceil(p*n)
        attempts=0
        while (~keep).sum()<target and attempts<20*n:
            start=int(rng.integers(0,max(1,n-length+1)))
            keep[start:start+length]=False
            attempts+=1
        if (~keep).sum()<target: raise RuntimeError(f"Block mask target not reached: {kind} {p}")
        return keep.reshape(n_days,24).T,seed
    raise ValueError(kind)


def stage_rows(split: str) -> list[dict]:
    all_rows=csv_read(OUT/"F3_data_inventory.csv")
    result=[]
    for r in all_rows:
        if r["eligible_E1"]!="True" or r["station"] not in ("COI","KDU","GUA"):continue
        y=int(r["year"])
        if split=="development" and ((r["station"]=="COI" and 2007<=y<=2011) or (r["station"]=="KDU" and 2014<=y<=2015)):
            result.append(r)
        if split=="holdout" and ((r["station"]=="COI" and 2012<=y<=2017) or (r["station"]=="KDU" and 2016<=y<=2018) or r["station"]=="GUA"):
            result.append(r)
    return result


def prepare_truth(row: dict, c: int) -> tuple[np.ndarray,np.ndarray,dict,np.ndarray,dict]:
    matrix=np.load(ROOT/row["matrix_cache"],allow_pickle=False)["XYZ_nT"][:,:,c]
    complete,keep,_=gaps.apply(matrix,"M-INT")
    if not keep.all() or not np.isfinite(complete).all():
        raise RuntimeError("E1 QC complete month cannot be filled without dropping days")
    ref=selection.sq_iqd(complete,gfz_days(int(row["year"]),int(row["month"])))
    result=pca.decompose_v1(complete)
    from classification_core import random_phase_surrogates
    surrogates=random_phase_surrogates(ref)
    truth=selection.choose(result,ref,surrogates)
    if truth["selected"] is None:
        raise RuntimeError("Complete-data S8 has NO_PASS candidate; E1 relative target undefined")
    if not np.isfinite(truth["curve"]).all() or np.linalg.norm(truth["curve"])==0:
        raise RuntimeError("Complete-data target curve zero/nonfinite")
    return complete,ref,truth,surrogates,result


def process_month(row: dict,split: str) -> tuple[list[dict],list[dict]]:
    station,year,month=row["station"],int(row["year"]),int(row["month"])
    if sha(ROOT/row["matrix_cache"])!=row["matrix_cache_sha256"]:
        raise RuntimeError(f"Monthly derived input hash mismatch: {row['matrix_cache']}")
    truths=[];notes=[]
    for ci,c in enumerate("XYZ"):
        try:
            complete,ref,truth,surrogates,truth_pca=prepare_truth(row,ci)
            truths.append((c,complete,ref,truth,surrogates,truth_pca))
            notes.append({"split":split,"station":station,"year":year,"month":month,"component":c,
                          "status":"OK","truth_candidate":truth["selected"],"error":""})
        except Exception as e:
            notes.append({"split":split,"station":station,"year":year,"month":month,"component":c,
                          "status":"UNRESOLVED_TRUTH","truth_candidate":"","error":f"{type(e).__name__}: {e}"})
    if not truths:return [],notes
    tnd_file=np.load(WORK/"TND_2017_hourly_masks.npz",allow_pickle=False)
    tnd=tnd_file[f"m{month:02d}"]
    output=[]
    for family,kind,p,length,reps in SETTINGS:
        for rep in range(reps):
            observed,mask_seed=make_mask(kind,p,length,truths[0][1].shape[1],rep,station,year,month,tnd)
            actual=1-float(observed.mean())
            for c,complete,ref,truth,surrogates,truth_pca in truths:
                masked=complete.copy();masked[~observed]=np.nan
                for method in METHODS:
                    base={"split":split,"station":station,"year":year,"month":month,"component":c,
                          "mask_family":family,"mask_kind":kind,"p_nominal":p if p is not None else "TND",
                          "p_actual":actual,"block_length":length if length is not None else "",
                          "replicate":rep,"mask_seed":mask_seed,"method":method,"status":"OK",
                          "error_original":"","error_relative_l2":float("inf"),"fixed_candidate_error":float("inf"),
                          "pc1_angle_deg":float("nan"),"candidate_agree":False,
                          "selected_candidate":"","truth_candidate":truth["selected"],
                          "days_kept":0,"observed_fraction":1-actual,
                          "em_iterations":0,"em_final_change_nT":0.0}
                    try:
                        filled,keep,meta=gaps.apply(masked,method)
                        base["days_kept"]=int(keep.sum())
                        base["em_iterations"]=meta["iterations"]
                        base["em_final_change_nT"]=meta["final_change_nT"]
                        if filled.shape[1]<3 or not np.isfinite(filled).all():
                            base["status"]="NO_MATRIX"
                        else:
                            result=pca.decompose_v1(filled)
                            chosen=selection.choose(result,ref,surrogates)
                            base["pc1_angle_deg"]=metrics.vector_angle_deg(result["pc"][:,0],truth_pca["pc"][:,0])
                            fixed=candidates.curves(result)[truth["selected"]]
                            base["fixed_candidate_error"]=metrics.relative_l2(fixed,truth["curve"])
                            base["selected_candidate"]=chosen["selected"] or ""
                            base["candidate_agree"]=chosen["selected"]==truth["selected"]
                            if chosen["curve"] is not None:
                                base["error_relative_l2"]=metrics.relative_l2(chosen["curve"],truth["curve"])
                            else:base["status"]="NO_PASS"
                    except Exception as e:
                        base["status"]="ERROR"
                        base["error_original"]=f"{type(e).__name__}: {e}"
                    output.append(base)
    return output,notes


def run_split(split: str,workers: int=4) -> None:
    verify_snapshot()
    if split=="holdout":
        config=OUT/"F3_E1_frozen.json"
        if not config.is_file() or sha(config)!=(OUT/"F3_E1_frozen.json.sha256").read_text().split()[0]:
            raise RuntimeError("E1 frozen config missing/hash mismatch")
        freeze=json.loads(config.read_text(encoding="utf-8"))
        for name,digest in freeze["code_sha256"].items():
            if sha(OUT/name)!=digest:raise RuntimeError(f"E1 code changed after freeze: {name}")
        if sha(OUT/"F3_data_inventory.csv")!=freeze["data_inventory_sha256"] or sha(WORK/"TND_2017_hourly_masks.npz")!=freeze["TND_mask_cache_sha256"]:
            raise RuntimeError("E1 data inventory or TND masks changed after freeze")
    path=WORK/f"E1_{split}_cases.csv"
    if path.exists():raise RuntimeError(f"E1 {split} already exists; refusing to rerun: {path}")
    todo=stage_rows(split)
    log(f"E1 {split}: {len(todo)} QC eligible station-months, {workers} workers; holdout values {'after' if split=='holdout' else 'before'} freeze")
    notes=[]
    with path.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=CASE_FIELDS,extrasaction="ignore");writer.writeheader()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures={pool.submit(process_month,row,split):row for row in todo}
            for idx,future in enumerate(as_completed(futures),1):
                row=futures[future]
                try: cases,info=future.result()
                except Exception as e:
                    raise RuntimeError(f"E1 worker failure {row['station']} {row['year']}-{row['month']}: {type(e).__name__}: {e}") from e
                writer.writerows(cases);f.flush();notes.extend(info)
                if idx%5==0 or idx==len(todo):log(f"E1 {split}: completed {idx}/{len(todo)} station-months; rows written {path.stat().st_size} bytes")
    csv_write(WORK/f"E1_{split}_truth_status.csv",notes,["split","station","year","month","component","status","truth_candidate","error"])
    log(f"E1 {split} complete: {len(csv_read(path))} cases, {sum(x['status']=='OK' for x in notes)} complete-data truths")
    verify_snapshot()


def develop() -> None:
    run_split("development",int(os.environ.get("F3_WORKERS","4")))
    data=csv_read(WORK/"E1_development_cases.csv")
    grouped=defaultdict(list)
    for r in data:
        p=float(r["p_actual"]) if r["mask_family"]=="TND" else float(r["p_nominal"])
        if p<=.3000001:
            grouped[(r["method"],r["mask_family"],r["component"])].append(float(r["error_relative_l2"]))
    summaries=[]
    for (method,family,c),values in sorted(grouped.items()):
        summaries.append({"method":method,"mask_family":family,"component":c,
                          "cases":len(values),"median_error":float(np.median(values))})
    csv_write(OUT/"F3_E1_dev_method_summary.csv",summaries,["method","mask_family","component","cases","median_error"])
    scores={m:float(np.mean([v["median_error"] for v in summaries if v["method"]==m])) for m in METHODS}
    chosen=min(METHODS,key=lambda m:(scores[m],METHODS.index(m)))
    code_paths=sorted(p for p in (OUT/"auto_sqpca").glob("*.py")) + [OUT/"f3_e1.py",OUT/"f3_inventory.py"]
    freeze={"method":chosen,"selection_score_mean_of_family_component_medians":scores,
            "tie_order":list(METHODS),"seed":SEED,"mask_replicates":20,
            "development_cases_sha256":sha(WORK/"E1_development_cases.csv"),
            "data_inventory_sha256":sha(OUT/"F3_data_inventory.csv"),
            "TND_mask_cache_sha256":sha(WORK/"TND_2017_hourly_masks.npz"),
            "protocol_sha256":sha(OUT/"F3_protocol_v1.md"),
            "code_sha256":{p.relative_to(OUT).as_posix():sha(p) for p in code_paths},
            "method_definition_note":"M-EM uses documented 1e-8 nT precision guard instead of F3-v1 1e-4; 500-iteration cap retained; requires reviewer scrutiny",
            "selection_formula":"mean across mask families x components of median relative-L2 errors for nominal p<=0.30; TND included only when actual missing fraction<=0.30; all non-output cases inf"}
    jwrite(OUT/"F3_E1_frozen.json",freeze)
    (OUT/"F3_E1_frozen.json.sha256").write_text(f"{sha(OUT/'F3_E1_frozen.json')}  F3_E1_frozen.json\n",encoding="ascii")
    log(f"E1 development selected {chosen}; scores={scores}; frozen SHA-256={sha(OUT/'F3_E1_frozen.json')}")


if __name__=="__main__":
    cmd=sys.argv[1] if len(sys.argv)>1 else ""
    if cmd=="development":develop()
    elif cmd=="holdout":run_split("holdout",int(os.environ.get("F3_WORKERS","4")))
    else:raise SystemExit("Usage: python f3_e1.py development|holdout")
