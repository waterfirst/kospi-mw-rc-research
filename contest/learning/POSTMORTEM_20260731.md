# POSTMORTEM — 2026-07-31

## 결과
- 시가 예측: 5789.33 vs 실제 5657.79
  - 오차 131.54pt
  - 오차율 2.3256%
  - tier_score 0
- 12:30 종가 예측: 6389 vs 실제 6595.45
  - 오차 206.45pt
  - 오차율 3.1301%
  - tier_score 0

## 엔진별 판정
1. 시가 엔진: 실패
   - 미국 반도체 급등을 개장 갭으로 과대 전이했다.
   - 실제 개장은 +1.15%에 그쳤고, 본격 급등은 장중에 나왔다.

2. flow nowcast: 부분 적중
   - 공식 preopen 기준 재계산: foreign positive / institution positive / program positive
   - 실제: foreign positive / institution negative / program positive
   - 2/3 적중

3. 장중 종가 엔진: 실패
   - weak_drift로 잠갔지만, 반도체 초강세 + 외인/프로그램 대규모 순매수 지속을 오후 melt-up continuation으로 충분히 올리지 못했다.

## failure_tags
- `F26_preopen_daily_log_not_persisted_repeated`
- `F34_positive_extreme_gapup_open_followthrough_overread`
- `F35_semis_meltup_continuation_credit_missing`

## 규칙 수정
- 파일: `monitor/kospi_1230_final_model_run.py`
- 변경 1: morning log가 없을 때 전일 `next_session_open_forecast`를 복원하는 fallback 추가
- 변경 2: `semis_meltup_continuation` + `semis_meltup_credit` 추가
- 이유: 7/31처럼 nowcast 2/3~3/3, 반도체 상대강도 급등, 저가권 이탈 없이 고점권 유지인 날 종가 상방을 과소평가하던 편향 완화

## 테스트
- 2026-07-31 종가 시뮬레이션
  - 패치 전: 6389 / tier 0
  - 패치 후: 6609 / 오차 13.55pt / 0.2054% / tier 5
- 2026-07-30: 변화 없음
- 2026-07-22: 변화 없음

## 다음 후보
- `require_preopen_domestic_confirmation_before_using_positive_extreme_gapup_cap_above_3p5pct`
- `persist_preopen_daily_log_before_intraday_close_engine`

투자자문이 아니라 연구·설명 목적입니다.
