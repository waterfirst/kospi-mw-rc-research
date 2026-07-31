# POSTMORTEM 2026-07-22

- 실제값 확인(Investing.com, 2026-07-22 16:39 KST): 시가 **7052.09**, 종가 **6797.70**
- 잠긴 원예측 채점:
  - 시가 **6869.41** → 오차 **182.68pt**, **2.5904%**, **tier 0**
  - 12:30 종가 **7072.00** → 오차 **274.30pt**, **4.0351%**, **tier 0**

## 엔진별 복기

- **시가 엔진: 실패**
  - EWY·SOX·Nasdaq이 모두 강했는데 `fx_pressure_high`와 +1.8% cap이 상방을 과도하게 눌렀다.
  - 오늘은 환율 부담이 있었어도 반도체 주도 super gap-up이 더 강했다.

- **flow nowcast: 부분 적중**
  - foreign/program positive는 맞았다.
  - institution만 positive로 오판했다.
  - 최종 부호 일치 **2/3**.

- **장중 종가 엔진: 실패**
  - 12:30 시점에 이미 고점 대비 94pt 밀렸고, 저가 회복률도 0.37로 낮았다.
  - 하지만 `weak_drift`로 남겨 오후 blow-off reversal을 충분히 차감하지 못했다.

## 반복 실패 / 신규 실패

- `F13_extreme_gapup_compression_too_conservative_repeated`
  - 7/15에 이어 오늘도 초강한 갭업을 너무 보수적으로 눌렀다.

- `F24_super_gapup_false_negative_under_fx_pressure`
  - 환율 압박이 있어도 EWY·SOX·국내 반도체가 동시에 폭발하는 날은 별도 승격이 필요했다.

- `F25_midday_blowoff_reversal_risk_missing`
  - 큰 갭업 후 점심 전 고점 이탈·낮은 회복률 조합을 오후 되밀림 경고로 승격하지 못했다.

## 오늘 반영한 작은 수정

- `monitor/final_open_research.py`
  - `semiconductor_super_gapup_risk` 추가
  - EWY/SOX/나스닥/S&P와 국내 반도체 강세가 동시에 확인되면, 환율 패널티를 일부 우회하고 상단 cap을 **+5.0%**까지 허용

- `monitor/kospi_1230_final_model_run.py`
  - `detect_midday_blowoff_reversal_risk` 추가
  - 큰 갭업 후 고점 대비 밀림, 낮은 저가 회복률, 과열 가속, 프로그램 쏠림이 같이 나오면 `blowoff_drag`를 차감

## 테스트

- 문법 확인: `py_compile_ok`
- 2026-07-22 시가 추정 재현
  - 수정 전 예측: **6869.41**
  - 수정 후 추정: **7063.55**
  - 실제 시가: **7052.09**
  - 절대오차: **182.68pt → 11.46pt**

- 2026-07-22 종가 리스크 규칙 재현
  - `midday_blowoff_reversal_risk=True`
  - 수정 전 예측: **7072**
  - 수정 후 추정: **6838**
  - 실제 종가: **6797.70**
  - 절대오차: **274.30pt → 40.30pt**

- 회귀 확인
  - 2026-07-15 12:30 스냅샷: `midday_blowoff_reversal_risk=False`

## 다음 규칙 후보

- `reduce_institution_positive_nowcast_bias_on_semiconductor_meltup_days`
- `link_open_super_gapup_flag_to_intraday_close_exhaustion_prior`
- `persist_preopen_daily_log_before_intraday_close_engine`

투자자문이 아니라 연구·설명 목적입니다.
