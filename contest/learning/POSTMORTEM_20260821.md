# 2026-08-21 KOSPI Postmortem

## 채점
- 시가 엔진: 예측 6,861.81 / 실제 6,759.95 — 오차 **101.86pt (1.5068%)**, tier_score **0/5**
- 12:30 종가 엔진: 예측 6,900.00 / 실제 6,912.95 — 오차 **12.95pt (0.1873%)**, tier_score **5/5**
- 일일 합계: **5/10**

실제 시가·종가·고저는 Naver KOSPI realtime/integration API의 `marketStatus=CLOSE` (2026-08-21 16:35 KST)로 확정했다.

## 엔진별 복기
- **시가 엔진: 실패.** EWY +2.14%를 반영해 +0.135% 갭을 예상했으나, 실제는 전일 종가 대비 -1.351% 갭하락이었다. 미국 S&P/Nasdaq 약세와 USD/KRW 상승 압력을 충분히 반영하지 못했고, 예측 범위(6,816.81~6,906.81)도 벗어났다. 동일 조건은 첫 관측이므로 `F43_ewy_positive_us_riskoff_gapdown_open_watch`로만 보존한다.
- **flow nowcast: 부분 성공(2/3).** 외국인·프로그램 부호는 맞았지만, 기관은 약한 양(+) 예측(score +0.4866)과 달리 12:30 실측이 음(-)이었다. 기관 양→음 반전은 기존 반복 실패 `F10_nowcast_sign_flip_late_repeated`를 재확인했다.
- **장중 종가 엔진: 성공.** `weak_drift` 6,900은 실제 종가보다 12.95pt 낮았고 예측 범위(6,830~6,948) 안에 마감했다.

## 학습·수정
- F10은 반복되지만 오늘 종가 레벨이 tier 5이므로 **레벨 계수 변경은 하지 않았다.** `institution score 0~0.75`의 약한 양(+) 신호를 `uncertain`으로 기록하고 confidence를 -0.05 조정하는 후보를 최소 3건 전향 검증한다.
- F43은 첫 사례다. `EWY>0 · S&P/Nasdaq<0 · USD/KRW 상승 · 직전 급등 후 갭하락` 코호트를 2건 더 모은 뒤에만 시가 잔차보정을 교차검증한다.

## 테스트
- `monitor.score_contest.tier_score` 재계산: 시가 **101.86pt / 1.5068% / 0점**, 종가 **12.95pt / 0.1873% / 5점**.
- `pytest -q monitor/test_kospi_1230_final_model_run.py` → **8 passed**
- `python3 -m py_compile monitor/final_open_research.py monitor/kospi_1230_final_model_run.py monitor/save_daily_log.py monitor/score_contest.py` → 통과.

투자자문이 아니라 연구·설명 목적입니다.
