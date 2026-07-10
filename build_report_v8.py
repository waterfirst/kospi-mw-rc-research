#!/usr/bin/env python3
"""build_report_v8.py — 2년 백테스트/개량/수급 분석 자가완결 HTML 보고서 생성.
차트 3장 base64 임베드. 2026-07-10 | Claude. 정보·연구 목적."""
import base64, os, datetime

HERE = "/home/waterfirst/kospi-mw-rc-research"
BT = f"{HERE}/contest/backtests"

def b64(p):
    return base64.b64encode(open(p, "rb").read()).decode()

img1 = b64(f"{BT}/chart_Q1_open.png")
img2 = b64(f"{BT}/chart_Q2_close_from_open.png")
img3 = b64(f"{BT}/chart_Q3_diffusion_trend.png")
gen = datetime.datetime.now().strftime("%Y-%m-%d %H:%M KST")

HTML = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>KOSPI 다이오드 v8 — 2년 백테스트 & 수급 분석 보고서</title>
<style>
:root{{--bg:#0f1420;--card:#171d2b;--ink:#e8ecf4;--sub:#9aa6bd;--line:#28304aff;
--red:#e4572e;--grn:#2e8b57;--blu:#3a6ea5;--pur:#6a4c93;--amber:#d9a441;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
font-family:'Segoe UI','Noto Sans KR',system-ui,sans-serif;line-height:1.65}}
.wrap{{max-width:960px;margin:0 auto;padding:32px 20px 80px}}
h1{{font-size:26px;margin:0 0 4px}}
h2{{font-size:20px;margin:38px 0 12px;padding-bottom:6px;border-bottom:2px solid var(--line)}}
h3{{font-size:16px;margin:20px 0 8px;color:var(--amber)}}
.sub{{color:var(--sub);font-size:14px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin:14px 0}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}}
.kpi{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}}
.kpi .v{{font-size:26px;font-weight:700}}
.kpi .l{{color:var(--sub);font-size:12px;margin-top:2px}}
.good{{color:#4ade80}} .bad{{color:#f87171}} .mut{{color:var(--sub)}}
table{{width:100%;border-collapse:collapse;margin:10px 0;font-size:14px}}
th,td{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:right}}
th:first-child,td:first-child{{text-align:left}}
th{{color:var(--sub);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.03em}}
tr.win td{{background:rgba(46,139,87,.10)}}
img{{width:100%;border-radius:10px;border:1px solid var(--line);margin:8px 0;background:#fff}}
.tag{{display:inline-block;font-size:11px;padding:2px 8px;border-radius:20px;border:1px solid var(--line);color:var(--sub);margin-left:6px}}
.verdict{{border-left:4px solid var(--amber);background:rgba(217,164,65,.08);padding:14px 18px;border-radius:0 10px 10px 0;margin:14px 0}}
code{{background:#0b0f18;padding:1px 6px;border-radius:5px;font-size:13px}}
.foot{{color:var(--sub);font-size:12px;margin-top:40px;border-top:1px solid var(--line);padding-top:14px}}
ul{{margin:6px 0 6px 2px;padding-left:18px}} li{{margin:3px 0}}
</style></head><body><div class="wrap">

<h1>KOSPI 다이오드 회로모델 — 2년 백테스트 &amp; 수급 예측 분석</h1>
<div class="sub">v7 → <b>v8 재캘리브레이션</b> · 표본 602거래일(2024-01~2026-06) · 생성 {gen}<span class="tag">정보·연구 목적 · 투자자문 아님</span></div>

<div class="kpis">
  <div class="kpi"><div class="v good">0.733%</div><div class="l">v8 시가 MAE (v7 0.853%)</div></div>
  <div class="kpi"><div class="v">0.840%</div><div class="l">순진 baseline MAE</div></div>
  <div class="kpi"><div class="v good">+0.107%p</div><div class="l">v8의 baseline 대비 우위</div></div>
  <div class="kpi"><div class="v">78.2%</div><div class="l">오차 ≤1% 비율 (v7 69.6%)</div></div>
  <div class="kpi"><div class="v">R²=0.37</div><div class="l">외인수급 예측 설명력</div></div>
</div>

<div class="verdict"><b>한 줄 요약.</b> v7 시가모델(0.58×EWY)은 2년 백테스트에서 “그냥 전일종가”에도 졌다.
원인은 EWY 과신 + 극단일 폭주. <b>K를 0.58→0.30으로 낮추고 극단 EWY를 ±3%로 winsor한 v8</b>은
walk-forward OOS에서 baseline·v7을 모두 이긴다. 종가 점예측은 노이즈 바닥(시가로 설명 2.3%)이라
실익이 없고, 진짜 정보는 <b>장중 외인 수급</b>에 있다(외인은 부분예측 가능, 기관은 불가).</div>

<h2>1. 최종 모델 수정 — v7 → v8</h2>
<div class="card">
<h3>무엇을 왜 고쳤나</h3>
<ul>
<li><b>K_EWY 0.58 → 0.30</b>: v7은 EWY 오버나잇을 과신. EWY엔 원/달러 환율노이즈+미장 과민반응이 섞여
있어 계수가 컸다. 인샘플 최적 K≈0.24, 홀드아웃 안정구간 0.30~0.35 → <b>0.30 채택</b>.</li>
<li><b>EWY winsor ±3% 신설</b>: |EWY|&gt;3% 극단일에 선형 외삽이 대형오차를 냄
(예: 06/24 EWY −12.25%인데 실제 시가 +1.86%). 신호를 ±3%로 축소해 fat-tail 억제.</li>
</ul>
<table>
<tr><th>지표</th><th>v7 (K=0.58)</th><th>v8 (K=0.30, winsor±3)</th><th>baseline(갭0)</th></tr>
<tr class="win"><td>평균 오차 MAE</td><td>0.853%</td><td><b>0.733%</b></td><td>0.840%</td></tr>
<tr><td>중앙값 오차</td><td>0.625%</td><td><b>0.503%</b></td><td>0.542%</td></tr>
<tr><td>오차 ≤0.5% 비율</td><td>42.4%</td><td><b>49.7%</b></td><td>—</td></tr>
<tr><td>오차 ≤1.0% 비율</td><td>69.6%</td><td><b>78.2%</b></td><td>—</td></tr>
<tr><td>최대 오차</td><td>7.25%</td><td><b>5.21%</b></td><td>—</td></tr>
</table>
<h3>Walk-forward OOS 검증 (look-ahead 없음, 482일)</h3>
<table>
<tr><th>구간</th><th>v8 개량형</th><th>v7</th><th>baseline</th></tr>
<tr class="win"><td>전체 OOS MAE</td><td><b>0.781%</b></td><td>0.954%</td><td>0.911%</td></tr>
<tr class="win"><td>극단일 |EWY|&gt;3% (75일)</td><td><b>1.30%</b></td><td>1.85%</td><td>—</td></tr>
</table>
<div class="sub">배포 반영: <code>kospi_diode_mcp/core.py</code> K_EWY=0.30, EWY_WINSOR=3.0. 단위테스트 8/8 통과.</div>
</div>

<h2>2. Q1 — 시가 예측은 잘하는가? <span class="tag">그래프: 실측 vs 예측</span></h2>
<div class="card">
<p>v7 기준으론 <b>아니었다</b>(baseline도 못 넘음). 아래 그래프의 하단 오차밴드를 보면 2024·2025는
baseline 근처, <b>2026 급락장에서 빨간 오차가 폭발</b>. v8은 이 극단 구간을 크게 순화한다.</p>
<img alt="Q1 시가 실측 vs 예측" src="data:image/png;base64,{img1}">
</div>

<h2>3. Q2 — 시가로 종가를 예측할 수 있나? <span class="tag">거의 불가</span></h2>
<div class="card">
<table>
<tr><th>항목</th><th>값</th><th>해석</th></tr>
<tr><td>시가갭 → 장중(시가→종가) 상관</td><td>r = 0.15</td><td>매우 약한 모멘텀</td></tr>
<tr><td>설명력 (r²)</td><td class="bad">2.3%</td><td>나머지 97.7%는 장중 수급·뉴스</td></tr>
<tr><td>walk-forward 모델 MAE</td><td>0.94%</td><td>baseline(close=open) 0.92%도 못 넘음</td></tr>
</table>
<p>결론: <b>시가만으로 종가는 못 맞춘다.</b> 그래서 종가모델이 12:35 실시간 외인/기관 수급을
입력으로 쓰는 것이 올바른 설계다.</p>
<img alt="Q2 시가→종가 산점도" src="data:image/png;base64,{img2}">
</div>

<h2>4. Q3 — 나비에-스토크스(확산항) 장기 트렌드 <span class="tag">분석 O · 예측 X</span></h2>
<div class="card">
<p>로그가격에 확산(열)방정식 <code>∂u/∂τ = ν ∂²u/∂x²</code>을 적용한 트렌드 필터.
장기추세선 + 추세속도(모멘텀) 장을 깔끔히 뽑아 <b>국면 분해·시각화엔 유용</b>하다.
단, 이는 정교한 저역통과 필터 = 스마트 이동평균이라 <b>미래 트렌드를 생성하지 못한다(묘사≠예측)</b>.
완전한 NS(이류·압력·비선형)를 넣어도 시장엔 물리적 속도장 대응물이 없어 예측 edge는 생기지 않는다.</p>
<img alt="Q3 확산 트렌드" src="data:image/png;base64,{img3}">
</div>

<h2>5. 장중 외인/기관 수급 — 모니터링 &amp; 예측</h2>
<div class="card">
<h3>수급 예측가능성 (2년 실측)</h3>
<table>
<tr><th>주체</th><th>자기상관 AR(1)</th><th>부호지속률</th><th>예측성</th></tr>
<tr class="win"><td>외국인 net</td><td class="good">r = +0.52</td><td>62%</td><td>강한 관성 → <b>부분예측 가능</b></td></tr>
<tr><td>기관 net</td><td class="bad">r = −0.03</td><td>54%</td><td>거의 없음 → <b>예측 불가</b>(반대·재량매매)</td></tr>
</table>
<ul>
<li>외인 다중회귀 <b>R²=0.37</b> (EWY오버나잇 + 전일수익 + 전일외인). 오버나잇 EWY↔당일 외인 r=0.20.</li>
<li>당일 외인 net ↔ 당일 수익 r=0.42 = <b>진짜 드라이버</b>. 단, “외인 방향 예측”이 “익일 수익”으론
거의 안 넘어감(익일차 +0.07%p) → 수급은 <b>진단엔 강, 예측엔 약</b>.</li>
</ul>
<h3>장중 수급 모니터링 설계 (실행안)</h3>
<ul>
<li><b>1차(핵심):</b> KRX/네이버 투자자별 장중 순매매 — 시가모델은 이미 <code>investorDealTrendDay</code>로
당일 누적 외인/기관을 12:35에 읽는다. 폴링 주기를 <b>09:00·10:00·11:00·12:35</b>로 촘촘히.</li>
<li><b>2차(선행):</b> 프로그램매매 순액(외인 흐름과 고상관, 준실시간) + <b>KOSPI200 선물 외인 순포지션</b>
(현물보다 선행) + <b>원/달러 장중</b>(약세 시 외인 매도 압력).</li>
<li><b>조기신호:</b> 장 초반 30분 누적 외인이 하루 전체 방향을 상당부분 결정 → 09:30 스냅샷으로
12:35 이전에 종가 레짐을 조기 세팅.</li>
</ul>
<h3>“미리 예측”은 어디까지 되나</h3>
<ul>
<li><b>가능:</b> 외인 방향은 (전일 외인 관성 r=0.52 + 오버나잇 EWY/환율)로 <b>R²≈0.37 수준 선행</b> 가능.
지수·배당·MSCI 리밸런싱·선물만기 같은 <b>캘린더성 대량 수급</b>은 사전 확정.</li>
<li><b>불가:</b> 기관 순매매 방향, 그리고 “수급→익일 지수수익”의 직접 예측(노이즈 바닥).</li>
</ul>
</div>

<h2>6. 코덱스 분석과의 비교</h2>
<div class="card">
<table>
<tr><th>항목</th><th>Claude (본 보고서)</th><th>Codex</th></tr>
<tr><td>검증 대상</td><td class="good">실제 배포 최종모델(EWY/SOX 복원)</td><td>일봉 코어 프록시(실모델 아님, 본인 명시)</td></tr>
<tr><td>점예측 vs naive</td><td>v7 패 → <b>v8 승</b></td><td>vFinal 프록시 MAE 1.31 vs 1.28 <span class="bad">패</span></td></tr>
<tr><td>전략 P&amp;L</td><td class="mut">본 라운드 미측정</td><td class="good">측정 — B&amp;H +215% Sharpe 1.69가 전부 압도</td></tr>
</table>
<p><b>상호보완.</b> 코덱스는 “Buy&amp;Hold가 모든 스마트전략을 이긴다”는 냉정한 P&amp;L 진실을 보탰고,
본 보고서는 “실제 모델을 진짜로 백테스트하고 v8로 개량”했다. 공통 결론:
<b>점예측 edge는 노이즈 바닥, 유일한 실익은 당일 수급 리스크 진단</b>.</p>
</div>

<h2>7. 다음 라운드 — v8로 코덱스와 재대결</h2>
<div class="card">
<ul>
<li>배포 엔진 <code>core.py</code>가 v8로 교체됨 → OS 크론(07:35/12:35/16:35)이 다음 거래일부터 자동으로 v8 예측 발송.</li>
<li>플래그 규율 유지(자동만료). hyper_bull 방치 자멸 재발 방지.</li>
<li>개량 초점: 시가는 v8로 극단 순화 완료, 다음은 <b>장중 수급 조기신호(09:30 스냅샷)</b> 기반 종가모델.</li>
</ul>
</div>

<div class="foot">엔진 <code>kospi_diode_claude</code> v8 · 데이터 KOSPI 일봉+수급(네이버) · EWY/SOX 오버나잇(Yahoo).
거래비용·세금·슬리피지 미반영. 정보·연구 목적, 투자자문 아님.</div>
</div></body></html>"""

out = f"{BT}/REPORT_v8_2yr_2026-07-10.html"
open(out, "w", encoding="utf-8").write(HTML)
print("WROTE", out, f"({len(HTML)//1024}KB)")
