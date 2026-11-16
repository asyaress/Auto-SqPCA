import sys, json, numpy as np
sys.path.insert(0,'phase3'); 
from auto_sqpca import gaps, selection, candidates, bootstrap
from auto_sqpca.pca import decompose_v1
rng=np.random.default_rng(1); out={}
h=np.arange(24)+.5
sq=np.exp(-((h-11.5)/3.2)**2); sq-=sq.mean(); m2=np.sin(2*np.pi*(h-3)/24); m3=np.sin(4*np.pi*(h-1)/24)
def ar_days(n,rho=.9,sd=3):
    e=rng.normal(size=(24,n)); x=np.zeros((24,n)); x[0]=e[0]
    for i in range(1,24): x[i]=rho*x[i-1]+np.sqrt(1-rho**2)*e[i]
    return sd*x
def month(n=30,amp=20,noise=3):
    a=rng.lognormal(0,.3,n); b=rng.normal(0,4,n); c=rng.normal(0,2,n)
    return 20000+rng.normal(0,15,n)[None,:]+amp*sq[:,None]*a+m2[:,None]*b+m3[:,None]*c+ar_days(n,sd=noise)
# A: night baseline is a no-op in the reference
A=month(); qd=[3,9,14,20,27]
ref=selection.sq_iqd(A,qd); alt=A[:,np.array(qd)-1].mean(axis=1); alt-=alt.mean()
out['A_baseline_noop_max_abs_diff_nT']=float(np.max(np.abs(ref-alt)))
# B: imputation keeps observed values; adds daily mean back; exact on rank-3
L=20000+rng.normal(0,15,30)[None,:]+ (np.c_[sq,m2,m3]@rng.normal(0,10,(3,30)))
mask=rng.random(L.shape)<.3; M=L.copy(); M[mask]=np.nan
F,keep,it,ch=gaps.fill_em(M)
out['B_observed_unchanged']=bool(np.array_equal(F[~mask],L[~mask])); out['B_rank3_max_err_nT']=float(np.max(np.abs(F-L))); out['B_iter']=it
out['B_filled_level_ok']=bool(abs(F[mask].mean()-L[mask].mean())<1)
# C: convergence sensitivity (test copy of fill_em with configurable cap; same arithmetic)
def fill_em_cap(a,cap,tol=1e-8):
    keep=np.isfinite(a).sum(axis=0)>=6; o=a[:,keep].copy(); miss=~np.isfinite(o)
    o[miss]=np.broadcast_to(np.nanmean(o,axis=0),o.shape)[miss]
    for i in range(1,cap+1):
        dm=o.mean(axis=0,keepdims=True); u,s,vh=np.linalg.svd(o-dm,full_matrices=False)
        r=(u[:,:3]*s[:3])@vh[:3]+dm; c=float(np.max(np.abs(r[miss]-o[miss]))); o[miss]=r[miss]
        if c<tol: break
    return o,i,c
def pipe(F,qd):
    ref=selection.sq_iqd(F,qd); return selection.choose(decompose_v1(F),ref)
res=[]
for kind,p in [('mcar',.05),('mcar',.10),('block12',.10)]:
    for t in range(60):
        A=month(); n=A.shape[1]; obs=np.ones(A.shape,bool)
        if kind=='mcar': obs=rng.random(A.shape)>=p
        else:
            flat=obs.T.reshape(-1).copy(); 
            while (~flat).mean()<p:
                s0=rng.integers(0,len(flat)-12); flat[s0:s0+12]=False
            obs=flat.reshape(n,24).T
        M=A.copy(); M[~obs]=np.nan
        if (np.isfinite(M).sum(axis=0)<6).any(): continue
        qd=sorted(rng.choice(np.arange(1,n+1),5,replace=False).tolist())
        r={}
        for cap in (50,500,5000):
            F,i,c=fill_em_cap(M,cap); ch=pipe(F,qd); r[cap]=(i,c,ch['selected'],ch['curve'])
        ref5=r[5000]
        def rel(x): 
            return float(np.linalg.norm(x-ref5[3])/np.linalg.norm(ref5[3])) if (x is not None and ref5[3] is not None and x.shape==ref5[3].shape) else None
        res.append(dict(kind=kind,p=p,capped500=r[500][0]>=500,chg500=r[500][1],chg5000=r[5000][1],it5000=r[5000][0],
                        same_cand_500=r[500][2]==ref5[2],same_cand_50=r[50][2]==ref5[2],rel500=rel(r[500][3]) if r[500][2]==ref5[2] else None,rel50=rel(r[50][3]) if r[50][2]==ref5[2] else None))
import pandas as pd; d=pd.DataFrame(res)
out['C']=json.loads(d.groupby(['kind','p']).agg(n=('kind','size'),capped500=('capped500','mean'),med_final_change_500=('chg500','median'),conv_by_5000=('it5000',lambda x:(x<5000).mean()),same_cand_500=('same_cand_500','mean'),same_cand_50=('same_cand_50','mean'),max_rel_curve_diff_500=('rel500','max'),med_rel_curve_diff_500=('rel500','median'),max_rel_curve_diff_50=('rel50','max')).reset_index().to_json(orient='records'))
# D: null with no common daily pattern, reference taken from 5 of the same days
passed=0; cand=[]; N=400
for t in range(N):
    A=20000+ar_days(30,sd=5); qd=sorted(rng.choice(np.arange(1,31),5,replace=False).tolist())
    ch=pipe(A,qd); passed+=ch['selected'] is not None; cand.append(ch['selected'])
out['D_null_selfref_A1_pass_rate']=passed/N
# same null but reference from 5 independent days not in the matrix
p2=0
for t in range(N):
    A=20000+ar_days(30,sd=5); B=20000+ar_days(5,sd=5); ref=B.mean(axis=1); ref-=ref.mean()
    p2+=selection.choose(decompose_v1(A),ref)['selected'] is not None
out['D_null_independent_ref_pass_rate']=p2/N
# with bootstrap stability >=0.5 (subset)
acc=0; K=60
for t in range(K):
    A=20000+ar_days(30,sd=5); qd=sorted(rng.choice(np.arange(1,31),5,replace=False).tolist())
    ref=selection.sq_iqd(A,qd); ch=selection.choose(decompose_v1(A),ref)
    if ch['selected'] is None: continue
    b=bootstrap.summarize(A,ref,ch['selected'],n_boot=200,seed=t); acc+= b['stability']>=.5
out['D_null_selfref_accept_after_A2_rate']=acc/K
# E: polarity: can a candidate with negative r pass?
neg=0;tot=0
for t in range(300):
    A=month(amp=3,noise=4); qd=sorted(rng.choice(np.arange(1,31),5,replace=False).tolist())
    ch=pipe(A,qd)
    if ch['selected']: tot+=1; neg+= ch['scores'][ch['selected']]['r']<0
out['E_selected_negative_r']=[neg,tot]
print(json.dumps(out,indent=1))
