#!/usr/bin/env python3
"""
다이오드 모델 2년 백테스트 — 실데이터 (네이버 금융)
=====================================================
2026-06-26 | Claude

데이터:
  · 가격: KOSPI 일별 OHLCV (네이버 siseJson, 2024-01-02~2026-06-26)
  · 수급: 일별 외국인·기관·개인 순매매 (네이버 investorDealTrendDay, 2023~2026)

검증 명제:
  H1 (동시점 분류력): D_sell=(F<0 AND I<0) 인 날의 수익률 < OFF 인 날
  H2 (폭락 포착력)  : 큰 하락일(-2%↓) 중 D_sell ON 비율
  H3 (익일 예측력)  : D_sell[t] 가 return[t+1] 을 예측하는가 (관성 L 가설)
  H4 (트레이딩)     : 다이오드 신호 전략 vs Buy&Hold (샤프·MDD·CAGR)

비교 모델:
  · Buy&Hold       : 항상 보유
  · RC(단조회복)    : 하락 다음날 항상 반등 베팅 (단조 가정)
  · 다이오드        : D_sell ON이면 회피/숏, OFF면 보유
"""

import csv, math
import numpy as np

# ══════════════════════════════════════════════════════════════
# 1. 데이터 로드 & 병합
# ══════════════════════════════════════════════════════════════
def load_price(path):
    out = {}
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0] in ('날짜','date') or "'" in row[0]:
                continue
            try:
                d = row[0].strip().strip('"')
                if not d.isdigit(): continue
                out[d] = float(row[4])  # 종가
            except: pass
    return out

def load_flow(path):
    out = {}
    with open(path) as f:
        r = csv.reader(f); next(r, None)
        for row in r:
            if len(row) < 4: continue
            try:
                out[row[0]] = (int(row[1]), int(row[2]), int(row[3]))  # P,F,I
            except: pass
    return out

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
def _find(name):
    for p in (os.path.join(_HERE, 'data', name), os.path.join('/tmp', name)):
        if os.path.exists(p):
            return p
    return os.path.join(_HERE, 'data', name)

price = load_price(_find('kospi_price.csv'))
flow  = load_flow(_find('kospi_flow.csv'))

dates = sorted(set(price) & set(flow))
print("=" * 70)
print("다이오드 모델 2년 백테스트 (실데이터)")
print("=" * 70)
print(f"\n  병합 구간: {dates[0]} ~ {dates[-1]}  ({len(dates)} 거래일)")

# 시계열 구성
close = np.array([price[d] for d in dates])
P     = np.array([flow[d][0] for d in dates], dtype=float)
F     = np.array([flow[d][1] for d in dates], dtype=float)
I     = np.array([flow[d][2] for d in dates], dtype=float)
ret   = np.zeros(len(close))
ret[1:] = (close[1:]/close[:-1] - 1) * 100  # 일별 수익률 %

# 다이오드 상태
D_sell = ((F < 0) & (I < 0)).astype(int)

print(f"  KOSPI 범위: {close.min():.0f} ~ {close.max():.0f}")
print(f"  D_sell ON: {D_sell.sum()}일 ({D_sell.mean()*100:.1f}%)  OFF: {(1-D_sell).sum()}일")

# ══════════════════════════════════════════════════════════════
# 2. H1 — 동시점 분류력 (D_sell 인 날의 수익률)
# ══════════════════════════════════════════════════════════════
print("\n\n【H1. 동시점 분류력 — D_sell 상태별 당일 수익률】")
print("─" * 70)
r_on  = ret[D_sell == 1]
r_off = ret[D_sell == 0]
print(f"  {'상태':>10} {'일수':>6} {'평균%':>9} {'중앙%':>9} {'표준편차':>9} {'하락비율':>9}")
print("  " + "─" * 60)
for label, arr in [("D_sell ON", r_on), ("D_sell OFF", r_off)]:
    down = (arr < 0).mean()*100
    print(f"  {label:>10} {len(arr):>6} {arr.mean():>+9.3f} "
          f"{np.median(arr):>+9.3f} {arr.std():>9.3f} {down:>8.1f}%")

# t-검정 (간이)
diff = r_off.mean() - r_on.mean()
pooled_se = math.sqrt(r_on.var()/len(r_on) + r_off.var()/len(r_off))
t_stat = diff / pooled_se
print(f"\n  평균차 (OFF-ON) = {diff:+.3f}%/일   t≈{t_stat:.2f}")
print(f"  → D_sell ON 날이 OFF 날보다 평균 {diff:.3f}%p 낮음 "
      f"({'유의미 (|t|>2)' if abs(t_stat)>2 else '약함'})")

