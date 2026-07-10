#!/usr/bin/env python3
"""
revise_and_flow_study.py — (A) 시가모델 개량 검증  (B) 수급 예측가능성 실측
2026-07-10 | Claude   정보·연구 목적. 투자자문 아님.
"""
import csv, json, os, sys, datetime, bisect
import numpy as np

HERE = "/home/waterfirst/kospi-mw-rc-research"
def load_price(p):
    out={}
    for r in csv.reader(open(p)):
        if r and r[0].strip().strip('"').isdigit():
            out[r[0].strip().strip('"')]=tuple(float(x) for x in r[1:5])
    return out
def load_flow(p):
    out={}; rr=csv.reader(open(p)); next(rr,None)
    for r in rr:
        if len(r)>=4 and r[0].isdigit(): out[r[0]]=(int(r[1]),int(r[2]),int(r[3]))
    return out
def ypct(p):
    r=json.load(open(p))["chart"]["result"][0]
    s=[(datetime.datetime.utcfromtimestamp(t).strftime("%Y%m%d"),c)
       for t,c in zip(r["timestamp"],r["indicators"]["quote"][0]["close"]) if c]
    return {s[i][0]:(s[i][1]/s[i-1][1]-1)*100 for i in range(1,len(s))}

price=load_price(f"{HERE}/data/kospi_price.csv"); flow=load_flow(f"{HERE}/data/kospi_flow.csv")
ewy=ypct("/tmp/ewy.json"); sox=ypct("/tmp/sox.json"); ed=sorted(ewy); sd=sorted(sox)
def ov(kd,pct,ds):
    i=bisect.bisect_left(ds,kd); return pct.get(ds[i-1]) if i else None
kd=sorted(price)

# 정렬 시계열
rows=[]
for i in range(1,len(kd)):
    d=kd[i]; pc=price[kd[i-1]][3]; e=ov(d,ewy,ed)
    if e is None: continue
    o,h,l,c=price[d]
    rows.append({"d":d,"pc":pc,"ewy":e,"sox":ov(d,sox,sd) or 0.0,
                 "open":o,"close":c,"gap":(o/pc-1)*100})
EWY=np.array([r["ewy"] for r in rows]); GAP=np.array([r["gap"] for r in rows])
PC=np.array([r["pc"] for r in rows]); OP=np.array([r["open"] for r in rows])

def mae(pred): return float(np.mean(np.abs(pred-OP)/OP*100))
base_pred=PC                                   # 갭0
v7_pred=np.round(PC*(1+np.clip(0.58*EWY,-6,6)/100))
print("="*70); print("(A) 시가모델 개량 검증"); print("="*70)
print(f"  표본 {len(rows)}일 | baseline(갭0) MAE {mae(base_pred):.3f}% | v7(0.58·EWY) MAE {mae(v7_pred):.3f}%")

# A1. 최적 K 전수(인샘플 하한 참고)
best=(1e9,None)
for K in np.arange(0.0,0.81,0.02):
    p=PC*(1+K*EWY/100); m=mae(p)
    if m<best[0]: best=(m,round(float(K),2))
print(f"  인샘플 최적 K = {best[1]}  → MAE {best[0]:.3f}%  (v7 K=0.58과 비교)")

# A2. winsor(극단축소)+shrink 개량형, walk-forward 최적화(정직한 OOS)
def revised(K,cap,shr,ewy_v,pc):
    g=K*np.clip(ewy_v,-cap,cap); g=g*(1-shr)   # baseline으로 shrink
    return pc*(1+g/100)
grid=[(K,cap,shr) for K in np.arange(0.1,0.7,0.05)
                   for cap in (2.0,2.5,3.0,4.0,10.0)
                   for shr in (0.0,0.15,0.3)]
MINW=120; wf_pred=np.full(len(rows),np.nan)
for i in range(MINW,len(rows)):
    # 과거 구간에서 최적 파라미터
    bpar=(1e9,None)
    for K,cap,shr in grid:
        p=revised(K,cap,shr,EWY[:i],PC[:i]); m=float(np.mean(np.abs(p-OP[:i])/OP[:i]*100))
        if m<bpar[0]: bpar=(m,(K,cap,shr))
    K,cap,shr=bpar[1]; wf_pred[i]=revised(K,cap,shr,np.array([EWY[i]]),np.array([PC[i]]))[0]
