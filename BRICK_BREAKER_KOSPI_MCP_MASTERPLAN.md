# Brick Breaker KOSPI MCP Masterplan

## 한 줄 목표

코스피 시가·종가 예측을 **하루 예측 작업**이 아니라,  
**반복-채점-회고-규칙수정**이 자동 순환되는 **벽돌깨기식 학습 루프**로 바꾼다.

---

## 1. 왜 벽돌깨기 구조인가

벽돌깨기에서 AI가 강해진 이유는 단순 반복이 아니라 아래 구조 때문이다.

1. 같은 게임을 계속 반복한다
2. 점수가 명확하다
3. 실패 원인이 다음 전략에 반영된다
4. 운이 아니라 구조가 쌓인다

코스피 예측도 동일하다.

- **게임**: 매일 시가·종가 맞히기
- **점수**: 오차, 방향성, 레짐 판정
- **실패**: 반도체 리더십 누락, 뉴스 충격 누락, 수급 오판 등
- **학습**: 플래그 추가, 조건 수정, 입력 변수 확장

즉, 목표는 “한 번 잘 맞히는 모델”이 아니라  
**매일 채점받으며 진화하는 예측 엔진**이다.

---

## 2. 최종 구조

```text
데이터 수집
  ↓
레짐 판정
  ↓
시가 예측 / 종가 예측
  ↓
실제값 수집
  ↓
자동 채점
  ↓
실패 유형 분류
  ↓
모델 규칙 수정 후보 생성
  ↓
주간 / 월간 보고서
```

---

## 3. MCP로 완성할 때의 역할

MCP는 단순 조회기가 아니라 아래 5개를 한 몸으로 묶는 구조여야 한다.

### A. 데이터 허브
- 미국장 지표
- 반도체 지표
- 환율
- 외인/기관/프로그램 수급
- 뉴스 이벤트
- 과거 예측/채점 기록

### B. 예측 엔진
- 시가 예측
- 종가 예측
- 방향성 판정
- 레짐 판정
- 신뢰도 점수

### C. 채점 엔진
- 시가 점수
- 종가 점수
- 방향 점수
- 레짐 점수
- Claude vs Codex 비교 점수

### D. 회고 엔진
- 왜 틀렸는지 자동 분류
- 같은 실패 반복 여부 탐지
- 모델 수정 후보 도출

### E. 보고서 엔진
- 일간 결과 요약
- 주간 종합 리포트
- 시계열 그래프
- 회로도 변화 과정

---

## 4. 반드시 들어가야 할 루프 안전장치

### 1) 종료 조건
- 일일 예측 1회 제출 후 종료
- 종가 채점 완료 시 일일 루프 종료
- 주간 보고서 생성 시 주간 루프 종료

### 2) 반복 상한
- 같은 날 재시도 횟수 제한
- 모델 자동 수정 제안 횟수 제한
- 주간 규칙 변경 건수 제한

### 3) 예산 상한
- 토큰 상한
- API 호출 상한
- 데이터 수집 시간 상한

### 4) 같은 실패 반복 차단기
- 동일 실패 유형 3회 연속 발생 시 경고
- 동일 플래그가 3회 연속 무효일 경우 비활성 후보 등록
- 같은 과적합 수정이 2주 이상 악화시키면 롤백 후보 등록

---

## 5. 예측 입력 변수 체계

## 5-1. 해외 선행 변수
- S&P500
- Nasdaq
- SOX
- EWY
- Micron / Nvidia / Meta / Amazon 등 AI·반도체 관련 강도

## 5-2. 환율 변수
- USD/KRW
- 달러 인덱스
- 위험회피성 환율 급등 여부

## 5-3. 국내 수급 변수
- 외국인 순매수
- 기관 순매수
- 프로그램 순매수
- 연기금/투신 보조 데이터 가능 시 추가

## 5-4. 뉴스/이벤트 변수
- 전쟁
- 관세
- 반도체 규제
- 대형 실적 발표
- 대통령/정부 정책 이벤트

## 5-5. 구조 변수
- 갭 상승 피로도
- 폭락 후 반등 구조
- 반도체 리더십
- breadth 약세 vs 흐름 지지
- panic / capitulation / exhaustion 상태

---

## 6. 실패 유형 분류 체계

실패는 “틀림”으로 끝내면 안 되고 반드시 유형화해야 한다.

### F1. 반도체 리더십 누락
- SOX 급등/급락이 시가에 과소반영됨

### F2. 환율 저항 과대·과소반영
- USD/KRW 영향이 실제보다 약하거나 강하게 반영됨

### F3. 뉴스 충격 누락
- 전쟁, 관세, 실적, 정책 쇼크 미반영

### F4. 수급 단위/강도 해석 오류
- 외인·기관·프로그램 해석 실패

### F5. 갭 후 피로도 누락
- 시가 급등 후 종가 밀림을 놓침

### F6. 폭락 후 반등 해석 실패
- panic 다음날 technical rebound를 놓침

### F7. 과적합 플래그 오발화
- 특정 플래그가 최근 며칠 패턴만 보고 과도 발동

---

## 7. MCP 도구 목록 제안

## 7-1. 입력/조회 계층

### `get_market_snapshot(date)`
- 전일 미국장, EWY, SOX, 주요 종목, 환율, 수급 요약 반환

### `get_news_shocks(date)`
- 당일 및 전일의 충격 이벤트 추출

### `get_flow_snapshot(date)`
- 외인, 기관, 프로그램 수급 요약

### `get_prediction_history(start, end)`
- 과거 예측/실측/점수 이력 조회

---

## 7-2. 예측 계층

### `predict_open(date, model_version)`
- 시가 예측값 + 근거 + 플래그 + 신뢰도

### `predict_close(date, model_version)`
- 종가 예측값 + 근거 + 플래그 + 신뢰도

