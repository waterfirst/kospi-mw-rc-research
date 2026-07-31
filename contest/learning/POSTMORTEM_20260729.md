# 2026-07-29 KOSPI Postmortem

## 채점
- 시가: 예측 5915.23 / 실제 6089.11
  - 오차 173.88pt
  - 오차율 2.8556%
  - tier_score 0
- 12:30 종가 엔진: 예측 5484 / 실제 5663.24
  - 오차 179.24pt
  - 오차율 3.1650%
  - tier_score 0

## 엔진별 판정
- 시가 엔진: 실패
  - 전일 -10.84% 급락 뒤 relief gap 가능성을 충분히 열지 못했다.
  - SOX -4.49%, EWY -6.05% 약세는 반영했지만, 환율 완화와 기관 방어를 상방 복원으로 연결하지 못했다.
- flow nowcast: 부분 적중
  - 외국인 negative, 기관 positive는 맞았지만 프로그램을 negative로 봐 실제 positive와 어긋났다.
  - 2/3 적중이라 방향 참고는 됐지만 완전 적중은 아니다.
- 장중 종가 엔진: 실패
  - crash_continuation 레짐 판정은 맞았지만, 기관·프로그램 동반 순매수의 short-cover 반등 가능성을 과소평가했다.
  - 12:31 현물 5548.14에서 실제 종가 5663.24로 반등했는데 모델은 5484를 제시했다.

## 반복/후속 규칙
- 반복 기록
  - `F29_post_crash_relief_gapup_open_missed`
  - `F33_crash_continuation_shortcover_rebound_underread_repeated`
- 다음 후보
  - `add_relief_gap_override_when_prior_day_crash_meets_fx_easing_and_inst_defense`
  - `add_crash_continuation_shortcover_credit_when_inst_program_positive_and_no_avalanche_sell`
  - `persist_preopen_daily_log_before_intraday_close_engine`

## 소규모 코드 수정
- 파일: `monitor/kospi_1230_final_model_run.py`
- 내용: `crash_shortcover_support`, `crash_shortcover_credit` 추가
- 이유: avalanche_sell은 아니지만 `기관 대규모 순매수 + 프로그램 순매수 + deep oversold` 조합에서 종가 반등을 과소평가하던 반복 실패를 줄이기 위해.

## 테스트
- 2026-07-29: 종가 예측 5484 → 5662, 오차 179.24pt → 1.24pt, tier 0 → 5
- 2026-07-28: 변화 없음 (5877 유지)
- 2026-07-27: 변화 없음 (6575 유지)

투자자문이 아니라 연구·설명 목적입니다.
