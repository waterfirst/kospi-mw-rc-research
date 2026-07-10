# KOSPI MCP 단계별 구현 계획

## 목표

벽돌깨기식 코스피 시가·종가 예측 시스템을  
**기록 → 채점 → 실패분석 → 규칙개선 → 보고서 → MCP화** 순서로 구현한다.

---

## 1단계. 일일 로그 자동 저장기

### 목적
- 매일 예측과 실제값을 구조적으로 쌓는다
- 학습의 재료를 만든다

### 구현 항목
- 예측 결과 JSON 저장
- 입력 변수 저장
- 사용 플래그 저장
- 모델 버전 저장

### 산출물
- `contest/learning/daily_logs/YYYY-MM-DD.json`
- `contest/learning/daily_logs/_template.json`

### 구현 파일
- `monitor/save_daily_log.py`

### 완료 기준
- 하루 1회 실행 시 JSON 파일이 자동 생성됨
- 수동 복붙 없이 기록 가능

---

## 2단계. 자동 채점기

### 목적
- 시가/종가 예측을 점수로 바꾼다
- Claude vs Codex 비교 가능하게 만든다

### 구현 항목
- 시가 오차 점수 계산
- 종가 오차 점수 계산
- 방향성 점수 계산
- 총점 계산

### 산출물
- 일일 로그 내 `scores`
- 별도 점수 요약 JSON/CSV

### 구현 파일
- `monitor/score_daily_prediction.py`

### 완료 기준
- 실제값 입력 후 자동 채점 완료
- 날짜별 점수표 생성 가능

---

## 3단계. 실패 태그 자동 분류기

### 목적
- “틀렸다”를 끝내지 않고 왜 틀렸는지 구조화한다

### 구현 항목
- 반도체 리더십 누락 탐지
- 환율 영향 과소/과대 탐지
- 뉴스 충격 누락 탐지
- 수급 해석 오류 탐지
- 갭 피로도 누락 탐지

### 산출물
- `failure_tags`
- `reflection.summary`

### 구현 파일
- `monitor/tag_failure_patterns.py`

### 완료 기준
- 채점 후 자동으로 실패 태그 부여
- 최근 20일 실패 유형 집계 가능

---

## 4단계. 규칙 후보 제안기

### 목적
- 같은 실패가 쌓이면 모델 수정 후보를 자동 제안한다

### 구현 항목
- 최근 실패 유형 빈도 계산
- 반복 실패 경고
- 새 플래그 후보 생성
- 기존 플래그 약화/비활성 후보 생성

### 산출물
- `contest/learning/candidates/rule_update_queue.json`

### 구현 파일
- `monitor/propose_rule_updates.py`

### 완료 기준
- 최근 20거래일 기준 규칙 수정 후보 자동 생성
- 사람이 후보만 검토하면 됨

---

## 5단계. 주간 HTML 종합 보고서

### 목적
- 한 주간의 성과와 실패를 사람이 빠르게 이해하게 만든다

### 구현 항목
- 날짜별 점수표
- 누적 점수 그래프
- 실측 vs 예측 시계열
- 모델 변화 과정 회로도
- 실패 유형 요약

### 산출물
- `docs/weekly_report_YYYY_WW.html`
- 고정 링크 별칭

### 구현 파일
- `monitor/render_weekly_report.py`

### 완료 기준
- 매주 금요일 자동 생성
- GitHub Pages에 자동 배포

---

## 6단계. MCP 인터페이스화

### 목적
- AI가 직접 조회·예측·채점·회고할 수 있게 만든다

### 구현 항목
- `get_market_snapshot`
- `predict_open`
- `predict_close`
- `score_prediction`
- `analyze_failure_patterns`
- `render_weekly_report`

### 산출물
- MCP 서버
- manifest / README / examples

### 구현 파일
- `mcp_kospi_diode/server.py`
- `mcp_kospi_diode/core.py`

### 완료 기준
- Claude/Codex가 MCP 도구로 직접 사용 가능
- 예측/채점/회고/보고서가 도구 호출로 이어짐

---

## 추천 구현 순서

### 먼저 할 것
1. `save_daily_log.py`
2. `score_daily_prediction.py`
3. `tag_failure_patterns.py`

### 그 다음
4. `propose_rule_updates.py`
5. `render_weekly_report.py`

### 마지막
6. MCP 인터페이스로 통합

---

## 운영 루프

```text
아침:
  데이터 수집 → 시가 예측 저장

장중/종가:
  종가 예측 저장 → 실제값 반영

저녁:
  자동 채점 → 실패 태그 → 회고 로그 저장

금요일:
  주간 보고서 생성 → GitHub Pages 배포
```

---

## 이번 주 바로 착수할 3개

### A. 일일 로그 자동 저장기
- 가장 먼저 필요

### B. 자동 채점기
- 점수 없이는 학습도 없음

### C. 실패 태그 분류기
- 벽돌깨기식 개선의 핵심

---

## 한 줄 결론

**1단계는 기록, 2단계는 채점, 3단계는 실패분석**이다.  
이 세 개가 완성되면 그 다음부터는 모델이 “경험을 쌓는 구조”가 된다.

