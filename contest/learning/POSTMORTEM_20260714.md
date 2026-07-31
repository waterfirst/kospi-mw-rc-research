# POSTMORTEM 2026-07-14

- 실제 KOSPI 시가: 6,769.06
- 실제 KOSPI 종가: 6,856.83
- 시가 예측: 6,684.41 → 오차 84.65pt, 1.2505%, tier 1
- 12:30 종가 예측: 6,622 → 오차 234.83pt, 3.4248%, tier 0

## 엔진별 판정

1. 시가 엔진: 부분 적중 but 채점상 실패
   - Claude식 EWY 직결(6,473.32)보다는 덜 틀렸다.
   - 그러나 extreme compression 0.72와 -1.8% 하단 캡이 과도해 실제 시가보다 84.65pt 낮았다.

2. flow nowcast: 실패
   - institution sign만 맞고 foreign/program sign을 틀렸다.
   - 12:30 실제는 foreign +3,725 / institution +23,757 / program +3,972.

3. 장중 종가 엔진: 실패
   - breadth는 약했지만, 이미 실수급 3종이 모두 플러스였고 최근 10~20분 가격 가속도도 강했다.
   - 이를 `weak_drift`로 눌러 보고 late reversal을 놓쳤다.

## 반복 실패 분류

- `F10_nowcast_sign_flip_late_repeated`
  - 7/13은 false positive, 7/14는 false negative였다.
  - 방향은 반대지만 “flow nowcast가 실제 장중 수급 전환을 늦게 읽는다”는 실패 클래스는 반복됐다.

## 새 실패 분류

- `F11_midday_flow_reversal_squeeze_missed`
  - 12:30 기준 all-positive flow + positive acceleration 반등을 별도 레짐으로 승격하지 못했다.
- `F12_extreme_gapdown_compression_still_too_bearish`
  - EWY 급락일 과매도 완화는 했지만 open compression이 아직 너무 강했다.

## 오늘 반영한 작은 수정

- `monitor/kospi_1230_final_model_run.py`
  - `flow_reversal_squeeze` 조건 추가
  - 조건 충족 시 `rebound_credit` 반영
  - weak drift 상단 캡(기존 close+35)을 squeeze 레짐에서는 확장

## 재현 테스트

- 7/14 종가 재현:
  - 수정 전 6,622
  - 수정 후 6,842
  - 실제 6,856.83
  - 오차 234.83pt → 14.83pt
  - tier 0 → tier 5

- 7/13 보호 확인:
  - 기존 예측 6,804 유지
  - 기존 `avalanche_sell` 적중 케이스 훼손 없음

정보·연구 목적. 투자자문 아님.
