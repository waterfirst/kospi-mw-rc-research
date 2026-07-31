# POSTMORTEM — 2026-07-24

## 결과
- 시가 예측: 7088.34 → 실제 7000.78
  - 오차 87.56pt
  - 오차율 1.2507%
  - tier_score 1
- 12:30 종가 예측: 6634 → 실제 6690.62
  - 오차 56.62pt
  - 오차율 0.8463%
  - tier_score 2

## 엔진별 복기
1. 시가 엔진: 부분 적중
   - 하락 방향은 맞았지만 낙폭을 87.56pt 과소평가했다.
   - 전일 강한 종가 복원과 EWY +2.01%를 상대적으로 더 반영해, 실제 장초반 동반 매도 압력을 덜 봤다.
2. flow nowcast: 실패
   - 예측: foreign negative / institution positive / program negative
   - 실제(12:31): foreign negative / institution negative / program negative
   - institution만 반대로 봤다.
3. 장중 종가 엔진: 부분 적중
   - avalanche_sell·crash_continuation 레짐 판정은 맞았다.
   - 다만 저가권 반등폭을 과소평가해 종가를 56.62pt 낮게 봤다.

## 반복 실패 / 태그
- `F26_preopen_daily_log_not_persisted_repeated`
- `F28_broad_selloff_institution_positive_bias_repeated`

## 규칙 수정
- 추가: `broad_selloff_institution_derisk`
  - 조건: breadth 약세, foreign/program 동반 대규모 순매도, 삼성전자·SK하이닉스 동반 급락, 미국 빅테크 약세
  - 효과: institution nowcast score에 추가 음수 패널티 부여

## 왜 바꿨나
- 오늘처럼 breadth 0.289, foreign -214.2bn, program -231.3bn, 삼성전자 -7.31%, SK하이닉스 -6.98%인 날에는
  foreign 매도 자체를 기관 흡수 신호로 읽는 기존 점수가 과도하게 낙관적이었다.

투자자문이 아니라 연구·설명 목적입니다.
