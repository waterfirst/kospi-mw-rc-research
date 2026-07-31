# 2026-07-28 KOSPI Postmortem

## 채점
- 시가: 예측 6665.56 / 실제 6400.27
  - 오차 265.29pt
  - 오차율 4.1450%
  - tier_score 0
- 12:30 종가 엔진: 예측 5877 / 실제 6023.66
  - 오차 146.66pt
  - 오차율 2.4354%
  - tier_score 0

## 엔진별 판정
- 시가 엔진: 실패
  - 약세 방향은 맞았지만 실제 패닉 갭다운 강도를 따라가지 못했다.
  - SOX -2.23%, EWY -1.08%, USD/KRW +0.47%를 반영했어도 하방 cap/압축이 너무 보수적으로 작동했다.
- flow nowcast: 성공
  - 외국인 negative / 기관 positive / 프로그램 negative를 3/3 맞혔다.
- 장중 종가 엔진: 실패
  - avalanche_sell·crash_continuation 레짐은 맞았지만, 12:30 이후 추가 하락폭을 과대추정했다.
  - 12:30 현물 6050.17 대비 종가 6023.66은 소폭 추가 하락이었는데, 모델은 5877까지 내려갔다.

## 반복/후속 규칙
- 신규 기록
  - `F31_extreme_crash_gapdown_open_underreaction`
- 반복 기록
  - `F32_avalanche_sell_close_overshoot_repeated`
- 다음 후보
  - `add_preopen_crash_gapdown_override_when_sox_breaks_and_fx_pressure_high`
  - `keep_panic_stabilization_credit_when_avalanche_sell_nowcast_3of3_and_inst_positive`

## 소규모 코드 수정
- 파일: `monitor/kospi_1230_final_model_run.py`
- 내용: `panic_stabilization_credit` 추가
- 이유: 급락일 12:30 이후에도 추가 붕괴를 기계적으로 크게 보는 편향을 줄이기 위해, `nowcast 3/3 + 기관 순매수 + 최근 20분 하락 둔화 + 저가권` 조건에서 종가 하단을 현물 근처로 끌어올렸다.

## 테스트
- 2026-07-28: 종가 예측 5877 → 6046, 오차 146.66pt → 22.34pt, tier 0 → 4
- 2026-07-24: 변화 없음 (6634 유지)
- 2026-07-27: 규칙 미발동 (`panic_stabilization_credit=0`)
