# POSTMORTEM 2026-07-20

- 실제값 확인(네이버, 2026-07-20 16:36 KST): 시가 **6643.58**, 종가 **6516.27**
- 잠긴 원예측 채점:
  - 시가 6697.83 → 오차 **54.25pt**, **0.8166%**, **tier 2**
  - 12:30 종가 6490.00 → 오차 **26.27pt**, **0.4031%**, **tier 4**

## 엔진별 복기

- **시가 엔진: 부분 적중**
  - gap-down 방향은 맞았다.
  - 다만 전일 -6.37% 급락 뒤 오전 저가매수 복원 가능성을 과소평가해 시가를 54.25pt 높게 봤다.

- **flow nowcast: 실패**
  - 예측: foreign negative / institution positive / program negative
  - 실제: foreign positive / institution negative / program positive
  - 전일 급락 손상 뒤 `foreign+program dip-buy / institution de-risk` 회전이 다시 나타났는데 기존 점수식은 이를 계속 bearish continuation으로만 읽었다.

- **장중 종가 엔진: 적중**
  - breadth 붕괴, 낮은 저가 회복률, 음의 10~20분 가속도를 유지한 약세 지속 해석은 맞았다.
  - 종가 오차를 26.27pt로 제한해 tier 4를 기록했다.

## 작은 규칙 수정

- `monitor/kospi_1230_final_model_run.py`
  - `post_damage_rebound_rotation` 조건 추가
  - 조건: 전일 -5% 이하 급락 + 전일 장중 되밀림 + 손상된 국내 수급 + 미국 약세가 과도하지 않은 날
  - 효과: foreign/program nowcast를 덜 bearish하게, institution nowcast를 더 보수적으로 조정

## 재현 테스트

- 2026-07-20 nowcast
  - before: **negative / positive / negative**
  - after: **positive / negative / positive**
  - actual: **positive / negative / positive**
  - mismatch: **3 → 0**
- 회귀 확인
  - 2026-07-13 after: **negative / negative / negative** 유지
  - 2026-07-16 after: **negative / negative / negative** 유지

투자자문이 아니라 연구·설명 목적입니다.
