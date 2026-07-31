# POSTMORTEM 2026-07-17

- 실제값 채점: **보류**
- 확인 결과:
  - 네이버 KOSPI 일봉/API 마지막 체결일: **2026-07-16**
  - Yahoo Finance `^KS11` 마지막 체결일: **2026-07-16**
  - `2026-07-17`은 확인 소스 기준 **KRX 휴장일**로 보여 당일 시가·종가 실제값이 없다.

## 오늘 판정

- **시가 엔진: 채점 불가**
  - `2026-07-17` 실제 시가가 없어 오차·오차율·tier_score 계산 불가.

- **flow nowcast: 무효**
  - 생성된 `20260717_1230_final_model_forecast.json`은 `local_traded_at=2026-07-16` 전일 스냅샷 사용.

- **장중 종가 엔진: 무효**
  - 12:30 최종모델 산출물이 휴장일 stale snapshot 기반이라 당일 성능으로 볼 수 없다.

## 작은 규칙 수정

- `monitor/kospi_1230_final_model_run.py`
  - `stale_market_data` 가드 추가
  - 실시간 `local_traded_at` / `bizdate`가 오늘 KST와 다르면 12:30 엔진 즉시 중단

## 테스트

- 2026-07-17 환경 재실행:
  - 이전: 전일(2026-07-16) 스냅샷으로 12:30 예측 파일 생성
  - 이후: `status=error`, `reason=stale_market_data`로 중단

## 학습 기록

- failure_tags
  - `F17_krx_holiday_open_score_unavailable`
  - `F18_intraday_stale_snapshot_guard_missing`

- 다음 규칙 후보
  - `add_krx_holiday_gate_before_0730_open_forecast`
  - `block_1230_final_model_when_realtime_date_is_not_today`

투자자문이 아니라 연구·설명 목적입니다.
