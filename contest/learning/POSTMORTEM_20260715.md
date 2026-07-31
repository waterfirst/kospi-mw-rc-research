# POSTMORTEM 2026-07-15

- 실제값 확인(네이버, 2026-07-15 16:36 KST): 시가 **7082.91**, 종가 **7284.41**
- 잠긴 원예측 채점:
  - 시가 6979.61 → 오차 **103.30pt**, **1.4584%**, **tier 1**
  - 12:30 종가 7386 → 오차 **101.59pt**, **1.3946%**, **tier 1**

## 엔진별 복기

- **시가 엔진: 실패**
  - EWY +5.33 / SOX +2.54 / USDKRW -0.62의 초강한 갭업 조합인데도 `compression=0.72`와 상단 `cap=+1.8%`가 동시에 걸려 상방을 과도하게 눌렀다.
  - 반복 실패로 `F13_extreme_gapup_compression_too_conservative_repeated` 기록.

- **flow nowcast: 부분 적중**
  - foreign/program positive는 맞음.
  - institution만 negative로 오판.
  - 반복 패턴으로 `F10_nowcast_sign_flip_late_repeated` 유지.

- **장중 종가 엔진: 실패**
  - 12:30에 시가=저가, 저가 회복률 0.99, 프로그램 +16,134, 반도체 상대강도 +2.15, 가속도 +21.3/+28.7pt를 continuation으로 해석.
  - 하지만 오후에는 점심 구간 포물선 확장분이 일부 반납됐다.

## 작은 규칙 수정

- `monitor/final_open_research.py`
  - 초강한 갭업일 `positive_extreme_gapup` 플래그 추가
  - 해당 조건에서 residual uplift 추가
  - compression을 0.72 대신 0.96 사용
  - 상단 open cap을 +1.8% → +3.5%로 완화

- `monitor/kospi_1230_final_model_run.py`
  - `parabolic_exhaustion_risk` 감지 추가
  - 시가=저가형 급등 + 높은 회복률 + 강한 프로그램/반도체 주도 시 `exhaustion_drag` 차감

## 재현 테스트

- 2026-07-15 시가: **6979.61 → 7058.39**, 오차 **103.30pt → 24.52pt**, **tier 1 → 4**
- 2026-07-15 종가: **7386 → 7274**, 오차 **101.59pt → 10.41pt**, **tier 1 → 5**
- 2026-07-14 회귀 확인:
  - 시가 예측 변화 없음: **6684.41**
  - 종가 재현값: **6842** (실제 **6856.83**)

투자자문이 아니라 연구·설명 목적입니다.
