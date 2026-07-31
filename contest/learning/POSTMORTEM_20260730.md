# 2026-07-30 KOSPI Postmortem

## 채점
- 시가: 예측 5561.30 / 실제 5681.77
  - 오차 120.47pt
  - 오차율 2.1203%
  - tier_score 0
- 12:30 종가 엔진: 예측 5623.00 / 실제 5593.56
  - 오차 29.44pt
  - 오차율 0.5263%
  - tier_score 3

## 엔진별 판정
- 시가 엔진: 실패
  - 전일 -5.98% 급락 뒤 relief gap 가능성을 또 충분히 열지 못했다.
  - SOX -5.33%, EWY -4.78% 약세는 반영했지만, 환율 완화와 장초 방어 흐름을 상방 복원으로 연결하지 못했다.
- flow nowcast: 실패
  - 예측: foreign negative / institution positive / program negative
  - 실제: foreign positive / institution positive / program positive
  - 외국인·프로그램의 플러스 전환을 놓쳐 1/3 적중에 그쳤다.
- 장중 종가 엔진: 부분 적중
  - weak_drift 자체는 크게 벗어나지 않았다.
  - 실제 종가 5593.56과의 오차를 29.44pt로 제한해 tier 3을 기록했다.

## 반복/후속 규칙
- 반복 기록
  - `F29_post_crash_relief_gapup_open_missed`
  - `F19_post_damage_rebound_nowcast_inversion_repeated`
- 다음 후보
  - `add_post_crash_relief_gap_rebound_credit_when_fx_eases_and_defense_survives`
  - `revive_post_damage_rebound_rotation_override_when_foreign_program_flip_positive`
  - `persist_preopen_daily_log_before_intraday_close_engine`

## 소규모 코드 수정
- 파일: `monitor/final_open_research.py`
- 내용: `relief_gap_rebound` 보정 규칙 추가
- 이유: 전일 급락 뒤 환율 완화 + 방어 흐름이 겹칠 때 시가 엔진이 -1.8% 하방 cap에 고정되던 반복 실패를 줄이기 위해

## 테스트
- 2026-07-30: 시가 예측 5561.30 → 5649.91, 오차 120.47pt → 31.86pt, tier 0 → 3
- 2026-07-29: 시가 예측 5915.23 → 6026.18, 오차 173.88pt → 62.93pt, tier 0 → 1
- 2026-07-28: 변화 없음 (6665.60 유지)
- 2026-07-27: 변화 없음 (6570.19 유지)

투자자문이 아니라 연구·설명 목적입니다.
