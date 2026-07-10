#!/usr/bin/env python3
"""
MODEL_v7_backtest.py — 최종 모델(v7.1/v7.2) 2년 백테스트
========================================================
2026-07-10 | Claude

대결 최종 배포 모델(kospi_diode_claude/core.py)의 predict_open / score 를
'그대로 import' 하여 과거 2년에 적용한다. (재구현 오차 없음)

데이터 (대결 최초 진행 데이터 + 오버나잇 보강):
  · KOSPI 일봉 OHLC : kospi-mw-rc-research/data/kospi_price.csv  (2024-01~2026-06)
  · KOSPI 수급      : kospi-mw-rc-research/data/kospi_flow.csv
  · EWY / SOX 오버나잇 : Yahoo Finance 일봉 (/tmp/ewy.json, /tmp/sox.json)

한계(정직하게):
  · 시가모델: 완전 재현 가능 (prev_close + EWY 오버나잇만 필요). 플래그는
    '최종 모델 규율'대로 전부 OFF(자동만료) 상태 = 순수 엔진.
  · 종가모델: 12:35 장중 스냅샷(당시 현재가/고가/저가/장중수급)이 입력인데
    일봉엔 없다 → 점예측 완전재현 불가. 대신 '수급 레짐 분류가 실제 종가
    방향을 맞췄는가'를 검증(보조).

정보·연구 목적. 투자자문 아님. 거래비용/세금/슬리피지 미반영.
"""
from __future__ import annotations
import csv, json, os, sys, statistics as st

# ── 배포 모델 그대로 import ────────────────────────────────
ENGINE = "/home/waterfirst/kospi_diode_claude"
sys.path.insert(0, ENGINE)
from kospi_diode_mcp import core   # predict_open, predict_close, score

HERE = "/home/waterfirst/kospi-mw-rc-research"
PRICE = os.path.join(HERE, "data", "kospi_price.csv")
FLOW  = os.path.join(HERE, "data", "kospi_flow.csv")
EWY_J = "/tmp/ewy.json"
SOX_J = "/tmp/sox.json"


# ── 데이터 로드 ────────────────────────────────────────────
def load_price(path):
    """date(YYYYMMDD) -> (open, high, low, close)"""
    out = {}
    with open(path) as f:
        for row in csv.reader(f):
            if not row or not row[0].strip().strip('"').isdigit():
                continue
            d = row[0].strip().strip('"')
            out[d] = (float(row[1]), float(row[2]), float(row[3]), float(row[4]))
    return out


def load_flow(path):
    out = {}
    with open(path) as f:
        r = csv.reader(f); next(r, None)
        for row in r:
            if len(row) < 4 or not row[0].isdigit():
                continue
            out[row[0]] = (int(row[1]), int(row[2]), int(row[3]))  # P,F,I
    return out


def load_yahoo_pct(path):
    """Yahoo chart json -> {YYYYMMDD: 일간등락률%}  (전일종가 대비)"""
    import datetime
    d = json.load(open(path))
    r = d["chart"]["result"][0]
    ts = r["timestamp"]
    closes = r["indicators"]["quote"][0]["close"]
    seq = []
    for t, c in zip(ts, closes):
        if c is None:
            continue
        ymd = datetime.datetime.utcfromtimestamp(t).strftime("%Y%m%d")
        seq.append((ymd, c))
    pct = {}
    for i in range(1, len(seq)):
        (d0, c0), (d1, c1) = seq[i-1], seq[i]
        pct[d1] = (c1 / c0 - 1) * 100
    return pct  # US date -> 그 세션 등락률


def overnight_for(kdate, us_pct, us_dates_sorted):
    """한국 거래일 kdate 개장 직전 '가장 최근 미국 세션' 등락률."""
    import bisect
    i = bisect.bisect_left(us_dates_sorted, kdate)  # kdate 미만 최대
    if i == 0:
        return None
    return us_pct.get(us_dates_sorted[i-1])


# ── 메인 ───────────────────────────────────────────────────
price = load_price(PRICE)
flow  = load_flow(FLOW)
ewy   = load_yahoo_pct(EWY_J)
sox   = load_yahoo_pct(SOX_J)
ewy_dates = sorted(ewy)
sox_dates = sorted(sox)

kdates = sorted(price)
print("=" * 72)
print("최종 모델(v7.1/v7.2) 2년 백테스트 — 배포 core.predict_open 직접 호출")
print("=" * 72)
print(f"  KOSPI 일봉: {kdates[0]} ~ {kdates[-1]}  ({len(kdates)}일)")
print(f"  EWY 세션: {ewy_dates[0]}~{ewy_dates[-1]} ({len(ewy)}) | "
      f"SOX 세션: {sox_dates[0]}~{sox_dates[-1]} ({len(sox)})")

