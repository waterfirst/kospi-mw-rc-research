#!/usr/bin/env python3
"""
backtest_charts_v7.py — 실측 vs 모델 시계열 그래프 + Q1/Q2/Q3 분석
2026-07-10 | Claude

Q1 시가 예측력       : 배포 core.predict_open, 실측 vs 예측 시계열 + 오차
Q2 시가→종가 예측    : 장중 연속성(open_gap→intraday) walk-forward 검증
Q3 나비에-스토크스   : 확산(열)방정식 트렌드 필터로 장기추세 분해(기술적, 예측 아님)
정보·연구 목적. 투자자문 아님.
"""
import csv, json, os, sys, datetime
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

# 한글 폰트
FP = "/usr/share/fonts/truetype/nanum/NanumSquare_acR.ttf"
fm.fontManager.addfont(FP)
plt.rcParams["font.family"] = fm.FontProperties(fname=FP).get_name()
plt.rcParams["axes.unicode_minus"] = False

sys.path.insert(0, "/home/waterfirst/kospi_diode_claude")
from kospi_diode_mcp import core

HERE = "/home/waterfirst/kospi-mw-rc-research"
OUT = os.path.join(HERE, "contest", "backtests")
os.makedirs(OUT, exist_ok=True)

# ── 데이터 ──────────────────────────────────────────────
def load_price(path):
    out = {}
    for row in csv.reader(open(path)):
        if row and row[0].strip().strip('"').isdigit():
            d = row[0].strip().strip('"')
            out[d] = tuple(float(x) for x in row[1:5])  # o,h,l,c
    return out

def yahoo_pct(path):
    r = json.load(open(path))["chart"]["result"][0]
    seq = [(datetime.datetime.utcfromtimestamp(t).strftime("%Y%m%d"), c)
           for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]) if c]
    return {seq[i][0]: (seq[i][1]/seq[i-1][1]-1)*100 for i in range(1, len(seq))}

price = load_price(os.path.join(HERE, "data", "kospi_price.csv"))
ewy, sox = yahoo_pct("/tmp/ewy.json"), yahoo_pct("/tmp/sox.json")
ed, sd = sorted(ewy), sorted(sox)
import bisect
def overnight(kd, pct, ds):
    i = bisect.bisect_left(ds, kd)
    return pct.get(ds[i-1]) if i else None

kd = sorted(price)
def dt(d): return datetime.datetime.strptime(d, "%Y%m%d")

# ── Q1: 시가 실측 vs 예측 ───────────────────────────────
D, actО, predO, prevC = [], [], [], []
for i in range(1, len(kd)):
    d = kd[i]; pc = price[kd[i-1]][3]; ov = overnight(d, ewy, ed)
    if ov is None: continue
    out = core.predict_open(prev_close=pc, ewy_overnight=ov,
                            sox_overnight=overnight(d, sox, sd) or 0.0)
    D.append(dt(d)); actО.append(price[d][0]); predO.append(out["pred_open"]); prevC.append(pc)
actО, predO, prevC = map(np.array, (actО, predO, prevC))
errO = np.abs(predO-actО)/actО*100
baseO = np.abs(prevC-actО)/actО*100  # 갭0 베이스라인

# ── Q2: 시가→종가 (장중 연속성) walk-forward ───────────
# 입력: 오늘 시가갭 g=(open/prevclose-1). 목표: 장중 m=(close/open-1).
# 모델: m_hat = a + b*g (과거만으로 OLS, 익일 예측). 베이스라인: close=open(m=0).
kd2 = kd
o = np.array([price[d][0] for d in kd2]); c = np.array([price[d][3] for d in kd2])
pc2 = np.array([price[kd2[i-1]][3] if i else price[kd2[0]][3] for i in range(len(kd2))])
g = (o/pc2-1)*100          # 시가갭%
m = (c/o-1)*100            # 장중 시가→종가%
Dc = [dt(d) for d in kd2]
predC_wf, actC = [], []; base_mae, mdl_mae = [], []
MINW = 60
for i in range(MINW, len(kd2)):
    X = g[:i]; Y = m[:i]
    b, a = np.polyfit(X, Y, 1)          # 과거만
    mhat = a + b*g[i]
    ch = o[i]*(1+mhat/100)
    predC_wf.append(ch); actC.append(c[i])
    mdl_mae.append(abs(ch-c[i])/c[i]*100)
    base_mae.append(abs(o[i]-c[i])/c[i]*100)   # close=open
DcW = Dc[MINW:]
corr = np.corrcoef(g, m)[0,1]

# ── Q3: 확산(열)방정식 트렌드 필터 ─────────────────────
# 로그가격 u(x,t). ∂u/∂τ = ν ∂²u/∂x² 를 명시적 차분으로 반복 → 확산 평활.
# 남는 것: 저주파 '추세장(field)'. 잔차 = 고주파 변동. 예측 아님(기술적 분해).
logp = np.log(np.array([price[d][3] for d in kd]))
u = logp.copy(); nu = 0.20; steps = 400
for _ in range(steps):
    lap = np.zeros_like(u); lap[1:-1] = u[2:]-2*u[1:-1]+u[:-2]
    lap[0]=lap[1]; lap[-1]=lap[-2]
    u += nu*lap
trend = np.exp(u)                     # 확산추세
raw = np.exp(logp)
vel = np.gradient(u)*100              # 추세 '속도'(모멘텀 장) %/일
Dall = [dt(d) for d in kd]

