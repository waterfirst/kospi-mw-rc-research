# 2026-08-19 KOSPI Postmortem

## 채점
- 시가 엔진: 예측 6,746.17 / 실제 6,528.77 — 오차 **217.40pt (3.3299%)**, tier_score **0/5**
- 12:30 종가 엔진: 예측 6,424 / 실제 6,471.17 — 오차 **47.17pt (0.7289%)**, tier_score **3/5**
- 일일 합계: **3/10**

실제 시가·종가는 Naver KOSPI realtime/integration API의 `marketStatus=CLOSE` (2026-08-19 16:35 KST)로 확정했다.

## 엔진별 판정
- **시가 엔진: 실패.** EWY -8.13%, SOX -4.98%, Nasdaq -1.33%의 동반 하락에서 원시 야간 충격 -4.505%를 0.72로 압축하고 하방 -1.8% cap을 적용했다. 실제 시가는 -4.965%였으므로 217.40pt를 과소예측했다.
- **flow nowcast: 부분 실패(2/3).** 외국인·프로그램 순매도는 맞았으나 기관은 +1.991(양) 예측, 12:30 실측 -12,623(음)으로 틀렸다. 기관 양→음 반전은 `F10_nowcast_sign_flip_late_repeated`를 재확인한다.
- **장중 종가 엔진: 부분 성공.** `weak_drift` 6,424는 47.17pt 낮았지만 제시 범위(6,354~6,489) 안에 마감했다.

## 학습·수정
- `F10_nowcast_sign_flip_late_repeated`를 일일 로그에 남겼다. 종가 레벨은 범위 안·tier 3이므로 계수를 사후 조정하지 않는다.
- 오늘의 동반 극단 하락은 F31과 섞지 않고 `F40_extreme_overnight_selloff_open_compression_underreaction_watch`로 분리했다.
- `monitor/final_open_research.py`에 EWY≤-5%, SOX≤-3%, Nasdaq≤-1%, 전일 장중 반락·약한 breadth·기관/프로그램 순매도 동시 충족 관측 predicate를 추가했다. **예측 레벨에는 아직 연결하지 않는다.** 같은 좁은 코호트가 2개 추가 실패한 뒤에만 compression/cap 완화를 교차검증한다.

## 테스트
- `pytest -q monitor/test_kospi_1230_final_model_run.py` → **8 passed**
- `python3 -m py_compile` → 통과
- 일일 로그 JSON 파싱 및 `git diff --check` → 통과

투자자문이 아니라 연구·설명 목적입니다.
