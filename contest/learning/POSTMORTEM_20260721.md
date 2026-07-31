# POSTMORTEM 2026-07-21

- 실제값 확인(네이버 API / Investing.com, 2026-07-21 16:35~16:36 KST): 시가 **6553.88**, 종가 **6747.95**
- 잠긴 원예측 채점:
  - 시가 **6798.48** → 오차 **244.60pt**, **3.7328%**, **tier 0**
  - 12:30 종가 **6775.00** → 오차 **27.05pt**, **0.4009%**, **tier 4**

## 엔진별 복기

- **시가 엔진: 실패**
  - 전일 급락 손상 뒤 반등 시도를 너무 크게 열어뒀다.
  - 특히 오늘 로그는 07:30 저장 누락 후 12:32 재구성본이라 `prior_kospi_close=6761.59`처럼 당일 값이 섞여 복기용 입력까지 오염됐다.

- **flow nowcast: 부분 적중**
  - foreign/program positive는 맞았다.
  - institution은 negative로 예측했지만 실제는 positive였다.
  - 최종 부호 일치 **2/3**.

- **장중 종가 엔진: 적중**
  - `institution_absorption` 판정은 유지됐고 종가 오차를 **27.05pt**로 제한했다.
  - tier 4라 완벽하진 않지만, 오늘 최종모델의 실질 성과는 종가 엔진이 지켰다.

## 반복 실패 분류

- `F21_post_damage_rebound_open_overshoot_repeated`
  - 전일 손상도가 큰 날, SOX·환율 완화만 보고 시가 반등 폭을 과대평가하는 패턴이 다시 나타났다.

## 새 운영 실패 분류

- `F22_open_log_reconstruction_contaminated`
  - 07:30 daily log 저장 누락 뒤 12:30 이후 재구성하면서 당일 값이 morning input에 섞였다.

## 오늘 반영한 작은 수정

- `monitor/final_open_research.py`
  - 09:00 이후 재실행/복기 시에는 **당일 행이 아니라 전일 완료 세션**을 시가 앵커로 사용하도록 수정
  - `reference_mode`, `reference_kospi_date`, `prior_kospi_close_date`를 남겨 재구성 오염 여부를 추적 가능하게 함

## 재현 테스트

- 2026-07-21 재구성 테스트(16:38 KST 재실행):
  - 수정 전 `prior_kospi_close`: **6761.59**
  - 수정 후 `prior_kospi_close`: **6516.27**
  - 수정 전 open replay: **6798.48**
  - 수정 후 open replay: **6525.37**
  - 실제 시가: **6553.88**
  - 재구성 오차: **244.60pt → 28.51pt**

## 다음 규칙 후보

- `persist_0730_daily_log_before_1230_run`
- `cap_open_rebound_after_prior_damage_if_us_tailwind_is_only_mild`
- `track_reference_session_dates_in_open_replay`

투자자문이 아니라 연구·설명 목적입니다.
