# POSTMORTEM 2026-07-13

- 실제 KOSPI 시가: 7,412.03
- 실제 KOSPI 종가: 6,806.93
- 시가 예측: 7,472.19 → 오차 60.16pt, 0.8117%, tier 2
- 12:30 종가 예측: 6,804 → 오차 2.93pt, 0.0430%, tier 5

## 엔진별 판정

1. 시가 엔진: 실패
   - EWY -0.67% 음수인데 전일 국내 흡수력 잔차와 삼성전자 단독 강세를 과대평가했다.
   - SK하이닉스 -0.27% 비확인을 충분히 벌점화하지 못했다.

2. flow nowcast: 실패
   - foreign / institution 부호를 모두 positive로 봤다.
   - 실제 12:30 기준 foreign -17,033 / institution -5,422 / program -13,677 이었다.

3. 장중 종가 엔진: 적중
   - breadth 붕괴, 반도체 상대약세, 저가 회복 실패, 최근 10~20분 가속도 악화를 잘 반영했다.
   - avalanche_sell 레짐 판정은 유효했다.

## 반복 실패 분류

- `F3_ewy_negative_underweighted_repeated`
  - 7/3 계열의 EWY 가중치 이슈가 반대 방향으로 재발했다.
- `F6_split_semi_nonconfirmation_missed`
  - 삼성전자만 강하고 하이닉스가 못 따라오는 split-semi 상황을 낙관적으로 처리했다.
- `F9_nowcast_false_positive_foreign_institution`
  - 전일 반등 흔적을 현재 수급 부호로 과투영했다.

## 규칙 수정 후보

- EWY < -0.4%, SK하이닉스 <= +0.3%, 프로그램 <= 0, 전일 상승 후 되밀림이면 `split_semi_downside` 발동
- `split_semi_downside`에서는
  - 시가 엔진의 positive residual 축소
  - 추가 하방 penalty 부여
  - nowcast의 foreign / institution 점수 낙관 바이어스 제거

## 오늘 반영한 작은 수정

- `monitor/final_open_research.py`
  - `split_semi_downside` 규칙 추가
  - `opening_semiconductor_lead`에 SK하이닉스 확인 조건 추가
- `monitor/kospi_1230_final_model_run.py`
  - 동일 조건에서 foreign / institution nowcast 점수 하향 보정 추가

## 재현 테스트

- 시가 재현:
  - 수정 전 7,472.19
  - 수정 후 7,427.33
  - 실제 7,412.03
  - 오차 60.16pt → 15.30pt
  - tier 2 → tier 5

- nowcast 부호 재현:
  - 수정 전: foreign positive / institution positive / program negative
  - 수정 후: foreign negative / institution negative / program negative