# ══════════════════════════════════════════════════════════════
# 3. H2 — 폭락 포착력
# ══════════════════════════════════════════════════════════════
print("\n\n【H2. 폭락 포착력 — 큰 하락일을 다이오드가 잡는가】")
print("─" * 70)
print(f"  {'임계':>10} {'해당일수':>8} {'D_sell ON':>10} {'포착률':>9}")
print("  " + "─" * 50)
for thr in [-1.0, -2.0, -3.0, -5.0]:
    mask = ret < thr
    n = mask.sum()
    if n == 0: continue
    captured = D_sell[mask].sum()
    print(f"  {thr:>+9.1f}% {n:>8} {captured:>10} {captured/n*100:>8.1f}%")
# 상승일과 대조
print()
for thr in [+2.0, +3.0]:
    mask = ret > thr
    n = mask.sum()
    if n==0: continue
    on = D_sell[mask].sum()
    print(f"  {thr:>+9.1f}%↑ {n:>8} {on:>10} {on/n*100:>8.1f}%  (상승일엔 D_sell 드물어야 정상)")

# ══════════════════════════════════════════════════════════════
# 4. H3 — 익일 예측력 (관성 L 가설, ex-ante)
# ══════════════════════════════════════════════════════════════
print("\n\n【H3. 익일 예측력 — D_sell[t] → return[t+1] (진짜 ex-ante)】")
print("─" * 70)
# t일 종가 후 알 수 있는 D_sell[t]로 t+1일 수익률 예측
nxt = ret[1:]               # t+1 수익률
sig = D_sell[:-1]           # t일 신호
nxt_on  = nxt[sig == 1]
nxt_off = nxt[sig == 0]
print(f"  D_sell[t]=ON  → 익일 평균: {nxt_on.mean():+.3f}%  (n={len(nxt_on)}, 하락 {100*(nxt_on<0).mean():.0f}%)")
print(f"  D_sell[t]=OFF → 익일 평균: {nxt_off.mean():+.3f}%  (n={len(nxt_off)}, 하락 {100*(nxt_off<0).mean():.0f}%)")
pred_diff = nxt_off.mean() - nxt_on.mean()
print(f"\n  익일 평균차 = {pred_diff:+.3f}%p")
if pred_diff > 0.05:
    print(f"  → 관성(L) 가설 지지: 동반매도 다음날도 약세 경향 (모멘텀 존재)")
elif pred_diff < -0.05:
    print(f"  → 평균회귀 우세: 동반매도 다음날 오히려 반등 (RC형)")
else:
    print(f"  → 익일 예측력 미미: 다이오드는 '동시점 분류'엔 강하나 '익일 예측'엔 약함")

# ══════════════════════════════════════════════════════════════
# 5. H4 — 트레이딩 전략 백테스트
# ══════════════════════════════════════════════════════════════
print("\n\n【H4. 트레이딩 전략 백테스트】")
print("─" * 70)

def equity_curve(daily_ret_pct):
    eq = np.cumprod(1 + daily_ret_pct/100)
    return eq

def metrics(daily_ret_pct, label):
    eq = equity_curve(daily_ret_pct)
    total = (eq[-1]-1)*100
    years = len(daily_ret_pct)/252
    cagr = ((eq[-1])**(1/years)-1)*100 if years>0 and eq[-1]>0 else float('nan')
    sharpe = (daily_ret_pct.mean()/daily_ret_pct.std()*math.sqrt(252)) if daily_ret_pct.std()>0 else 0
    peak = np.maximum.accumulate(eq)
    mdd = ((eq-peak)/peak).min()*100
    return label, total, cagr, sharpe, mdd, eq[-1]

# 전략 일별 수익률 구성 (포지션은 전일 신호로 결정 = ex-ante, look-ahead 없음)
pos_bh   = np.ones(len(ret))                          # 항상 보유
# RC(단조): 전일 하락이면 반등 베팅(보유), 전일 상승이면 회피 — 단조회복 가정
pos_rc   = np.zeros(len(ret))
pos_rc[1:] = (ret[:-1] < 0).astype(float)            # 하락 다음날 보유
# 다이오드: 전일 D_sell ON이면 회피(현금), OFF면 보유
pos_diode = np.zeros(len(ret))
pos_diode[1:] = (D_sell[:-1] == 0).astype(float)
# 다이오드+숏: ON이면 숏(-1), OFF면 롱(+1)
pos_ds = np.zeros(len(ret))
pos_ds[1:] = np.where(D_sell[:-1]==0, 1.0, -1.0)

