# POSTMORTEM 2026-07-16

- 실제값 확인(네이버, 2026-07-16 16:16 KST): 시가 **6960.50**, 종가 **6820.60**
- 잠긴 원예측 채점:
  - 시가 7216.70 → 오차 **256.20pt**, **3.6808%**, **tier 0**
  - 12:30 종가 6765.00 → 오차 **55.60pt**, **0.8152%**, **tier 2**

## 엔진별 복기

- **시가 엔진: 실패**
  - 전일 +6.24% 급등, 장중 +2.84% 확장, 상승비율 0.808의 과열 상태 뒤에 EWY -3.02 / SOX -2.08 unwind가 나왔는데도 하단 압축이 너무 강했다.
  - 결과적으로 하락 개시를 과소평가해 시가를 256.20pt 높게 봤다.

- **flow nowcast: 부분 적중**
  - foreign/program negative는 맞음.
  - institution만 positive로 오판.
  - 완전 동일 실패는 아니지만, **extreme semiconductor 다음날 institution leg 불안정** 패턴은 연속 관찰되어 새 태그로 기록.

- **장중 종가 엔진: 부분 적중**
  - `crash_continuation` 레짐 판정과 하락 방향은 맞았다.
  - 다만 12:30 이후 추가 하락폭을 실제보다 약 56pt 크게 반영했다.

## 작은 규칙 수정

- `monitor/final_open_research.py`
  - `negative_extreme_unwind` 플래그 추가
  - 전일 blowoff day 뒤 EWY·SOX 동반 반락이면 시가 하방 residual penalty 부여
  - 같은 조건에서 하단 cap을 -1.8% → -5.0%로 완화

- `monitor/kospi_1230_final_model_run.py`
  - 같은 unwind 조건에서 institution nowcast score에 추가 음수 패널티 부여
  - 목적: post-extreme-day 낙관 bias 제거

## 재현 테스트

- 2026-07-16 시가: **7216.70 → 6986.80**, 오차 **256.20pt → 26.30pt**, **tier 0 → 4**
- 2026-07-16 institution nowcast: **positive → negative**, 실제 **negative**
- 2026-07-15 회귀 확인:
  - open replay 변화 없음: **7028.77 → 7028.77**
  - institution nowcast 부호 변화 없음: **negative → negative**

투자자문이 아니라 연구·설명 목적입니다.
