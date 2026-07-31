# 2026-07-27 KOSPI Postmortem

## 채점
- 시가: 예측 6570.19 / 실제 6806.27
  - 오차 236.08pt
  - 오차율 3.4686%
  - tier_score 0
- 12:30 종가 엔진: 예측 6575 / 실제 6706.54
  - 오차 131.54pt
  - 오차율 1.9614%
  - tier_score 0

## 엔진별 판정
- 시가 엔진: 실패
  - prior crash 뒤 relief gap을 못 읽고 하방 앵커를 고정했다.
- flow nowcast: 성공
  - 외국인 negative / 기관 positive / 프로그램 negative를 3/3 맞혔다.
- 장중 종가 엔진: 실패
  - weak_drift는 맞았지만 오후 반등 크레딧이 부족했다.

## 반복/후속 규칙
- 신규 기록
  - `F29_post_crash_relief_gapup_open_missed`
  - `F30_semis_defensive_rebound_credit_missing`
- 다음 후보
  - `add_relief_gap_override_when_prior_day_crash_meets_fx_easing_and_sp500_flat`
  - `keep_semis_defensive_rebound_credit_when_nowcast_3of3_and_crash_continuation_false`

## 소규모 코드 수정
- 파일: `monitor/kospi_1230_final_model_run.py`
- 내용: `semis_defensive_rebound` 및 `semis_defensive_credit` 추가
- 이유: 반도체 상대강도 플러스 + nowcast 3/3 일치 + crash_continuation 없음에도 종가를 과도하게 낮게 보는 패턴 보정

## 테스트
- 2026-07-27: 종가 예측 6575 → 6674, 오차 131.54pt → 32.54pt, tier 0 → 4
- 2026-07-20: 변화 없음 (6490 유지)
- 2026-07-24: 변화 없음 (6634 유지)