strat = {
    "Buy&Hold":          ret * pos_bh,
    "RC(하락익일매수)":   ret * pos_rc,
    "다이오드(ON회피)":   ret * pos_diode,
    "다이오드(ON숏)":     ret * pos_ds,
}

print(f"  {'전략':>18} {'총수익%':>9} {'CAGR%':>8} {'샤프':>7} {'MDD%':>8} {'배수':>7}")
print("  " + "─" * 62)
results = {}
for label, dr in strat.items():
    _, total, cagr, sharpe, mdd, mult = metrics(dr, label)
    results[label] = (total, cagr, sharpe, mdd)
    print(f"  {label:>18} {total:>+9.1f} {cagr:>+8.2f} {sharpe:>7.2f} {mdd:>8.1f} {mult:>7.2f}x")

print(f"\n  ※ 포지션은 전일 신호로 결정 (look-ahead 없음, 거래비용 미반영)")

# ══════════════════════════════════════════════════════════════
# 6. 사례 — 최근 충격 구간 재현
# ══════════════════════════════════════════════════════════════
print("\n\n【최근 충격 구간 재현 (6/8 폭락 포함 검증)】")
print("─" * 70)
print(f"  {'날짜':>10} {'종가':>9} {'일간%':>8} {'외국인':>9} {'기관':>9} {'D_sell':>7} {'분류':>5}")
print("  " + "─" * 65)
# 큰 변동일들 출력
for i in range(len(dates)):
    if abs(ret[i]) >= 3.0:  # 큰 변동일만
        d = dates[i]
        ds = "🔴ON" if D_sell[i] else "⬜OFF"
        # 분류 정확도: ON이면 하락이어야, OFF면 상승이어야
        correct = "✓" if (D_sell[i]==1 and ret[i]<0) or (D_sell[i]==0 and ret[i]>0) else "✗"
        print(f"  {d:>10} {close[i]:>9.0f} {ret[i]:>+8.2f} {F[i]:>+9.0f} {I[i]:>+9.0f} {ds:>7} {correct:>5}")

# 큰 변동일 분류 정확도
big = np.abs(ret) >= 3.0
big_correct = (((D_sell==1)&(ret<0)) | ((D_sell==0)&(ret>0)))[big].mean()*100
print(f"\n  큰 변동일(|일간|≥3%) 다이오드 방향 분류 정확도: {big_correct:.1f}%  (n={big.sum()})")

# ══════════════════════════════════════════════════════════════
# 7. 결론
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("【백테스트 결론】")
print("=" * 70)
bh = results["Buy&Hold"]
dd = results["다이오드(ON회피)"]
print(f"""
  표본: {len(dates)} 거래일 ({dates[0][:4]}-{dates[0][4:6]} ~ {dates[-1][:4]}-{dates[-1][4:6]})

  H1 동시점 분류:  D_sell ON 날 평균 {r_on.mean():+.2f}% vs OFF {r_off.mean():+.2f}% (차 {diff:.2f}%p, t={t_stat:.1f})
  H2 폭락 포착:    -3%↓ 폭락일의 {D_sell[ret<-3.0].mean()*100 if (ret<-3.0).any() else 0:.0f}%를 D_sell이 포착
  H3 익일 예측:    익일 평균차 {pred_diff:+.2f}%p → {'관성 존재' if pred_diff>0.05 else '익일 예측력 약함'}
  H4 트레이딩:     다이오드(ON회피) 샤프 {dd[2]:.2f} vs B&H {bh[2]:.2f}, MDD {dd[3]:.0f}% vs {bh[3]:.0f}%

  핵심 발견:
    · 다이오드는 '동시점 방향 분류'에 강력 (큰 변동일 {big_correct:.0f}% 정확)
    · {'익일 예측력도 유효' if pred_diff>0.05 else '익일 예측은 제한적 (당일 수급은 당일에만 강력)'}
    · 실전 함의: 장중 수급(F,I) 실시간 추적이 다이오드 모델의 생명선
""")
print("  ※ 정보·연구 목적. 투자자문 아님. 거래비용·세금·슬리피지 미반영.")
