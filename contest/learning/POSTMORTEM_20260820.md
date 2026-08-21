# 2026-08-20 KOSPI Postmortem

## 채점
- 시가 엔진: 예측 6,478.34 / 실제 6,680.34 — 오차 **202.00pt (3.0238%)**, tier_score **0/5**
- 12:30 종가 엔진: 예측 6,826.00 / 실제 6,852.58 — 오차 **26.58pt (0.3879%)**, tier_score **4/5**
- 일일 합계: **4/10**

실제 시가·종가는 Naver KOSPI realtime API의 `marketStatus=CLOSE` (2026-08-20 16:35 KST)로 확정했다.

## 엔진별 복기
- **시가 엔진: 실패.** 전일 -5.80% 급락 뒤 EWY +2.58% 반등을 SOX -2.12%와 압축 규칙이 상쇄해 +0.11%만 반영했다. 실제는 +3.23% 갭상승으로 202.00pt를 과소예측했다.
- **flow nowcast: 실패(1/3).** 외국인·프로그램 음(-) 예측이 12:30 양(+) 실측과 반대였고 기관만 맞았다. 기존 F19와 비슷한 급락 후 수급 회전이지만 기관 부호가 달라 별도 태그 `F42_post_crash_foreign_program_positive_flip_watch`로 보존한다.
- **장중 종가 엔진: 성공.** `weak_drift` 6,826은 마감보다 26.58pt 낮았지만 범위(6,756~6,863) 안에 들었고 tier 4를 기록했다.

## 학습·수정
- `F41_post_crash_split_overnight_gapup_open_underreaction_watch`: 전일 -5% 이하 급락, EWY 반등과 SOX 약세가 엇갈린 뒤의 강한 시가 반등을 첫 관측으로 기록했다.
- `F42_post_crash_foreign_program_positive_flip_watch`: 외국인·프로그램 동시 양(+) 전환을 놓친 사례를 별도 기록했다.
- 두 조합 모두 표본 1건이므로 **코드·계수 변경은 하지 않았다.** 각각 같은 좁은 조건의 추가 2건을 채점한 뒤에만 잔차보정·nowcast override를 교차검증한다. 사후 적합을 피하기 위한 결정이다.

## 테스트
- `pytest -q monitor/test_kospi_1230_final_model_run.py` → **8 passed**
- `python3 -m py_compile monitor/final_open_research.py monitor/kospi_1230_final_model_run.py monitor/save_daily_log.py` → 통과
- 일일 로그 JSON 파싱 → 통과

투자자문이 아니라 연구·설명 목적입니다.
