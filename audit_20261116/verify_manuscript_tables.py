"""Check main manuscript Table 3–9 values against archived source tables."""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import numpy as np
from docx import Document

REPO = Path(__file__).resolve().parents[1]
DOC = Path("Auto-SqPCA_MethodsX_manuscript_rev4_audit_candidate.docx")
OUT = REPO / "audit_20261116/manuscript_table_validation.json"
if len(sys.argv) >= 2: DOC = Path(sys.argv[1])
doc = Document(DOC)


def read(rel: str) -> list[dict]:
    with (REPO / rel).open(newline="", encoding="utf-8") as f: return list(csv.DictReader(f))


def matching(data: list[dict], **conditions: object) -> dict:
    found = [r for r in data if all(str(r[k]) == str(v) for k, v in conditions.items())]
    assert len(found) == 1, (conditions, len(found))
    return found[0]


def has_number(cell: str, value: float, places: int) -> bool:
    cell = cell.replace("−", "-")
    if places == 0: cell = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "", cell)
    token = f"{value:.{places}f}"
    return bool(re.search(rf"(?<!\d){re.escape(token)}(?!\d)", cell))


labels = {"Random hours":"MCAR", "6-h blocks":"BLOCK6", "24-h blocks":"BLOCK24",
          "72-h blocks":"BLOCK72", "Whole days":"DAY"}
checks=[]


def check(table: int, row: int, field: str, actual: str, expected: float, places: int) -> None:
    checks.append({"table":table,"row":row,"field":field,"printed":actual,"source":expected,
                   "places":places,"pass":has_number(actual,expected,places)})


e1=read("phase3/F3_E1_holdout_summary.csv")
for i,row in enumerate(doc.tables[3].rows[1:],1):
    c=[x.text for x in row.cells]; kind=labels[c[0]]; p=float(c[1].strip("%"))/100
    for j,method in ((2,"M-INT"),(3,"M-EXC"),(4,"M-EM")):
        if "no output" in c[j]: continue
        src=matching(e1,mask_kind=kind,p=p,method=method)
        check(3,i,method,c[j],float(src["median_error"]),3)

sup=read("phase3/F3_E1_superiority.csv")
for i,row in enumerate(doc.tables[4].rows[1:],1):
    c=[x.text for x in row.cells]; kind=labels[c[0]]
    levels=[.2,.3,.4] if "–" in c[1] else [float(c[1].strip("%"))/100]
    for p in levels:
        src=matching(sup,mask_kind=kind,p=p)
        for col,key in ((2,"ratio"),(3,"ci_lower"),(3,"ci_upper")):
            check(4,i,f"{key}_{p}",c[col],float(src[key]),3)

u2=read("phase3/audit_add/U2_operating_range_ratios.csv")
for i,row in enumerate(doc.tables[5].rows[1:],1):
    c=[x.text for x in row.cells]; kind=labels[c[0]]; p=float(c[1].strip("%"))/100
    comp="M-EM/M-INT" if c[2]=="Interpolation" else "M-EM/M-EXC"
    src=matching(u2,mask_kind=kind,p_nominal=p,comparison=comp)
    for col,prefix in ((3,"median"),(4,"p90")):
        for key in (f"{prefix}_error_ratio",f"{prefix}_ratio_ci95_low",f"{prefix}_ratio_ci95_high"):
            check(5,i,key,c[col],float(src[key]),3)

u3=read("phase3/audit_add/U3_summary.csv")
for i,row in enumerate(doc.tables[6].rows[1:],1):
    c=[x.text for x in row.cells]; kind=labels[c[0]]; p=float(c[1].strip("%"))/100
    for method in ("M-EM","M-INT"):
        src=matching(u3,mask_kind=kind,p_nominal=p,method=method)
        check(6,i,method+" accepted",c[2],int(src["n_accepted"]),0)
        if src["accepted_error_median"]:
            check(6,i,method+" median",c[3],float(src["accepted_error_median"]),3)
    check(6,i,"paired count",c[4],int(src["n_paired_both_accepted"]),0)
    if src["paired_M_EM_minus_M_INT_median"]:
        check(6,i,"paired median",c[5],float(src["paired_M_EM_minus_M_INT_median"]),4)

u1=read("phase3/audit_add/U1_summary.csv")
for i,row in enumerate(doc.tables[7].rows[1:],1):
    c=[x.text for x in row.cells]; src=matching(u1,mask_kind=labels[c[0]])
    for col,key in ((1,"fraction_at_cap500"),(2,"fraction_converged_before_cap5000"),
                    (3,"fraction_candidate_same")):
        check(7,i,key,c[col],float(src[key])*100,1)
    for col,keys in ((4,("curve_diff_median","curve_diff_p90")),
                     (5,("cap500_error_median","cap5000_error_median")),
                     (6,("cap500_error_p90","cap5000_error_p90"))):
        for key in keys: check(7,i,key,c[col],float(src[key]),3)

e3=read("phase3/F3_E3_cases.csv")
e3summary=read("phase3/F3_E3_station_summary.csv")
u4=read("phase3/audit_add/U4_rmse_by_station_component.csv")
for i,row in enumerate(doc.tables[9].rows[1:],1):
    c=[x.text for x in row.cells]; station=c[0]
    part=[r for r in e3 if r["station"]==station]
    accepted=[r for r in part if r["abstained"]=="False"]
    assert len(part)==3*int(c[3])
    assert c[4].split("/")[0].strip()==str(len(accepted))
    check(8,i,"abstain",c[5],(1-len(accepted)/len(part))*100,1)
    check(8,i,"median_r",c[6],float(np.median([float(r["r_AUTO_DIFI"]) for r in accepted])),3)

for i,row in enumerate(doc.tables[10].rows[1:],1):
    c=[x.text for x in row.cells]; station,comp=c[:2]
    src=matching(e3summary,station=station,component=comp)
    rm=matching(u4,station=station,component=comp)
    n=int(src["months"]); accepted=int(src["accepted"])
    assert c[2].replace(" ","")==f"{accepted}/{n}"
    check(9,i,"abstain",c[3],float(src["abstain_fraction"])*100,1)
    check(9,i,"median_r",c[4],float(src["median_r_AUTO_DIFI_accepted"]),3)
    check(9,i,"amplitude_ratio",c[5],float(src["median_AUTO_DIFI_amplitude_ratio"]),2)
    check(9,i,"rmse",c[6],float(rm["rmse_nT_median"]),1)
    part=[r for r in e3 if r["station"]==station and r["component"]==comp]
    check(9,i,"model_amplitude",c[7],float(np.median([float(r["DIFI_amplitude_nT"]) for r in part])),1)

result={"level":"ARCHIVED_SUMMARY_TO_MANUSCRIPT", "n_checks":len(checks),
        "failed":[x for x in checks if not x["pass"]], "by_table":{
            str(t):{"checks":sum(x["table"]==t for x in checks),"failed":sum(x["table"]==t and not x["pass"] for x in checks)}
            for t in range(3,10)}}
OUT.write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))