# ══════════════════════════════════════════════════════════
# A. 시가 모델 (완전 재현) — 플래그 전부 OFF = 순수 엔진
# ══════════════════════════════════════════════════════════
rows = []   # (date, prev_close, ewy, sox, actual_open, pred, err%, tier, dir_ok)
for i in range(1, len(kdates)):
    d, pd_ = kdates[i], kdates[i-1]
    prev_close = price[pd_][3]
    actual_open = price[d][0]
    ov_ewy = overnight_for(d, ewy, ewy_dates)
    ov_sox = overnight_for(d, sox, sox_dates)
    if ov_ewy is None:
        continue
    out = core.predict_open(
        prev_close=prev_close,
        ewy_overnight=ov_ewy,
        sox_overnight=ov_sox or 0.0,
        us_holiday=False, hyper_bull=False, hyper_bear=False, sox_colead=False,
    )
    pred = out["pred_open"]
    sc = core.score(pred, actual_open)
    real_gap = (actual_open / prev_close - 1) * 100
    pred_gap = (pred / prev_close - 1) * 100
    dir_ok = (real_gap == 0) or (pred_gap * real_gap > 0) or (abs(real_gap) < 0.05)
    rows.append((d, prev_close, ov_ewy, ov_sox, actual_open, pred,
                 sc["error_pct"], sc["score"], dir_ok, real_gap, pred_gap))

errs   = [r[6] for r in rows]
tiers  = [r[7] for r in rows]
dirs   = [r[8] for r in rows]

# 베이스라인: '갭0(전일종가=시가)' 순진예측
base_errs = [abs(price[kdates[i]][0]/price[kdates[i-1]][3]-1)*100
             for i in range(1, len(kdates))]

def pctile(a, p):
    a = sorted(a); k = (len(a)-1)*p/100
    f = int(k); return a[f] if f+1>=len(a) else a[f]+(a[f+1]-a[f])*(k-f)

print("\n【A. 시가 모델 — 2년 완전 재현 (플래그 OFF)】")
print("─" * 72)
print(f"  표본: {len(rows)}일")
print(f"  평균 오차율(MAE): {st.mean(errs):.3f}%   중앙값: {st.median(errs):.3f}%")
print(f"  P90 오차: {pctile(errs,90):.3f}%   P95: {pctile(errs,95):.3f}%   최대: {max(errs):.3f}%")
print(f"  방향(갭 부호) 적중률: {sum(dirs)/len(dirs)*100:.1f}%")
hit05 = sum(1 for e in errs if e<=0.5)/len(errs)*100
hit10 = sum(1 for e in errs if e<=1.0)/len(errs)*100
print(f"  오차 ≤0.5% 비율: {hit05:.1f}%   ≤1.0% 비율: {hit10:.1f}%")
print(f"\n  [대조] 순진 베이스라인(시가=전일종가, 갭0) MAE: {st.mean(base_errs):.3f}%  "
      f"중앙 {st.median(base_errs):.3f}%")
print(f"  → 평균 MAE 기준 모델 {st.mean(base_errs)-st.mean(errs):+.3f}%p "
      f"({'개선' if st.mean(errs)<st.mean(base_errs) else '악화'})")
# 공정 비교: 날짜별 페어 승패 (같은 날 모델오차 vs 베이스라인오차)
wins = losses = 0
for i, r in enumerate(rows):
    b = abs(r[4]/r[1]-1)*100   # 그 날 베이스라인 오차
    if r[6] < b - 1e-9: wins += 1
    elif r[6] > b + 1e-9: losses += 1
print(f"  → 날짜별 페어 승패: 모델 승 {wins}일 / 패 {losses}일 "
      f"(승률 {wins/(wins+losses)*100:.1f}%)")
# 극단 오버나잇(|EWY|>3%) 제외 시
calm = [r for r in rows if abs(r[2])<=3.0]
calm_b = [abs(r[4]/r[1]-1)*100 for r in calm]
print(f"  → 잔잔한 날(|EWY|≤3%, {len(calm)}일)만: 모델 MAE {st.mean([r[6] for r in calm]):.3f}% "
      f"vs 베이스 {st.mean(calm_b):.3f}%")

# 채점 티어 분포 (대결 규칙)
print("\n  대결 채점 티어 분포(≤0.25→5 … >1.5→0):")
from collections import Counter
tc = Counter(tiers)
for t in (5,4,3,2,1,0):
    n = tc.get(t,0)
    print(f"    tier {t}: {n:>4}일 ({n/len(tiers)*100:4.1f}%)  " + "█"*int(n/len(tiers)*40))
