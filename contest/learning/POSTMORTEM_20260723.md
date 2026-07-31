# POSTMORTEM 2026-07-23

- 실제값 확인(2026-07-23 16:39 KST): 시가 **6963.35**, 종가 **7096.89**
- 잠긴 원예측 채점:
  - 시가 **6752.24** → 오차 **211.11pt**, **3.0317%**, **tier 0**
  - 12:30 종가 **7014.00** → 오차 **82.89pt**, **1.1680%**, **tier 1**

## 엔진별 복기

- **시가 엔진: 실패**
  - 오늘 로그는 preopen 잠금본이 아니라 12:31 자동 생성본이다.
  - 전일 장중 손상과 약한 미국 지표를 더 크게 봤고, 당일 삼성전자·SK하이닉스 강세와 외국인·프로그램 추격 매수를 시가에 충분히 반영하지 못했다.

- **flow nowcast: 실패**
  - 원예측: foreign positive / institution positive / program negative
  - 실제: foreign positive / institution negative / program positive
  - 부호 일치 **1/3**.

- **장중 종가 엔진: 부분 적중**
  - 오후 추가 상방을 충분히 열어 두지 못해 7014로 다소 낮았지만, 오차를 **82.89pt**로 제한해 **tier 1**을 기록했다.

## 반복 실패

- `F26_preopen_daily_log_not_persisted_repeated`
  - 7/21~7/23에 preopen 로그가 잠기지 않아 당일 시가 채점 기준이 불안정했다.

- `F27_semi_meltup_institution_positive_bias_repeated`
  - 7/22, 7/23 연속으로 반도체 주도 강세장에서 기관을 positive로 과대평가했다.

## 오늘 반영한 작은 수정

- `monitor/kospi_1230_final_model_run.py`
  - `semi_meltup_institution_derisk` 규칙 추가
  - 조건: 외국인·프로그램 강한 양수, 높은 상승비율, 삼성전자/하이닉스 동반 강세, 기관 prior flow가 과도한 양수가 아닐 때
  - 효과: 기관 score를 낮추고 프로그램 score를 소폭 높여 melt-up 구간 de-risking을 반영

- `monitor/final_open_research.py`
  - `--save-log` 옵션 추가
  - 07:30 실행 시 preopen daily log를 즉시 저장할 수 있게 해, 반복된 “아침 로그 미저장” 실패를 줄일 수 있게 함

## 테스트

- 문법 확인: `py_compile_ok`
- nowcast 회귀:
  - 2026-07-20: **positive / negative / positive**, mismatch **0**
  - 2026-07-22: **positive / negative / positive**, mismatch **0**
  - 2026-07-23: **positive / negative / positive**, mismatch **0**
- CLI 확인:
  - `python3 monitor/final_open_research.py --help` 정상 출력

## 다음 규칙 후보

- `enable_final_open_research_save_log_in_0730_scheduler`
- `keep_semi_meltup_institution_derisk_nowcast_override`
- `add_open_rebound_override_after_prior_intraday_damage_when_live_semis_flip_positive`

투자자문이 아니라 연구·설명 목적입니다.