# ══════════════════════════════════════════════════════
# 그래프 1: Q1 시가 실측 vs 예측
# ══════════════════════════════════════════════════════
fig, ax = plt.subplots(2, 1, figsize=(13, 8), height_ratios=[3, 1.2], sharex=True)
ax[0].plot(D, actО, color="#111", lw=1.3, label="실측 시가")
ax[0].plot(D, predO, color="#e4572e", lw=1.0, alpha=.85, label="모델 예측 시가 (0.58×EWY)")
ax[0].set_title(f"Q1. KOSPI 시가 — 실측 vs 최종모델 예측 (2년, n={len(D)}, MAE {errO.mean():.2f}%)",
                fontsize=13, weight="bold")
ax[0].legend(loc="upper left", frameon=False); ax[0].grid(alpha=.25)
ax[0].set_ylabel("지수")
ax[1].fill_between(D, errO, color="#e4572e", alpha=.5, label=f"모델 오차 (평균 {errO.mean():.2f}%)")
ax[1].axhline(baseO.mean(), color="#3a6ea5", ls="--", lw=1,
              label=f"베이스라인(갭0) 평균오차 {baseO.mean():.2f}%")
ax[1].set_ylabel("오차 %"); ax[1].legend(loc="upper left", frameon=False, fontsize=8)
ax[1].grid(alpha=.25)
fig.tight_layout(); f1 = os.path.join(OUT, "chart_Q1_open.png"); fig.savefig(f1, dpi=130); plt.close(fig)

# ══════════════════════════════════════════════════════
# 그래프 2: Q2 시가→종가
# ══════════════════════════════════════════════════════
fig, ax = plt.subplots(2, 1, figsize=(13, 8), height_ratios=[2.2, 2])
ax[0].plot(DcW, actC, color="#111", lw=1.2, label="실측 종가")
ax[0].plot(DcW, predC_wf, color="#2e8b57", lw=1.0, alpha=.85,
           label=f"시가→종가 모델 (walk-forward, MAE {np.mean(mdl_mae):.2f}%)")
ax[0].set_title(f"Q2. 시가로 종가 예측 — 실측 vs 예측 (베이스라인 close=open MAE {np.mean(base_mae):.2f}%)",
                fontsize=13, weight="bold")
ax[0].legend(loc="upper left", frameon=False); ax[0].grid(alpha=.25); ax[0].set_ylabel("지수")
# 산점도: 시가갭 vs 장중수익
ax[1].scatter(g, m, s=9, alpha=.35, color="#2e8b57")
bb, aa = np.polyfit(g, m, 1)
xs = np.linspace(g.min(), g.max(), 50)
ax[1].plot(xs, aa+bb*xs, color="#e4572e", lw=1.6,
           label=f"회귀 m={bb:+.2f}·gap{aa:+.2f}  (상관 r={corr:+.2f})")
ax[1].axhline(0, color="#888", lw=.6); ax[1].axvline(0, color="#888", lw=.6)
ax[1].set_xlabel("시가갭 % (open/전일종가-1)"); ax[1].set_ylabel("장중 % (close/open-1)")
ax[1].legend(loc="upper right", frameon=False); ax[1].grid(alpha=.2)
fig.tight_layout(); f2 = os.path.join(OUT, "chart_Q2_close_from_open.png"); fig.savefig(f2, dpi=130); plt.close(fig)

# ══════════════════════════════════════════════════════
# 그래프 3: Q3 확산방정식 트렌드
# ══════════════════════════════════════════════════════
fig, ax = plt.subplots(2, 1, figsize=(13, 8), height_ratios=[2.6, 1.4], sharex=True)
ax[0].plot(Dall, raw, color="#bbb", lw=.9, label="실측 종가")
ax[0].plot(Dall, trend, color="#6a4c93", lw=2.0, label=f"확산방정식 추세 (ν={nu}, {steps}스텝)")
ax[0].set_title("Q3. 나비에-스토크스(확산항) 트렌드 필터 — 장기추세 분해 (기술적, 예측 아님)",
                fontsize=13, weight="bold")
ax[0].legend(loc="upper left", frameon=False); ax[0].grid(alpha=.25); ax[0].set_ylabel("지수")
ax[1].fill_between(Dall, vel, 0, where=(vel>=0), color="#2e8b57", alpha=.5, label="추세속도 +")
ax[1].fill_between(Dall, vel, 0, where=(vel<0), color="#c0392b", alpha=.5, label="추세속도 −")
ax[1].axhline(0, color="#333", lw=.6); ax[1].set_ylabel("추세 속도 %/일")
ax[1].legend(loc="upper left", frameon=False, fontsize=8); ax[1].grid(alpha=.25)
fig.tight_layout(); f3 = os.path.join(OUT, "chart_Q3_diffusion_trend.png"); fig.savefig(f3, dpi=130); plt.close(fig)

print(json.dumps({
    "Q1_open_MAE": round(float(errO.mean()),3), "Q1_base_MAE": round(float(baseO.mean()),3),
    "Q2_corr_gap_intraday": round(float(corr),3),
    "Q2_model_MAE": round(float(np.mean(mdl_mae)),3), "Q2_base_MAE": round(float(np.mean(base_mae)),3),
    "Q2_intraday_std": round(float(m.std()),3),
    "files": [f1, f2, f3],
}, ensure_ascii=False, indent=2))
