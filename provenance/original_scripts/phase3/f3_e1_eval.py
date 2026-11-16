"""Evaluate frozen F3A E1 holdout errors, safe bounds, CI, C1, and figures."""
from __future__ import annotations
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
import numpy as np

from f3_preflight import OUT, sha, verify_snapshot

WORK=OUT/"work"
METHODS=("M-INT","M-EXC","M-EM")
EPSILONS=(.03,.05,.10)


def save_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)


def val(x: float):
    return float(x) if np.isfinite(x) else None


def main() -> None:
    verify_snapshot()
    frozen=OUT/"F3_E1_frozen.json"
    if sha(frozen)!=(OUT/"F3_E1_frozen.json.sha256").read_text().split()[0]:
        raise RuntimeError("E1 frozen config hash mismatch")
    config=json.loads(frozen.read_text(encoding="utf-8"))
    selected=config["method"]
    path=WORK/"E1_holdout_cases.csv"
    if not path.is_file():raise RuntimeError("E1 holdout cases missing")
    by_setting=defaultdict(list)
    by_month=defaultdict(lambda:defaultdict(list))
    by_tnd=defaultdict(list)
    status=defaultdict(int)
    em_cap_count=0
    n=0
    with path.open(encoding="utf-8",newline="") as f:
        for r in csv.DictReader(f):
            n+=1
            method=r["method"];kind=r["mask_kind"]
            if method=="M-EM" and int(r["em_iterations"])>=500:em_cap_count+=1
            error=float(r["error_relative_l2"])
            status[r["status"]]+=1
            month_key=f"{r['station']}:{r['year']}-{int(r['month']):02d}"
            if kind=="TND":
                by_tnd[(method,r["station"],int(r["month"]))].append(error)
                continue
            p=float(r["p_nominal"])
            by_setting[(method,kind,p)].append(error)
            if (kind in ("MCAR","BLOCK24","DAY") and p in (.20,.30,.40)):
                by_month[(kind,p,month_key)][method].append(error)
    if n==0:raise RuntimeError("Holdout CSV contains no E1 cases")
    summary=[]
    for (method,kind,p),values in sorted(by_setting.items()):
        arr=np.array(values)
        summary.append({"method":method,"mask_kind":kind,"p":p,"n":len(arr),
                        "median_error":val(float(np.median(arr))),
                        "p90_error":val(float(np.quantile(arr,.9,method="higher"))),
                        "nonfinite_errors":int((~np.isfinite(arr)).sum())})
    save_csv(OUT/"F3_E1_holdout_summary.csv",summary,["method","mask_kind","p","n","median_error","p90_error","nonfinite_errors"])
    pstar=[]
    for method in METHODS:
        for kind in ("MCAR","BLOCK6","BLOCK24","BLOCK72","DAY"):
            for eps in EPSILONS:
                eligible=[r["p"] for r in summary if r["method"]==method and r["mask_kind"]==kind and
                          r["median_error"] is not None and r["p90_error"] is not None and
                          r["median_error"]<=eps and r["p90_error"]<=2*eps]
                pstar.append({"method":method,"mask_kind":kind,"epsilon":eps,
                              "pstar":max(eligible) if eligible else "UNDEFINED"})
    save_csv(OUT/"F3_E1_pstar.csv",pstar,["method","mask_kind","epsilon","pstar"])
    tnd=[]
    for (method,station,month),values in sorted(by_tnd.items()):
        arr=np.array(values)
        tnd.append({"method":method,"station":station,"month":month,"n":len(arr),
                    "median_error":val(float(np.median(arr))),"p90_error":val(float(np.quantile(arr,.9,method="higher"))),
                    "nonfinite_errors":int((~np.isfinite(arr)).sum())})
    save_csv(OUT/"F3_E1_TND_summary.csv",tnd,["method","station","month","n","median_error","p90_error","nonfinite_errors"])
    superiority=[]
    rng=np.random.default_rng(20261114)
    for kind in ("MCAR","BLOCK24","DAY"):
        for p in (.20,.30,.40):
            clusters=[]
            for (k,q,month),methods in by_month.items():
                if k==kind and q==p and methods.get("M-INT") and methods.get(selected):
                    clusters.append((month,float(np.median(methods[selected])),float(np.median(methods["M-INT"]))))
            if not clusters:
                superiority.append({"mask_kind":kind,"p":p,"months":0,"ratio":None,"ci_lower":None,"ci_upper":None,"better_real":False})
                continue
            arr=np.array([(a,b) for _,a,b in clusters])
            base=float(np.median(arr[:,1]))
            ratio=float(np.median(arr[:,0])/base) if base>0 else float("nan")
            draws=[]
            for _ in range(2000):
                sample=arr[rng.integers(0,len(arr),size=len(arr))]
                d=float(np.median(sample[:,1]))
                draws.append(float(np.median(sample[:,0])/d) if d>0 else float("nan"))
            ci=np.nanpercentile(draws,[2.5,97.5]) if np.isfinite(draws).any() else [float("nan")]*2
            superiority.append({"mask_kind":kind,"p":p,"months":len(clusters),"ratio":val(ratio),
                                "ci_lower":val(float(ci[0])),"ci_upper":val(float(ci[1])),
                                "better_real":bool(np.isfinite(ci[1]) and ci[1]<1)})
    save_csv(OUT/"F3_E1_superiority.csv",superiority,["mask_kind","p","months","ratio","ci_lower","ci_upper","better_real"])
    improved_kinds=sorted(kind for kind in ("MCAR","BLOCK24","DAY")
                          if sum(r["better_real"] for r in superiority if r["mask_kind"]==kind)>=2)
    c1={"selected_method":selected,"C1_success":len(improved_kinds)>=2,
        "improved_mask_kinds":improved_kinds,"criterion":"upper 95% cluster-month bootstrap CI of selected/M-INT median error <1 at >=2 of 3 p levels (20,30,40%) within a kind; C1 requires >=2 of MCAR,BLOCK24,DAY kinds",
        "holdout_cases":n,"holdout_status_counts":dict(status),"M_EM_reached_500_iterations":em_cap_count,
        "denominator_note":"missing/no-pass errors are +infinity and included in medians; pstar UNDEFINED if no level satisfies both thresholds",
        "CI_method":"2000 bootstrap resamples of station-year-month clusters; median of monthly method medians, ratio selected/M-INT",
        "pstar_epsilon_0p05_selected":{r["mask_kind"]:r["pstar"] for r in pstar if r["method"]==selected and r["epsilon"]==.05},
        "TND_summary_rows":len(tnd),"holdout_cases_sha256":sha(path)}
    (OUT/"F3_C1_result.json").write_text(json.dumps(c1,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    figures(summary,tnd,selected)
    verify_snapshot()
    print(f"E1 evaluation: {n} holdout method-cases, selected {selected}, C1={c1['C1_success']}, improved kinds={improved_kinds}")


def figures(summary: list[dict],tnd: list[dict],selected: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(12,7),sharey=False)
    kinds=("MCAR","BLOCK6","BLOCK24","BLOCK72","DAY")
    with (OUT/"F3_E1_pstar.csv").open(encoding="utf-8",newline="") as f:
        bounds={(r["method"],r["mask_kind"]):r["pstar"] for r in csv.DictReader(f) if r["epsilon"]=="0.05"}
    for ax,kind in zip(axes.flat,kinds):
        for method in METHODS:
            r=sorted((x for x in summary if x["method"]==method and x["mask_kind"]==kind),key=lambda x:x["p"])
            if r:ax.plot([x["p"]*100 for x in r],[x["median_error"] for x in r],marker="o",label=method)
        ax.axhline(.05,color="black",linestyle="--",linewidth=.8,label="ε=0.05")
        bound=bounds.get((selected,kind))
        if bound and bound!="UNDEFINED":
            ax.axvline(float(bound)*100,color="tab:red",linestyle=":",linewidth=1,label=f"p* {selected}")
        ax.set(title=kind,xlabel="Data hilang (%)",ylabel="Median galat relatif L2")
        ax.grid(alpha=.2)
    axes.flat[5].axis("off")
    axes.flat[5].legend(*axes.flat[0].get_legend_handles_labels(),loc="center")
    fig.tight_layout();fig.savefig(OUT/"F3A_figure1_error_curves.png",dpi=200);plt.close(fig)
    fig,(ax,ax_fail)=plt.subplots(1,2,figsize=(12,5))
    for method in METHODS:
        monthly=[];fail=[]
        for month in range(1,13):
            r=[x for x in tnd if x["method"]==method and x["month"]==month]
            finite=[x["median_error"] for x in r if x["median_error"] is not None]
            monthly.append(float(np.median(finite)) if finite else np.nan)
            fail.append(sum(x["nonfinite_errors"] for x in r)/sum(x["n"] for x in r) if r else np.nan)
        ax.plot(range(1,13),monthly,marker="o",label=method)
        ax_fail.plot(range(1,13),fail,marker="o",label=method)
    ax.set(xlabel="Bulan topeng TND 2017",ylabel="Median galat relatif L2 (keluaran valid)",title="Topeng nyata: galat")
    ax_fail.set(xlabel="Bulan topeng TND 2017",ylabel="Fraksi tanpa keluaran",title="Topeng nyata: kegagalan keluaran",ylim=(0,1.05))
    for panel in (ax,ax_fail):panel.grid(alpha=.2);panel.set_xticks(range(1,13))
    ax.legend();fig.tight_layout();fig.savefig(OUT/"F3A_figure2_TND.png",dpi=200);plt.close(fig)


if __name__=="__main__":main()