### `classify_regime(date, snapshot)`
- panic / rebound / trend / exhaustion 등 레짐 판정

---

## 7-3. 채점 계층

### `score_open(date, predicted, actual)`
- 시가 오차 기반 점수 계산

### `score_close(date, predicted, actual)`
- 종가 오차 기반 점수 계산

### `score_duel(date, codex, claude, actual)`
- Claude vs Codex 승패 산출

---

## 7-4. 학습 계층

### `analyze_failure_patterns(window_days=20)`
- 최근 실패를 유형별로 집계

### `propose_rule_updates(window_days=20)`
- 어떤 플래그를 추가/수정/제거할지 후보 생성

### `validate_rule_candidate(rule_name, backtest_window)`
- 후보 규칙이 최근 구간에서 개선되는지 확인

---

## 7-5. 산출물 계층

### `render_daily_note(date)`
- 일간 요약 메모 생성

### `render_weekly_report(week_id)`
- 전문가형 HTML 종합 보고서 생성

### `render_model_evolution_diagram(version)`
- 회로도 방식 모델 진화도 생성

---

## 8. 로그 포맷 설계

하루 한 줄이 아니라, **입력-예측-결과-회고**가 한 덩어리로 저장돼야 한다.

```json
{
  "date": "2026-07-10",
  "model_version": "v7.3-gate-rc",
  "regime": "gap_up_exhaustion",
  "inputs": {
    "sp500_pct": 0.8,
    "nasdaq_pct": 1.3,
    "sox_pct": 3.06,
    "ewy_pct": 1.11,
    "usdkrw_pct": 0.2,
    "foreign_flow_krw_bn": -120.5,
    "inst_flow_krw_bn": 245.3,
    "program_flow_krw_bn": 90.2
  },
  "flags": [
    "semi_lead_gap_up",
    "gap_up_exhaustion_risk"
  ],
  "predictions": {
    "open": 7339.0,
    "close": 7298.0
  },
  "actuals": {
    "open": 7552.49,
    "close": 7475.94
  },
  "scores": {
    "open": 0,
    "close": 0,
    "direction": 0,
    "regime": 1,
    "total": 1
  },
  "failure_tags": [
    "F1_semi_lead_underweighted",
    "F5_gap_up_exhaustion_miscalibrated"
  ],
  "reflection": {
    "summary": "SOX 급등 구조를 충분히 앵커링하지 못함",
    "next_candidates": [
      "increase_sox_anchor_weight",
      "separate_open_anchor_from_close_exhaustion"
    ]
  }
}
```

---

## 9. 저장 구조 제안

```text
contest/
  learning/
    daily_logs/
      2026-07-10.json
    weekly_reports/
      2026-W28.html
    failure_stats/
      rolling_20d.json
    candidates/
      rule_update_queue.json
```

---

## 10. 500회 반복 로드맵

500회를 “많이 해보자”가 아니라 단계별 진화로 설계한다.

### Phase 1. 1~30회: 기록 체계 완성
- 빠짐없이 저장
- 수동 수정 줄이기
- 예측·실제·점수 자동 연결

### Phase 2. 31~80회: 실패 유형 안정화
- 실패 태그 체계 고정
- 같은 실패 반복 패턴 탐지

### Phase 3. 81~150회: 규칙 후보 자동화
- 어떤 플래그를 왜 바꿔야 하는지 자동 제안
- 단기 구간 검증 자동화

### Phase 4. 151~250회: 레짐 분화
- panic / rebound / trend / exhaustion 분리
- 시가와 종가 모델 역할 분리

### Phase 5. 251~350회: 앵커 정교화
- EWY vs SOX vs 환율 비중 조정
- 종목 리더십 구조 반영 강화

### Phase 6. 351~500회: 운영 최적화
- 과적합 차단기 강화
- 무의미한 플래그 제거
- 주간 보고서 기반 인간 검토 최소화

---

## 11. Codex / Claude / 멀티에이전트 역할 분담

### Codex
- 데이터 구조화
- 로그 저장
- 채점 자동화
- 규칙 비교 실험
- 주간 HTML 보고서 생성

### Claude
- 서술형 회고
- 실패 패턴 해석
- 전략 문장화
- 리스크 설명

### 멀티에이전트 조합
- **Codex**: 수집, 계산, 구조화, 시각화
- **Claude**: 의미 해석, 내러티브, 액션 플랜
- 필요 시 **Gemini**: 실시간 검색/뉴스 확인
- 필요 시 **Z AI**: 코드 초안

---

## 12. 성공 기준

이 프로젝트의 성공은 “하루 대박 예측”이 아니다.

### 진짜 성공 기준
- 최근 20거래일 평균 점수 개선
- 0점 빈도 감소
- 실패 유형의 재발률 감소
- 플래그 추가 후 백테스트 개선
- 사람이 직접 손보는 횟수 감소

---

## 13. 다음 구현 순서

### 1단계
- 일일 로그 JSON 저장기 완성

### 2단계
- 시가/종가 자동 채점기 완성

### 3단계
- 실패 태그 자동 분류기 추가

### 4단계
- 규칙 후보 제안기 추가

### 5단계
- 주간 HTML 종합 보고서 자동 생성

### 6단계
- MCP 툴 인터페이스로 묶기

---

## 14. 결론

벽돌깨기 법칙의 핵심은 반복 자체가 아니라  
**반복 속에서 점수와 실패가 전략으로 전환되는 구조**다.

코스피 시가·종가 예측도 마찬가지다.

> 예측 → 채점 → 실패분류 → 규칙수정 → 재예측

이 루프를 매일 돌리고,  
그 루프를 MCP로 표준화하면  
비로소 **“코스피 예측 MCP”** 가 완성된다.