msk=~np.isnan(wf_pred)
wf_mae=float(np.mean(np.abs(wf_pred[msk]-OP[msk])/OP[msk]*100))
base_sub=float(np.mean(np.abs(PC[msk]-OP[msk])/OP[msk]*100))
v7_sub=float(np.mean(np.abs(v7_pred[msk]-OP[msk])/OP[msk]*100))
print(f"  [walk-forward, {int(msk.sum())}일 OOS] 개량형 MAE {wf_mae:.3f}%  "
      f"vs v7 {v7_sub:.3f}%  vs baseline {base_sub:.3f}%")
# 극단일만
ext=msk & (np.abs(EWY)>3.0)
if ext.sum():
    print(f"  극단 오버나잇(|EWY|>3%, {int(ext.sum())}일)만: 개량 "
          f"{float(np.mean(np.abs(wf_pred[ext]-OP[ext])/OP[ext]*100)):.2f}% vs "
          f"v7 {float(np.mean(np.abs(v7_pred[ext]-OP[ext])/OP[ext]*100)):.2f}%")

# ══════════════════════════════════════════════════════════════
print("\n"+"="*70); print("(B) 외인/기관 수급 예측가능성 실측"); print("="*70)
fk=sorted(set(price)&set(flow))
F=np.array([flow[d][1] for d in fk],float); I=np.array([flow[d][2] for d in fk],float)
cl=np.array([price[d][3] for d in fk]); ret=np.zeros(len(cl)); ret[1:]=(cl[1:]/cl[:-1]-1)*100
def ac1(x): return float(np.corrcoef(x[:-1],x[1:])[0,1])
def signpers(x):
    s=np.sign(x); ok=(s[1:]==s[:-1]); return float(ok.mean()*100)
print(f"  표본 {len(fk)}일 (수급∩가격)")
print(f"  외인 net 자기상관 AR(1) r={ac1(F):+.3f} | 부호지속률 {signpers(F):.1f}%")
print(f"  기관 net 자기상관 AR(1) r={ac1(I):+.3f} | 부호지속률 {signpers(I):.1f}%")
# 오버나잇→당일 외인 (같은 날 EWY 오버나잇이 그날 외인방향 예측?)
fk2=[d for d in fk if ov(d,ewy,ed) is not None]
Fe=np.array([flow[d][1] for d in fk2]); Ee=np.array([ov(d,ewy,ed) for d in fk2])
print(f"  EWY오버나잇 vs 당일 외인net 상관 r={np.corrcoef(Ee,Fe)[0,1]:+.3f} "
      f"(오버나잇으로 아침 외인방향 부분예측)")
# 전일수익률→당일 외인
print(f"  전일 KOSPI수익 vs 당일 외인net 상관 r={np.corrcoef(ret[:-1],F[1:])[0,1]:+.3f}")
# 당일 외인 → 당일 수익(동시점, 드라이버 확인)
print(f"  당일 외인net vs 당일 수익 상관 r={np.corrcoef(F,ret)[0,1]:+.3f} (동시점=진짜 드라이버)")
# 익일 외인 부호로 익일 수익 예측되나 (외인지속 가정)
nxt=ret[1:]; sig=np.sign(F[:-1])
up=nxt[sig>0]; dn=nxt[sig<0]
print(f"  외인[t]>0 → 익일수익 평균 {up.mean():+.3f}% (n={len(up)}) | "
      f"외인[t]<0 → {dn.mean():+.3f}% (n={len(dn)})  차 {up.mean()-dn.mean():+.3f}%p")
# 다중회귀: F[t] ~ EWY_on[t]+ret[t-1]+F[t-1]
n=len(fk2)
# 정렬 재구성
idx={d:j for j,d in enumerate(fk)}
X=[];Y=[]
for d in fk2:
    j=idx[d]
    if j==0: continue
    X.append([ov(d,ewy,ed), ret[j-1], F[j-1]]); Y.append(F[j])
X=np.array(X);Y=np.array(Y); Xa=np.column_stack([np.ones(len(X)),X])
beta,_,_,_=np.linalg.lstsq(Xa,Y,rcond=None); pred=Xa@beta
r2=1-np.sum((Y-pred)**2)/np.sum((Y-Y.mean())**2)
print(f"  외인[t] ~ EWY_on + 전일수익 + 외인[t-1] 다중회귀 R²={r2:.3f} "
      f"(설명력; 1에 가까울수록 예측가능)")
print("="*70)