avg_pts = st.mean(tiers)
print(f"  평균 획득점수: {avg_pts:.3f} / 5")

# 연도별
print("\n  연도별 시가 MAE:")
for yr in ("2024","2025","2026"):
    sub = [r[6] for r in rows if r[0].startswith(yr)]
    if sub:
        print(f"    {yr}: {len(sub):>3}일  MAE {st.mean(sub):.3f}%  중앙 {st.median(sub):.3f}%")

# 최악 5일 / 최고 5일
print("\n  최악 시가 예측 5일:")
for r in sorted(rows, key=lambda x:-x[6])[:5]:
    print(f"    {r[0]}  실제갭 {r[9]:+.2f}% / 예측갭 {r[10]:+.2f}% "
          f"(EWY {r[2]:+.2f} SOX {(r[3] or 0):+.2f}) → 오차 {r[6]:.2f}%")

# ══════════════════════════════════════════════════════════
# B. 종가 모델 — 수급 레짐 분류 검증(보조, 12:35 스냅샷 부재)
# ══════════════════════════════════════════════════════════
print("\n\n【B. 종가 모델 — 레짐 분류 방향 검증 (보조)】")
print("─" * 72)
print("  ※ 종가 점예측은 12:35 장중 스냅샷이 입력이라 일봉으론 완전재현 불가.")
print("     여기선 '일별 외인/기관 순매매 → 레짐 라벨'이 실제 종가 방향(시가대비)을")
print("     맞췄는지만 검증한다. (전일종가 대비 아님, 당일 시가 대비 종가)")
cls = []
for d in kdates:
    if d not in flow:
        continue
    o,hi,lo,c = price[d]
    P,F,I = flow[d]
    # 배포 predict_close 를 '풀데이 값'으로 호출(근사): current=close 는 look-ahead라
    # 방향판정엔 쓰지 않고, 레짐 라벨만 본다. current=open 으로 넣어 레짐만 뽑음.
    out = core.predict_close(open_price=o, current=o, high=hi, low=lo,
                             foreign=F, inst=I)
    regime = out["regime"]
    intraday = (c - o) / o * 100   # 시가→종가 실제 방향
    # 레짐 방향 기대: avalanche_down/gap_fail=하락, avalanche_up/inst_defense=상방, drift=중립
    exp = {"avalanche_down":-1,"gap_fail":-1,"avalanche_up":1,"inst_defense":1,"drift":0}[regime]
    ok = (exp==0) or (exp>0 and intraday>0) or (exp<0 and intraday<0)
    cls.append((d, regime, intraday, exp, ok))

from collections import Counter as C2
rc = C2(r[1] for r in cls)
print(f"  표본: {len(cls)}일   레짐 분포: " +
      ", ".join(f"{k} {v}" for k,v in rc.most_common()))
# 방향성 라벨(중립 제외)만 정확도
dircls = [r for r in cls if r[3]!=0]
if dircls:
    acc = sum(r[4] for r in dircls)/len(dircls)*100
    print(f"  방향성 레짐(중립 drift 제외) {len(dircls)}일 중 종가방향 적중: {acc:.1f}%")
for lab in ("avalanche_down","gap_fail","avalanche_up","inst_defense"):
    sub=[r for r in cls if r[1]==lab]
    if sub:
        a=sum(r[4] for r in sub)/len(sub)*100
        print(f"    {lab:>15}: {len(sub):>3}일  방향적중 {a:.0f}%")

# ══════════════════════════════════════════════════════════
# 결론 저장
# ══════════════════════════════════════════════════════════
summary = {
    "generated": "2026-07-10",
    "engine": "kospi_diode_claude core.predict_open (deployed)",
    "open_sample": len(rows),
    "open_MAE_pct": round(st.mean(errs),3),
    "open_median_pct": round(st.median(errs),3),
    "open_dir_acc_pct": round(sum(dirs)/len(dirs)*100,1),
    "open_hit_le0.5pct": round(hit05,1),
    "open_hit_le1.0pct": round(hit10,1),
    "baseline_MAE_pct": round(st.mean(base_errs),3),
    "open_avg_tier": round(avg_pts,3),
}
outp = os.path.join(HERE, "contest", "backtests", "BACKTEST_v7_2yr_2026-07-10.json")
os.makedirs(os.path.dirname(outp), exist_ok=True)
json.dump(summary, open(outp,"w"), ensure_ascii=False, indent=2)
print("\n" + "=" * 72)
print(f"요약 저장: {outp}")
print(json.dumps(summary, ensure_ascii=False, indent=2))
print("=" * 72)
